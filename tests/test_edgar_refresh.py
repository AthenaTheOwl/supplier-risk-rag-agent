from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.ingest.chunker import ChunkingConfig
from src.ingest.edgar_refresh import refresh_edgar_corpus, select_recent_filings
from src.ingest.manifest import IngestManifest
from src.retrieval.index import load_jsonl_corpus


class FakeEdgarClient:
    def __init__(self, submissions: dict[str, dict[str, Any]], html: dict[str, str]) -> None:
        self.submissions = submissions
        self.html = html
        self.filing_fetches: list[tuple[str, str, str]] = []

    async def fetch_company_submissions(self, cik: str) -> dict[str, Any]:
        return self.submissions[cik.zfill(10)]

    async def fetch_filing_html(self, cik: str, accession: str, primary_doc: str) -> str:
        self.filing_fetches.append((cik.zfill(10), accession, primary_doc))
        return self.html[accession]


def _submissions_payload() -> dict[str, Any]:
    return {
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q", "10-K", "10-K"],
                "accessionNumber": [
                    "0000320193-24-000080",
                    "0000320193-24-000081",
                    "0000320193-24-000123",
                    "",
                ],
                "filingDate": ["2024-08-01", "2024-08-02", "2024-11-01", "2024-12-01"],
                "reportDate": ["2024-08-01", "2024-06-29", "2024-09-28", "2024-12-01"],
                "primaryDocument": ["aapl-8k.htm", "aapl-10q.htm", "aapl-10k.htm", ""],
            }
        }
    }


def test_select_recent_filings_filters_targets_and_caps_results() -> None:
    selected = select_recent_filings(
        _submissions_payload(),
        cik="320193",
        filing_types=["10-K", "10-Q"],
        max_per_cik=1,
    )

    assert [filing.accession for filing in selected] == ["0000320193-24-000081"]
    assert selected[0].cik == "0000320193"
    assert selected[0].source_url.endswith("/000032019324000081/aapl-10q.htm")


def test_refresh_edgar_corpus_replaces_generated_jsonl_and_manifest(
    tmp_path: Path,
) -> None:
    manifest = IngestManifest.model_validate(
        {
            "ciks": [{"cik": "320193", "name": "Apple Inc.", "ticker": "AAPL"}],
            "filing_types": ["10-K", "10-Q"],
            "max_per_cik": 2,
        }
    )
    client = FakeEdgarClient(
        submissions={"0000320193": _submissions_payload()},
        html={
            "0000320193-24-000081": (
                "<html><body>Supplier capacity export controls logistics.</body></html>"
            ),
            "0000320193-24-000123": (
                "<html><body>Manufacturing disruption component sourcing risk.</body></html>"
            ),
        },
    )
    output = tmp_path / "generated" / "chunks.jsonl"
    refresh_manifest = tmp_path / "generated" / "manifest.json"
    output.parent.mkdir(parents=True)
    output.write_text("stale\n", encoding="utf-8")

    result = asyncio.run(
        refresh_edgar_corpus(
            manifest=manifest,
            client=client,
            output_path=output,
            refresh_manifest_path=refresh_manifest,
            source_manifest_path="data/sample_manifest.json",
            generated_at=datetime(2026, 5, 25, 12, 0, tzinfo=UTC),
            chunking_config=ChunkingConfig(max_words=20, overlap_words=0),
        )
    )

    chunks = load_jsonl_corpus(output)
    manifest_text = refresh_manifest.read_text(encoding="utf-8")
    assert result.filings_planned == 2
    assert result.filings_written == 2
    assert result.chunks_written == 2
    assert [chunk.accession for chunk in chunks] == [
        "0000320193-24-000081",
        "0000320193-24-000123",
    ]
    assert chunks[0].metadata["source"] == "edgar"
    assert chunks[0].metadata["company"] == "Apple Inc."
    assert '"chunks_written": 2' in manifest_text
    assert '"source_manifest": "data/sample_manifest.json"' in manifest_text
    assert "stale" not in output.read_text(encoding="utf-8")


def test_refresh_edgar_corpus_dry_run_skips_documents_and_writes(
    tmp_path: Path,
) -> None:
    manifest = IngestManifest.model_validate(
        {
            "ciks": [{"cik": "320193", "name": "Apple Inc."}],
            "filing_types": ["10-K"],
            "max_per_cik": 2,
        }
    )
    client = FakeEdgarClient(submissions={"0000320193": _submissions_payload()}, html={})
    output = tmp_path / "chunks.jsonl"
    refresh_manifest = tmp_path / "manifest.json"

    result = asyncio.run(
        refresh_edgar_corpus(
            manifest=manifest,
            client=client,
            output_path=output,
            refresh_manifest_path=refresh_manifest,
            dry_run=True,
        )
    )

    assert result.filings_planned == 1
    assert result.filings_written == 0
    assert client.filing_fetches == []
    assert not output.exists()
    assert not refresh_manifest.exists()
