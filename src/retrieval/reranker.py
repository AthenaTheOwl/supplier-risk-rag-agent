"""Cross-encoder reranker. Optional layer on top of HybridRanker.

Used in experiments/01-cross-encoder-rerank/. Off by default in CI to keep
the baseline reproducible without model downloads.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from src.retrieval.ranker import SearchResult


class RerankerLike(Protocol):
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Reorder candidates by learned relevance, return top_k."""


class CrossEncoderReranker:
    """Cross-encoder reranker via sentence-transformers.

    Default model: cross-encoder/ms-marco-MiniLM-L-6-v2 (~80 MB; CPU-friendly).
    Alternatives worth trying: BAAI/bge-reranker-base (~280 MB, stronger),
    BAAI/bge-reranker-large (~1.3 GB, strongest).

    The model is lazy-loaded on first rerank() call, so importing this module
    has no network or memory cost.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self.model_name = model_name
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # Imported lazily so the module is importable without sentence-transformers
        # installed. Production CI does not need this dependency.
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        if not results:
            return []
        self._ensure_loaded()
        assert self._model is not None  # type narrowing for mypy

        pairs = [[query, result.chunk.text] for result in results]
        scores = self._model.predict(pairs)
        # `scores` is a numpy array; cast to float so downstream stays json-safe.
        scored = sorted(
            zip((float(score) for score in scores), results, strict=True),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [replace(result, score=score) for score, result in scored[:top_k]]
