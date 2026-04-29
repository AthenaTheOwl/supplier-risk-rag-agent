"""Local corpus and optional Chroma index helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DocumentChunk:
    cik: str
    accession: str
    section: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0

    @property
    def id(self) -> str:
        safe_section = self.section.lower().replace(" ", "-")
        return f"{self.cik}:{self.accession}:{safe_section}:{self.chunk_index}"

    @property
    def company(self) -> str:
        return str(self.metadata.get("company", "Unknown company"))

    @classmethod
    def from_record(cls, record: dict[str, Any], default_index: int = 0) -> DocumentChunk:
        metadata = dict(record.get("metadata") or {})
        chunk_index = int(record.get("chunk_index", metadata.get("chunk_index", default_index)))
        metadata.setdefault("chunk_index", chunk_index)
        return cls(
            cik=str(record["cik"]).zfill(10),
            accession=str(record["accession"]),
            section=str(record.get("section", metadata.get("section", "Unknown"))),
            text=str(record["text"]).strip(),
            metadata=metadata,
            chunk_index=chunk_index,
        )

    def chroma_metadata(self) -> dict[str, str | int | float | bool]:
        base: dict[str, str | int | float | bool] = {
            "cik": self.cik,
            "accession": self.accession,
            "section": self.section,
            "chunk_index": self.chunk_index,
        }
        for key, value in self.metadata.items():
            if isinstance(value, str | int | float | bool):
                base[key] = value
        return base


def _jsonl_paths(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*.jsonl"))
    return [path]


def load_jsonl_corpus(path: str | Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for jsonl_path in _jsonl_paths(Path(path)):
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line_index, line in enumerate(handle):
                stripped = line.strip()
                if not stripped:
                    continue
                chunks.append(DocumentChunk.from_record(json.loads(stripped), line_index))
    return chunks


def load_sample_corpus(root: str | Path | None = None) -> list[DocumentChunk]:
    base = Path(root) if root else repo_root()
    return load_jsonl_corpus(base / "data" / "sample_corpus")


def build_chroma_collection(
    chunks: Iterable[DocumentChunk],
    *,
    persist_path: str | Path,
    collection_name: str = "supplier_risk",
) -> object:
    """Build a local Chroma collection from already embedded text.

    The app and CI use deterministic in-memory retrieval by default. This helper is present for
    local full-ingest workflows that want persistent Chroma storage.
    """

    import chromadb

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(name=collection_name)
    chunk_list = list(chunks)
    if not chunk_list:
        return collection
    collection.upsert(
        ids=[chunk.id for chunk in chunk_list],
        documents=[chunk.text for chunk in chunk_list],
        metadatas=[chunk.chroma_metadata() for chunk in chunk_list],
    )
    return collection
