"""Agent tools over the retrieval layer."""

from __future__ import annotations

from dataclasses import dataclass

from src.retrieval.index import DocumentChunk
from src.retrieval.ranker import HybridRanker, SearchResult


@dataclass
class RetrievalTools:
    ranker: HybridRanker

    def retrieve(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        return self.ranker.search(query, top_k=top_k)

    def filter_by_cik(self, query: str, cik: str, *, top_k: int = 5) -> list[SearchResult]:
        return self.ranker.search(query, top_k=top_k, filters={"cik": cik.zfill(10)})

    def get_section(self, cik: str, section: str) -> list[DocumentChunk]:
        return [
            chunk
            for chunk in self.ranker.chunks
            if chunk.cik == cik.zfill(10) and chunk.section.lower() == section.lower()
        ]
