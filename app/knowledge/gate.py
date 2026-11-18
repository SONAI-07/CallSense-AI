import time

from app.core.config import get_settings
from app.knowledge import facts, store
from app.knowledge.jev_router import decide
from app.knowledge.metrics import GATE_SECONDS, ROUTE_TOTAL

GROUND = (
    "\n[GROUND_TRUTH]\n{lines}\n"
    "Rules: answer product/spec/policy questions ONLY from GROUND_TRUTH. "
    "If the answer is not present, say you will confirm and send details — never invent numbers.\n"
)
DEFLECT = (
    "\n[GROUND_TRUTH]\n(empty)\n"
    "Rules: this question needs verified product detail you do not have. Acknowledge briefly, "
    "say you will confirm and send the exact details, then continue the pitch.\n"
)
FACTS = "\n[VERIFIED_FACTS]\n{body}\nRules: use these facts verbatim for numbers/status; do not guess.\n"


async def build_context(tenant_id: int, dest: str, call_sid: str | None) -> str:
    if dest == "tenant_rag":
        _top, hits = await store.probe(tenant_id, "")  # placeholder replaced below
        return GROUND.format(lines="")
    return ""


async def context_for(tenant_id: int, transcript: str, call_sid: str | None = None, call_state: str = ""):
    s = get_settings()
    t0 = time.perf_counter()
    dest, conf, _decision = await decide(tenant_id, transcript, call_state)
    mode = "shadow" if (s.knowledge_shadow_mode or not s.knowledge_enabled) else "live"
    ROUTE_TOTAL.labels(destination=dest, mode=mode).inc()
    GATE_SECONDS.observe(time.perf_counter() - t0)

    if mode == "shadow":
        return "", dest, conf, time.perf_counter() - t0

    if dest == "tenant_rag":
        _top, hits = await store.probe(tenant_id, transcript)
        ctx = GROUND.format(lines="\n".join(f"- {c.text}" for _s, c in hits))
    elif dest == "commercial_db":
        ctx = FACTS.format(body=await facts.commercial(tenant_id))
    elif dest == "call_state_db":
        ctx = FACTS.format(body=await facts.call_state(tenant_id, call_sid))
    elif dest == "deflect":
        ctx = DEFLECT
    else:
        ctx = ""  # llm_direct, or action_tool handled by the existing action node
    return ctx, dest, conf, time.perf_counter() - t0