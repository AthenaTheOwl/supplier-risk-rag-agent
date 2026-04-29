"""Filing text extraction and chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from src.retrieval.index import DocumentChunk

SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ChunkingConfig:
    max_words: int = 180
    overlap_words: int = 35


def normalize_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()
    return normalize_text(soup.get_text(" "))


def chunk_text(
    text: str,
    *,
    cik: str,
    accession: str,
    section: str,
    metadata: dict[str, Any] | None = None,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    config = config or ChunkingConfig()
    words = normalize_text(text).split()
    if not words:
        return []
    if config.max_words <= 0:
        raise ValueError("max_words must be positive")
    if config.overlap_words < 0 or config.overlap_words >= config.max_words:
        raise ValueError("overlap_words must be non-negative and smaller than max_words")

    chunks: list[DocumentChunk] = []
    step = config.max_words - config.overlap_words
    for chunk_index, start in enumerate(range(0, len(words), step)):
        window = words[start : start + config.max_words]
        if not window:
            break
        chunk_metadata = dict(metadata or {})
        chunk_metadata.setdefault("section", section)
        chunk_metadata["chunk_index"] = chunk_index
        chunks.append(
            DocumentChunk(
                cik=cik.zfill(10),
                accession=accession,
                section=section,
                text=" ".join(window),
                metadata=chunk_metadata,
                chunk_index=chunk_index,
            )
        )
        if start + config.max_words >= len(words):
            break
    return chunks


def chunk_filing_html(
    html: str,
    *,
    cik: str,
    accession: str,
    section: str = "Filing",
    metadata: dict[str, Any] | None = None,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    return chunk_text(
        html_to_text(html),
        cik=cik,
        accession=accession,
        section=section,
        metadata=metadata,
        config=config,
    )
