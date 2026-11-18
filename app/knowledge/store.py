import numpy as np
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.knowledge.embeddings import embed
from app.knowledge.models import KnowledgeChunk

_cache: dict[int, tuple[np.ndarray, list]] = {}


async def _load(tenant_id: int):
    async with AsyncSessionLocal() as s:
        rows = list((await s.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == tenant_id).order_by(KnowledgeChunk.id)
        )).scalars().all())
    if not rows:
        return np.zeros((0, 1), dtype=np.float32), []
    mat = np.asarray([r.embedding for r in rows], dtype=np.float32)
    mat /= np.clip(np.linalg.norm(mat, axis=1, keepdims=True), 1e-9, None)
    return mat, rows


async def get_matrix(tenant_id: int):
    if tenant_id not in _cache:
        _cache[tenant_id] = await _load(tenant_id)
    return _cache[tenant_id]


async def probe(tenant_id: int, query: str, k: int | None = None):
    k = k or get_settings().knowledge_top_k
    mat, rows = await get_matrix(tenant_id)
    if not rows:
        return 0.0, []
    sims = mat @ embed([query])[0]
    idx = np.argsort(-sims)[:k]
    return float(sims[idx[0]]), [(float(sims[i]), rows[i]) for i in idx]


def invalidate(tenant_id: int):
    _cache.pop(tenant_id, None)


async def list_docs(tenant_id: int):
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(
            select(KnowledgeChunk.doc_id, KnowledgeChunk.title)
            .where(KnowledgeChunk.tenant_id == tenant_id).distinct()
        )).all()
    return [{"doc_id": r[0], "title": r[1]} for r in rows]


async def delete_doc(tenant_id: int, doc_id: str):
    async with AsyncSessionLocal() as s:
        async with s.begin():
            await s.execute(delete(KnowledgeChunk).where(
                KnowledgeChunk.tenant_id == tenant_id, KnowledgeChunk.doc_id == doc_id
            ))
    invalidate(tenant_id)