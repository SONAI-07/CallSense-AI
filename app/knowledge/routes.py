import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.knowledge import store
from app.knowledge.embeddings import embed
from app.knowledge.models import KnowledgeChunk

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class DocIn(BaseModel):
    title: str
    text: str


def chunk(text: str, size: int = 600, overlap: int = 80):
    words = text.split()
    out, i = [], 0
    while i < len(words):
        out.append(" ".join(words[i:i + size]))
        i += size - overlap
    return out


@router.post("/documents", status_code=201)
async def ingest(payload: DocIn, tenant=Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    doc_id = uuid.uuid4().hex[:12]
    pieces = chunk(payload.text)
    vecs = embed(pieces)
    for i, (p, v) in enumerate(zip(pieces, vecs)):
        db.add(KnowledgeChunk(tenant_id=tenant.id, doc_id=doc_id, title=payload.title,
                              chunk_index=i, text=p, embedding=v.tolist()))
    await db.commit()
    store.invalidate(tenant.id)
    return {"doc_id": doc_id, "chunks": len(pieces)}


@router.get("/documents")
async def list_documents(tenant=Depends(get_current_tenant)):
    return await store.list_docs(tenant.id)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: str, tenant=Depends(get_current_tenant)):
    await store.delete_doc(tenant.id, doc_id)