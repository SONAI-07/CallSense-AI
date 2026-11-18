from functools import lru_cache
import numpy as np
from app.core.config import get_settings


@lru_cache
def _model():
    from fastembed import TextEmbedding
    return TextEmbedding(get_settings().embedding_model)


def embed(texts: list[str]) -> np.ndarray:
    vecs = np.asarray(list(_model().embed(list(texts))), dtype=np.float32)
    if vecs.ndim == 1:
        vecs = vecs[None, :]
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-9, None)