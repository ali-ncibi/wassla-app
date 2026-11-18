import hashlib
import math
import re

import httpx
from langchain_core.embeddings import Embeddings


class OpenAICompatibleEmbeddings(Embeddings):
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _embed(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                json={"model": self.model, "input": texts},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        ordered = sorted(data["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in ordered]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class StubEmbeddings(Embeddings):
    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in re.findall(r"\w+", text.lower()):
            h = hashlib.sha256(tok.encode()).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            v[idx] += 1.0 if h[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)
