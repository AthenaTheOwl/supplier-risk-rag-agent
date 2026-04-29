"""Embedding providers.

The default hashing embedder is deterministic and keyless so CI and evals do not need vendor
credentials. OpenAI embeddings are available for live ingestion or demos when a caller passes a
BYOK key explicitly.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from src.config import DEFAULT_EMBEDDING_MODEL, Keys, MissingKeyError
from src.retrieval.ranker import tokenize


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each text."""


@dataclass(frozen=True)
class HashingEmbedder:
    dimensions: int = 128

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0 for _ in range(self.dimensions)]
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbedder:
    def __init__(self, keys: Keys, model: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if not keys.openai_key:
            raise MissingKeyError("OpenAI API key is required for live embedding calls.")
        from openai import OpenAI

        self._client = OpenAI(api_key=keys.openai_key)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
