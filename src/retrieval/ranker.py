"""Hybrid retrieval over supplier-risk filing chunks."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rank_bm25 import BM25Okapi

from src.retrieval.index import DocumentChunk, load_sample_corpus

if TYPE_CHECKING:
    from src.retrieval.reranker import RerankerLike

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")

STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "between",
    "but",
    "can",
    "company",
    "companies",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "into",
    "its",
    "may",
    "our",
    "the",
    "their",
    "they",
    "this",
    "that",
    "were",
    "what",
    "when",
    "which",
    "with",
    "would",
}


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOP_WORDS]


class EmbedderLike(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return vectors for texts."""


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float
    bm25_score: float
    vector_score: float
    overlap: int


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class HybridRanker:
    """BM25 plus deterministic vector retrieval.

    OpenAI embeddings can be injected by passing another embedder. The default local embedder is
    imported lazily to avoid a circular import at module load time.
    """

    def __init__(
        self,
        chunks: Iterable[DocumentChunk],
        embedder: EmbedderLike | None = None,
        reranker: RerankerLike | None = None,
        candidate_pool: int = 50,
    ) -> None:
        from src.retrieval.embedder import HashingEmbedder

        self.chunks = list(chunks)
        self._tokenized_docs = [tokenize(chunk.text) for chunk in self.chunks]
        self._doc_token_sets = [set(tokens) for tokens in self._tokenized_docs]
        self._bm25 = BM25Okapi(self._tokenized_docs) if self._tokenized_docs else None
        self._embedder = embedder or HashingEmbedder()
        self._doc_vectors = self._embedder.embed_texts([chunk.text for chunk in self.chunks])
        self._reranker = reranker
        self._candidate_pool = candidate_pool

    @classmethod
    def from_sample_corpus(cls) -> HybridRanker:
        return cls(load_sample_corpus())

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        query_tokens = tokenize(query)
        query_token_set = set(query_tokens)
        if not query_tokens or not self.chunks:
            return []

        bm25_scores = list(self._bm25.get_scores(query_tokens)) if self._bm25 else []
        max_bm25 = max(bm25_scores) if bm25_scores else 0.0
        query_vector = self._embedder.embed_texts([query])[0]
        results: list[SearchResult] = []

        for index, chunk in enumerate(self.chunks):
            if filters and not self._matches_filters(chunk, filters):
                continue
            bm25_raw = float(bm25_scores[index]) if bm25_scores else 0.0
            bm25_norm = bm25_raw / max_bm25 if max_bm25 > 0 else 0.0
            vector_score = max(0.0, _cosine(query_vector, self._doc_vectors[index]))
            overlap = len(query_token_set & self._doc_token_sets[index])
            overlap_ratio = overlap / max(len(query_token_set), 1)
            if overlap == 0:
                combined = 0.03 * vector_score
            else:
                combined = (0.60 * bm25_norm) + (0.25 * vector_score) + (0.15 * overlap_ratio)
            results.append(
                SearchResult(
                    chunk=chunk,
                    score=combined,
                    bm25_score=bm25_norm,
                    vector_score=vector_score,
                    overlap=overlap,
                )
            )

        sorted_results = sorted(results, key=lambda result: result.score, reverse=True)
        if self._reranker is None:
            return sorted_results[:top_k]
        # Pull a wider candidate pool for the reranker. The pool size is bounded
        # to avoid wasting cross-encoder calls on clearly-irrelevant chunks.
        pool = sorted_results[: max(self._candidate_pool, top_k)]
        return self._reranker.rerank(query, pool, top_k)

    @staticmethod
    def _matches_filters(chunk: DocumentChunk, filters: dict[str, object]) -> bool:
        for key, expected in filters.items():
            if key == "cik":
                actual = chunk.cik
            elif key == "accession":
                actual = chunk.accession
            elif key == "section":
                actual = chunk.section
            else:
                actual = chunk.metadata.get(key)
            if isinstance(expected, list | tuple | set):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True
