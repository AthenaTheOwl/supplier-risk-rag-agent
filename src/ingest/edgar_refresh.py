"""EDGAR refresh pipeline that writes generated chunks in corpus JSONL shape."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from src.ingest.chunker import ChunkingConfig, chunk_filing_html
from src.ingest.manifest import IngestManifest, ManifestCompany
from src.retrieval.index import DocumentChunk


class EdgarClient(Protocol):
    async def fetch_company_submissions(self, cik: str) -> dict[str, Any]:
        """Return the SEC company submissions JSON payload for one CIK."""

    async def fetch_filing_html(self, cik: str, accession: str, primary_doc: str) -> str:
        """Return raw HTML for one filing document."""


@dataclass(frozen=True)
class FilingCandidate:
    cik: str
    accession: str
    form: str
    filing_date: str
    report_date: str | None
    primary_document: str

    @property
    def source_url(self) -> str:
        accession_no_dash = self.accession.replace("-", "")
        normalized_cik = str(int(self.cik))
        return (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{normalized_cik}/{accession_no_dash}/{self.primary_document}"
        )


@dataclass(frozen=True)
class CompanyRefreshResult:
    company: ManifestCompany
    planned_filings: list[FilingCandidate]
    fetched_filings: list[FilingCandidate]
    chunk_count: int


@dataclass(frozen=True)
class RefreshResult:
    generated_at: datetime
    dry_run: bool
    output_path: Path
    manifest_path: Path | None
    companies: list[CompanyRefreshResult]

    @property
    def filings_planned(self) -> int:
        return sum(len(company.planned_filings) for company in self.companies)

    @property
    def filings_written(self) -> int:
        return sum(len(company.fetched_filings) for company in self.companies)

    @property
    def chunks_written(self) -> int:
        return sum(company.chunk_count for company in self.companies)


def select_recent_filings(
    submissions: dict[str, Any],
    *,
    cik: str,
    filing_types: Sequence[str],
    max_per_cik: int,
) -> list[FilingCandidate]:
    """Select the newest complete target filings from an SEC submissions payload."""

    if max_per_cik < 1:
        return []

    recent = submissions.get("filings", {}).get("recent", {})
    if not isinstance(recent, dict):
        return []

    forms = _as_list(recent.get("form"))
    accessions = _as_list(recent.get("accessionNumber"))
    filing_dates = _as_list(recent.get("filingDate"))
    report_dates = _as_list(recent.get("reportDate"))
    primary_docs = _as_list(recent.get("primaryDocument"))
    target_forms = {form.upper() for form in filing_types}

    selected: list[FilingCandidate] = []
    for index, form in enumerate(forms):
        if form.upper() not in target_forms:
            continue
        accession = _value_at(accessions, index)
        filing_date = _value_at(filing_dates, index)
        primary_doc = _value_at(primary_docs, index)
        if not accession or not filing_date or not primary_doc:
            continue
        selected.append(
            FilingCandidate(
                cik=str(cik).zfill(10),
                accession=accession,
                form=form,
                filing_date=filing_date,
                report_date=_value_at(report_dates, index) or None,
                primary_document=primary_doc,
            )
        )
        if len(selected) >= max_per_cik:
            break
    return selected


async def refresh_edgar_corpus(
    *,
    manifest: IngestManifest,
    client: EdgarClient,
    output_path: str | Path = "data/generated/edgar_corpus/chunks.jsonl",
    refresh_manifest_path: str | Path | None = "data/generated/edgar_corpus/manifest.json",
    source_manifest_path: str | Path | None = None,
    dry_run: bool = False,
    generated_at: datetime | None = None,
    chunking_config: ChunkingConfig | None = None,
) -> RefreshResult:
    """Refresh configured EDGAR filings into a generated corpus JSONL file.

    Dry runs fetch only company submissions metadata, select target filings, and skip filing
    document downloads plus filesystem writes.
    """

    generated_at = generated_at or datetime.now(UTC)
    output = Path(output_path)
    manifest_output = Path(refresh_manifest_path) if refresh_manifest_path else None

    all_chunks: list[DocumentChunk] = []
    company_results: list[CompanyRefreshResult] = []

    for company in manifest.ciks:
        submissions = await client.fetch_company_submissions(company.cik)
        planned = select_recent_filings(
            submissions,
            cik=company.cik,
            filing_types=manifest.filing_types,
            max_per_cik=manifest.max_per_cik,
        )
        fetched: list[FilingCandidate] = []
        company_chunk_count = 0

        if not dry_run:
            for filing in planned:
                html = await client.fetch_filing_html(
                    company.cik,
                    filing.accession,
                    filing.primary_document,
                )
                chunks = chunk_filing_html(
                    html,
                    cik=company.cik,
                    accession=filing.accession,
                    section="Filing",
                    metadata={
                        "company": company.name,
                        "ticker": company.ticker or "",
                        "filing_type": filing.form,
                        "filing_date": filing.filing_date,
                        "report_date": filing.report_date or "",
                        "primary_document": filing.primary_document,
                        "source": "edgar",
                        "source_url": filing.source_url,
                    },
                    config=chunking_config,
                )
                all_chunks.extend(chunks)
                fetched.append(filing)
                company_chunk_count += len(chunks)

        company_results.append(
            CompanyRefreshResult(
                company=company,
                planned_filings=planned,
                fetched_filings=fetched,
                chunk_count=company_chunk_count,
            )
        )

    result = RefreshResult(
        generated_at=generated_at,
        dry_run=dry_run,
        output_path=output,
        manifest_path=manifest_output,
        companies=company_results,
    )

    if not dry_run:
        write_chunks_jsonl(all_chunks, output)
        if manifest_output is not None:
            write_refresh_manifest(
                result,
                manifest_path=manifest_output,
                source_manifest_path=source_manifest_path,
            )

    return result


def write_chunks_jsonl(chunks: Sequence[DocumentChunk], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output.with_suffix(output.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(_chunk_record(chunk), sort_keys=True))
            handle.write("\n")
    tmp_path.replace(output)


def write_refresh_manifest(
    result: RefreshResult,
    *,
    manifest_path: str | Path,
    source_manifest_path: str | Path | None = None,
) -> None:
    output = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output.with_suffix(output.suffix + ".tmp")
    payload = refresh_manifest_payload(result, source_manifest_path=source_manifest_path)
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(output)


def refresh_manifest_payload(
    result: RefreshResult,
    *,
    source_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "generated_at": result.generated_at.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "dry_run": result.dry_run,
        "source_manifest": str(source_manifest_path) if source_manifest_path else None,
        "chunk_file": result.output_path.name,
        "totals": {
            "companies": len(result.companies),
            "filings_planned": result.filings_planned,
            "filings_written": result.filings_written,
            "chunks_written": result.chunks_written,
        },
        "companies": [
            {
                "cik": company_result.company.cik,
                "name": company_result.company.name,
                "ticker": company_result.company.ticker,
                "chunk_count": company_result.chunk_count,
                "planned_filings": [
                    _filing_record(filing) for filing in company_result.planned_filings
                ],
                "fetched_filings": [
                    _filing_record(filing) for filing in company_result.fetched_filings
                ],
            }
            for company_result in result.companies
        ],
    }


def _as_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value]


def _value_at(values: Sequence[str], index: int) -> str:
    if index >= len(values):
        return ""
    return values[index].strip()


def _chunk_record(chunk: DocumentChunk) -> dict[str, Any]:
    return {
        "cik": chunk.cik,
        "accession": chunk.accession,
        "section": chunk.section,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "metadata": chunk.metadata,
    }


def _filing_record(filing: FilingCandidate) -> dict[str, Any]:
    return {
        "cik": filing.cik,
        "accession": filing.accession,
        "form": filing.form,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
        "primary_document": filing.primary_document,
        "source_url": filing.source_url,
    }
