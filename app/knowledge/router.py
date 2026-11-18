import re

from app.core.config import get_settings
from app.knowledge import store
from app.knowledge.embeddings import embed

K_EX = [
    "does it support hindi outbound calls", "what is the refund policy",
    "which crm do you integrate with", "tell me about the case study",
    "what are the product specifications", "is there a setup fee",
]
D_EX = [
    "hello how are you", "thanks that sounds good", "i am busy right now",
    "can you repeat that", "yes go ahead", "not interested thanks",
]
PRODUCT_INTENT = re.compile(r"\b(price|pricing|plan|cost|feature|support|integrat|policy|refund|spec|minute|language|voice|sla|security|uptime|case study)\b", re.I)
GREETING = re.compile(r"^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|ha|hmm)\b", re.I)
ACTION_RE = re.compile(r"\b(book|schedule|call me|send|whatsapp|email me)\b", re.I)
COMMERCIAL_RE = re.compile(r"\b(how much|cost|price|pricing|plan|per month|minutes included)\b", re.I)
CALLSTATE_RE = re.compile(r"\b(did you|did i|already send|already sent|brochure|last call)\b", re.I)

_k = _d = None


def _ex():
    global _k, _d
    if _k is None:
        _k = embed(K_EX)
        _d = embed(D_EX)
    return _k, _d


async def route(tenant_id: int, transcript: str) -> tuple[str, float]:
    s = get_settings()
    t = transcript.strip().lower()
    if GREETING.match(t) and len(t.split()) <= 6:
        return "llm_direct", 0.9
    if ACTION_RE.search(t):
        return "action_tool", 0.9
    if COMMERCIAL_RE.search(t):
        return "commercial_db", 0.8
    if CALLSTATE_RE.search(t):
        return "call_state_db", 0.8
    k, d = _ex()
    q = embed([transcript])[0]
    ks, ds = float((k @ q).max()), float((d @ q).max())
    margin = ks - ds
    if ks >= s.knowledge_sem_high and margin >= s.knowledge_sem_margin:
        top, _ = await store.probe(tenant_id, transcript)
        return ("tenant_rag", ks) if top >= s.knowledge_sim_threshold else ("deflect", ks)
    if ds >= s.knowledge_sem_high and margin <= -s.knowledge_sem_margin:
        return "llm_direct", ds
    top, _ = await store.probe(tenant_id, transcript)
    if top >= s.knowledge_sim_threshold:
        return "tenant_rag", top
    return ("deflect", 0.5) if PRODUCT_INTENT.search(t) else ("llm_direct", 0.5)