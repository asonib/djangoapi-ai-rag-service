"""Deterministic, offline test doubles for the AI infrastructure interfaces."""
import hashlib
import re
from typing import Dict, List, Sequence, Tuple

import numpy as np

from app.services.interfaces.embedding_service_interface import IEmbeddingService
from app.services.interfaces.llm_service_interface import ILLMService, LLMResult
from app.services.interfaces.vector_store_interface import IVectorStore

DIM = 384


class FakeEmbeddingService(IEmbeddingService):
    """Hashed bag-of-words embeddings: texts sharing words get high cosine similarity."""

    @property
    def model_name(self) -> str:
        return "fake-hash-embedding"

    @property
    def dimension(self) -> int:
        return DIM

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(DIM, dtype=np.float32)
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            if len(tok) < 3:
                continue
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts]) if texts else np.zeros((0, DIM), np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)


class InMemoryVectorStore(IVectorStore):
    def __init__(self):
        self.data: Dict[str, Dict[int, np.ndarray]] = {}

    @property
    def backend_name(self) -> str:
        return "faiss"

    def add(self, namespace: str, ids: Sequence[int], vectors: np.ndarray) -> None:
        bucket = self.data.setdefault(namespace, {})
        for i, v in zip(ids, vectors):
            bucket[int(i)] = np.asarray(v, dtype=np.float32)

    def remove(self, namespace: str, ids: Sequence[int]) -> int:
        bucket = self.data.get(namespace, {})
        return sum(1 for i in ids if bucket.pop(int(i), None) is not None)

    def search(self, namespace: str, query_vector: np.ndarray, top_k: int) -> List[Tuple[int, float]]:
        bucket = self.data.get(namespace, {})
        scored = sorted(((i, float(np.dot(v, query_vector))) for i, v in bucket.items()),
                        key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self, namespace: str) -> int:
        return len(self.data.get(namespace, {}))


class FakeLLMService(ILLMService):
    def __init__(self, reply: str = "fake answer"):
        self.reply = reply
        self.calls: List[dict] = []

    @property
    def model_name(self) -> str:
        return "fake-claude"

    def generate(self, system, messages) -> LLMResult:
        self.calls.append({"system": system, "messages": messages})
        return LLMResult(text=self.reply, model=self.model_name, input_tokens=11, output_tokens=7)
