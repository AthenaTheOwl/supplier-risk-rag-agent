"""Cross-encoder reranker. Optional layer on top of HybridRanker.

Used in experiments/01-cross-encoder-rerank/ and shipped as opt-in per
DEC-RET-006. Off by default in CI to keep the baseline reproducible
without model downloads.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Protocol

from src.retrieval.ranker import SearchResult

logger = logging.getLogger(__name__)


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

    If model load fails (missing dep, network error, bad model name), the
    reranker logs the failure and falls back to returning the input
    candidates' top_k unchanged. Hybrid retrieval continues; the opt-in
    path degrades to the deterministic default rather than raising.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self.model_name = model_name
        self._model: object | None = None
        self._load_failed = False

    def _ensure_loaded(self) -> None:
        if self._model is not None or self._load_failed:
            return
        # Imported lazily so the module is importable without sentence-transformers
        # installed. Production CI does not need this dependency.
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        except Exception as exc:
            self._load_failed = True
            logger.warning(
                "CrossEncoderReranker: model load failed for %s (%s: %s); "
                "falling back to hybrid ordering.",
                self.model_name,
                exc.__class__.__name__,
                exc,
            )

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        if not results:
            return []
        self._ensure_loaded()
        if self._model is None:
            # Load failed: return the input order's top_k unchanged.
            return list(results[:top_k])

        pairs = [[query, result.chunk.text] for result in results]
        scores = self._model.predict(pairs)  # type: ignore[attr-defined]
        # `scores` is a numpy array; cast to float so downstream stays json-safe.
        scored = sorted(
            zip((float(score) for score in scores), results, strict=True),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [replace(result, score=score) for score, result in scored[:top_k]]
