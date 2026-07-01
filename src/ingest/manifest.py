"""Manifest parsing for EDGAR ingestion."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ManifestCompany(BaseModel):
    cik: str
    name: str
    ticker: str | None = None

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        return str(value).strip().zfill(10)


class IngestManifest(BaseModel):
    ciks: list[ManifestCompany]
    filing_types: list[str] = Field(default_factory=lambda: ["10-K", "20-F", "10-Q"])
    max_per_cik: int = 2

    @field_validator("ciks")
    @classmethod
    def no_duplicate_ciks(cls, value: list[ManifestCompany]) -> list[ManifestCompany]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for company in value:
            if company.cik in seen:
                duplicates.append(company.cik)
            seen.add(company.cik)
        if duplicates:
            raise ValueError(f"Duplicate CIK entries: {', '.join(sorted(set(duplicates)))}")
        return value


def load_manifest(path: str | Path) -> IngestManifest:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        # Wrong --manifest path is the common operator mistake; give the path back.
        raise SystemExit(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest is not valid JSON ({path}): {exc}") from exc
    return IngestManifest.model_validate(data)
