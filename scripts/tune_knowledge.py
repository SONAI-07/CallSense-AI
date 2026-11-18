import asyncio
import itertools
import json

from app.core.config import get_settings
from app.knowledge import store
from app.knowledge.embeddings import embed
from app.knowledge.router import route

SAMPLE_KB = [
    "CallSense AI supports Hindi (hi-IN) and English (en-IN) outbound calls with native voices.",
    "Native integrations: HubSpot, Salesforce, Google Calendar, WhatsApp Business, REST webhooks.",
    "Refund policy: unused minutes refundable within 14 days of purchase.",
    "Security: SOC 2 Type II, GDPR-ready, consent logged and recordings encrypted at rest.",
    "Minutes reset monthly and do not roll over; telephony billed at cost.",
]


class _C:
    pass


async def main():
    vecs = embed(SAMPLE_KB)
    chunks = []
    for i, t in enumerate(SAMPLE_KB):
        c = _C(); c.text = t; c.embedding = vecs[i].tolist(); chunks.append(c)
    store._cache[1] = (vecs, chunks)

    golden = json.load(open("scripts/knowledge_golden.json"))
    s = get_settings()
    best = None
    for high, margin, sim in itertools.product(
        [0.55, 0.60, 0.62, 0.65, 0.70], [0.04, 0.06, 0.08, 0.10], [0.45, 0.50, 0.55, 0.60]
    ):
        s.knowledge_sem_high, s.knowledge_sem_margin, s.knowledge_sim_threshold = high, margin, sim
        correct = 0
        per = {}
        for item in golden:
            dest, _ = await route(1, item["transcript"])
            ok = dest == item["destination"]
            correct += ok
            p = per.setdefault(item["destination"], [0, 0])
            p[1] += 1; p[0] += ok
        acc = correct / len(golden)
        if best is None or acc > best[0]:
            best = (acc, high, margin, sim, per)
    print(json.dumps({
        "accuracy": best[0], "knowledge_sem_high": best[1],
        "knowledge_sem_margin": best[2], "knowledge_sim_threshold": best[3],
        "per_class_correct_over_total": best[4],
    }, indent=2))


asyncio.run(main())