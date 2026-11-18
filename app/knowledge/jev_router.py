import asyncio
import time

import httpx

from app.core.config import get_settings
from app.knowledge import store
from app.knowledge.decision_schema import RouteDecision
from app.knowledge.metrics import JEV_FALLBACK, JEV_SECONDS
from app.knowledge.router import route as local_cascade

QUESTIONS = {
    "answer_source": ["llm_direct", "tenant_rag", "commercial_db", "call_state_db", "action_tool", "deflect"],
    "product_intent": ["yes", "no"],
    "needs_grounding": ["yes", "no"],
}


async def _call_jev(state: str) -> RouteDecision:
    # Confirm exact endpoint/field names against TypeSafe's API console;
    # this adapter confines that uncertainty to one function.
    s = get_settings()
    async with httpx.AsyncClient(timeout=s.knowledge_jev_timeout_ms / 1000) as client:
        r = await client.post(
            s.typesafe_api_url,
            headers={"Authorization": f"Bearer {s.typesafe_api_key}"},
            json={"state": state, "questions": QUESTIONS},
        )
        r.raise_for_status()
        d = r.json()
        src = d["answer_source"]["probabilities"]
        return RouteDecision(
            p_llm_direct=src["llm_direct"], p_tenant_rag=src["tenant_rag"],
            p_commercial_db=src["commercial_db"], p_call_state_db=src["call_state_db"],
            p_action_tool=src["action_tool"], p_deflect=src["deflect"],
            p_product_intent=d["product_intent"]["probabilities"]["yes"],
            p_needs_grounding=d["needs_grounding"]["probabilities"]["yes"],
            confidence=d.get("confidence", 0.0),
        )


async def decide(tenant_id: int, transcript: str, call_state: str = "") -> tuple[str, float, RouteDecision | None]:
    s = get_settings()
    if not (s.typesafe_api_url and s.typesafe_api_key):
        dest, conf = await local_cascade(tenant_id, transcript)
        return dest, conf, None

    state = f"CALL_STATE:\n{call_state or 'n/a'}\nCUSTOMER_TURN:\n{transcript}"
    t0 = time.perf_counter()
    try:
        decision, (top_sim, _hits) = await asyncio.gather(
            asyncio.wait_for(_call_jev(state), timeout=s.knowledge_jev_timeout_ms / 1000),
            store.probe(tenant_id, transcript),
        )
    except Exception as exc:
        JEV_FALLBACK.labels(reason=type(exc).__name__).inc()
        dest, conf = await local_cascade(tenant_id, transcript)
        return dest, conf, None
    JEV_SECONDS.observe(time.perf_counter() - t0)

    ranked = decision.ranked()
    top, second = ranked[0], ranked[1]
    if top[1] - second[1] < s.knowledge_ambiguous_margin:
        dest = "tenant_rag" if top_sim >= s.knowledge_sim_threshold else (
            "deflect" if decision.p_product_intent > 0.5 else "llm_direct")
    elif top[0] == "tenant_rag" and top_sim < s.knowledge_sim_threshold:
        dest = "deflect"
    elif top[1] < s.knowledge_confident_p:
        dest = "tenant_rag" if top_sim >= s.knowledge_sim_threshold else "llm_direct"
    else:
        dest = top[0]
    return dest, decision.confidence, decision