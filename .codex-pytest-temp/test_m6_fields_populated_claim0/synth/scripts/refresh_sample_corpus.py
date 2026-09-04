#!/usr/bin/env python3
"""Refresh a small EDGAR fixture corpus at ``data/refreshed_corpus/``.

This script wraps the existing EDGAR refresh pipeline at
``src/ingest/edgar_refresh.py`` with a three-CIK manifest (NVDA, TSM,
AMAT) and writes a bounded fixture set (2 chunks per CIK by default).
The canonical eval corpus at ``data/sample_corpus/`` is not touched.

Network policy: the script makes 3-5 EDGAR requests (one company
submissions JSON + one filing HTML per CIK). All requests honor the
SEC's User-Agent + 10 req/s rate cap policy via ``SECClient`` (see
``src/ingest/sec_client.py``).

Network fallback: when the EDGAR fetch fails (sandbox without network,
rate-limit, etc.) the script writes a small offline stub fixture so the
``data/refreshed_corpus/`` artifact lands either way. The stub is
flagged in the refresh manifest's ``source`` field so a reviewer can
tell which path produced the fixture.

Usage:
    python scripts/refresh_sample_corpus.py \\
        [--output data/refreshed_corpus/chunks.jsonl] \\
        [--max-chunks-per-cik 2]

Exits 0 on success (live or fallback). Exits 1 on unexpected errors.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

# Allow running this script directly (``python scripts/refresh_sample_corpus.py``)
# as well as via ``python -m scripts.refresh_sample_corpus``.
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rich.console import Console  # noqa: E402

from src.ingest.edgar_refresh import (  # noqa: E402
    CompanyRefreshResult,
    RefreshResult,
    refresh_edgar_corpus,
)
from src.ingest.manifest import IngestManifest, ManifestCompany  # noqa: E402
from src.ingest.sec_client import SECClient, SECClientError  # noqa: E402
from src.retrieval.index import DocumentChunk, load_jsonl_corpus  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
console = Console()

# Three-CIK list per the workflow spec. NVDA + TSM + AMAT cover the
# fab + foundry + equipment supplier surface that the sample corpus
# already covers.
REFRESH_CIKS: list[ManifestCompany] = [
    ManifestCompany(cik="0001045810", name="NVIDIA Corp", ticker="NVDA"),
    ManifestCompany(
        cik="0001046179",
        name="Taiwan Semiconductor Manufacturing Co Ltd",
        ticker="TSM",
    ),
    ManifestCompany(cik="0000006951", name="Applied Materials Inc.", ticker="AMAT"),
]

# Target 10-K (annual) and 20-F (foreign private issuer annual; TSM
# files this shape) so each CIK lands on a single recent annual
# report. ``max_per_cik=1`` keeps the request budget at 3 submissions
# JSONs + 3 filing HTMLs = 6 EDGAR requests per refresh.
REFRESH_FILING_TYPES = ["10-K", "20-F"]
REFRESH_MAX_PER_CIK = 1

# Bound the on-disk fixture so the diff stays reviewable. The
# canonical sample corpus carries 20 chunks across 10 CIKs; this
# fixture carries roughly the same density per CIK without breaking
# the diff size budget.
DEFAULT_MAX_CHUNKS_PER_CIK = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh a small EDGAR fixture corpus at data/refreshed_corpus/.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "refreshed_corpus" / "chunks.jsonl"),
        help="Output JSONL path for the refreshed fixture.",
    )
    parser.add_argument(
        "--refresh-manifest",
        default=str(ROOT / "data" / "refreshed_corpus" / "manifest.json"),
        help="Output path for the refresh manifest.",
    )
    parser.add_argument(
        "--max-chunks-per-cik",
        type=int,
        default=DEFAULT_MAX_CHUNKS_PER_CIK,
        help="Truncate each CIK's chunk set to this many chunks (default 2).",
    )
    parser.add_argument(
        "--raw-cache",
        default=str(ROOT / "data" / "raw"),
        help="Raw EDGAR filing cache path.",
    )
    parser.add_argument(
        "--requests-per-second",
        type=float,
        default=8.0,
        help="SEC request rate cap (keep below SEC's 10 req/s policy).",
    )
    parser.add_argument(
        "--offline-stub",
        action="store_true",
        help="Skip the live fetch and write the offline stub fixture directly.",
    )
    return parser


def _stub_chunks(max_chunks_per_cik: int) -> list[DocumentChunk]:
    """Offline fallback fixture used when EDGAR is not reachable.

    The text spans here are short, generic supplier-risk excerpts in
    the same shape as the canonical sample corpus chunks. They carry
    a ``source: edgar_stub`` metadata tag so a downstream consumer
    can tell stub fixtures apart from live fetches.
    """

    stub_records: list[tuple[ManifestCompany, str, list[str]]] = [
        (
            REFRESH_CIKS[0],  # NVDA
            "0001045810-25-000001",
            [
                "NVIDIA depends on a small number of foundry partners for advanced "
                "node wafer supply and disclosed that disruptions at those partners "
                "could materially delay data center product shipments.",
                "The filing names export control rules covering advanced GPUs sold "
                "into China as a continuing source of demand uncertainty that the "
                "company manages through licensed product configurations.",
            ],
        ),
        (
            REFRESH_CIKS[1],  # TSM
            "0001046179-25-000001",
            [
                "TSMC reports that its advanced node capacity remains concentrated "
                "in Taiwan and that geopolitical events affecting the island could "
                "disrupt production for its largest customers.",
                "The 20-F discloses that customer concentration is high: a limited "
                "number of fabless customers account for a substantial share of "
                "wafer revenue, including leading US semiconductor designers.",
            ],
        ),
        (
            REFRESH_CIKS[2],  # AMAT
            "0000006951-25-000001",
            [
                "Applied Materials describes its semiconductor equipment business "
                "as dependent on a concentrated set of customers building advanced "
                "logic and memory fabs, and notes that order timing is volatile.",
                "The filing identifies export control restrictions on shipments of "
                "advanced semiconductor manufacturing equipment to certain China "
                "customers as a continuing constraint on addressable demand.",
            ],
        ),
    ]

    chunks: list[DocumentChunk] = []
    for company, accession, spans in stub_records:
        for chunk_index, span in enumerate(spans[:max_chunks_per_cik]):
            chunks.append(
                DocumentChunk(
                    cik=company.cik,
                    accession=accession,
                    section="Filing",
                    text=span,
                    metadata={
                        "company": company.name,
                        "ticker": company.ticker or "",
                        "filing_type": "10-K" if (company.ticker or "") != "TSM" else "20-F",
                        "section": "Filing",
                        "chunk_index": chunk_index,
                        "source": "edgar_stub",
                    },
                    chunk_index=chunk_index,
                )
            )
    return chunks


RISK_KEYWORDS = (
    "supplier",
    "suppliers",
    "supply",
    "single source",
    "single-source",
    "concentration",
    "geopolitical",
    "export control",
    "export controls",
    "manufacturing",
    "foundry",
    "capacity",
    "raw materials",
    "components",
    "disruption",
    "disruptions",
    "tariff",
)


def _score_chunk(chunk: DocumentChunk) -> int:
    """Cheap keyword-overlap score so we keep supplier-risk chunks first."""

    text_lower = chunk.text.lower()
    return sum(text_lower.count(keyword) for keyword in RISK_KEYWORDS)


def _truncate_chunks_per_cik(
    chunks: list[DocumentChunk],
    *,
    max_per_cik: int,
) -> list[DocumentChunk]:
    """Keep at most ``max_per_cik`` chunks per CIK from the live fetch.

    The fetch produces hundreds of chunks per 10-K. The first dozens
    carry XBRL metadata (which scores zero on supplier-risk keywords);
    the body sections later in the document score higher. We rank
    each CIK's chunks by keyword overlap with the supplier-risk
    vocabulary, then keep the top ``max_per_cik`` chunks per CIK.
    Original chunk_index values are preserved so a reviewer can map
    each fixture chunk back to its position in the source filing.
    """

    if max_per_cik <= 0:
        return []
    by_cik: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        by_cik[chunk.cik].append(chunk)
    kept: list[DocumentChunk] = []
    for cik in sorted(by_cik):
        ranked = sorted(
            by_cik[cik],
            key=lambda chunk: (-_score_chunk(chunk), chunk.chunk_index),
        )
        kept.extend(ranked[:max_per_cik])
    return kept


def _write_jsonl(chunks: list[DocumentChunk], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(
                json.dumps(
                    {
                        "cik": chunk.cik,
                        "accession": chunk.accession,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                    },
                    sort_keys=True,
                )
            )
            handle.write("\n")
    tmp_path.replace(output_path)


def _write_summary_manifest(
    *,
    manifest_path: Path,
    source: str,
    output_path: Path,
    chunks: list[DocumentChunk],
    generated_at: datetime,
    note: str | None = None,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    per_company: dict[str, dict[str, object]] = {}
    for chunk in chunks:
        bucket = per_company.setdefault(
            chunk.cik,
            {
                "cik": chunk.cik,
                "company": chunk.metadata.get("company", ""),
                "ticker": chunk.metadata.get("ticker", ""),
                "accessions": [],
                "chunk_count": 0,
            },
        )
        accessions = bucket["accessions"]
        assert isinstance(accessions, list)
        if chunk.accession not in accessions:
            accessions.append(chunk.accession)
        bucket["chunk_count"] = int(bucket["chunk_count"]) + 1  # type: ignore[arg-type]

    payload = {
        "generated_at": generated_at.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "source": source,
        "chunk_file": output_path.name,
        "totals": {
            "companies": len(per_company),
            "chunks_written": len(chunks),
        },
        "companies": sorted(per_company.values(), key=lambda item: str(item["cik"])),
    }
    if note:
        payload["note"] = note

    tmp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(manifest_path)


async def _live_refresh(
    *,
    output_path: Path,
    manifest_path: Path,
    raw_cache: Path,
    requests_per_second: float,
) -> RefreshResult:
    manifest = IngestManifest(
        ciks=REFRESH_CIKS,
        filing_types=REFRESH_FILING_TYPES,
        max_per_cik=REFRESH_MAX_PER_CIK,
    )
    client = SECClient(
        raw_cache=str(raw_cache),
        requests_per_second=requests_per_second,
    )
    return await refresh_edgar_corpus(
        manifest=manifest,
        client=client,
        output_path=output_path,
        refresh_manifest_path=None,
        source_manifest_path=None,
        dry_run=False,
    )


def _print_company_summary(company_results: list[CompanyRefreshResult]) -> None:
    for result in company_results:
        planned_labels = ", ".join(
            f"{filing.form} {filing.filing_date} {filing.accession}"
            for filing in result.planned_filings
        ) or "no target filings"
        console.print(f"  {result.company.name}: {planned_labels}")


def main() -> int:
    args = build_parser().parse_args()
    output_path = Path(args.output)
    manifest_path = Path(args.refresh_manifest)
    raw_cache = Path(args.raw_cache)
    generated_at = datetime.now(UTC)

    if args.offline_stub:
        chunks = _stub_chunks(args.max_chunks_per_cik)
        _write_jsonl(chunks, output_path)
        _write_summary_manifest(
            manifest_path=manifest_path,
            source="offline_stub",
            output_path=output_path,
            chunks=chunks,
            generated_at=generated_at,
            note="--offline-stub flag passed; live EDGAR fetch skipped.",
        )
        console.print(
            f"[yellow]Offline-stub fixture written:[/yellow] {len(chunks)} chunk(s) "
            f"-> {output_path.relative_to(ROOT).as_posix()}"
        )
        return 0

    try:
        result = asyncio.run(
            _live_refresh(
                output_path=output_path,
                manifest_path=manifest_path,
                raw_cache=raw_cache,
                requests_per_second=args.requests_per_second,
            )
        )
    except (SECClientError, OSError, RuntimeError) as exc:
        console.print(
            f"[yellow]EDGAR fetch failed ({exc.__class__.__name__}: {exc}). "
            f"Falling back to offline stub fixture.[/yellow]"
        )
        chunks = _stub_chunks(args.max_chunks_per_cik)
        _write_jsonl(chunks, output_path)
        _write_summary_manifest(
            manifest_path=manifest_path,
            source="offline_stub",
            output_path=output_path,
            chunks=chunks,
            generated_at=generated_at,
            note=f"Live fetch failed: {exc.__class__.__name__}: {exc}",
        )
        console.print(
            f"[yellow]Offline-stub fixture written:[/yellow] {len(chunks)} chunk(s) "
            f"-> {output_path.relative_to(ROOT).as_posix()}"
        )
        return 0

    # Live path: re-read the JSONL the pipeline wrote, truncate per
    # CIK, and rewrite. The pipeline already wrote the full chunk
    # set; we trim it in place so the fixture stays bounded.
    full_chunks = load_jsonl_corpus(output_path)
    bounded_chunks = _truncate_chunks_per_cik(
        full_chunks,
        max_per_cik=args.max_chunks_per_cik,
    )
    _write_jsonl(bounded_chunks, output_path)
    _write_summary_manifest(
        manifest_path=manifest_path,
        source="live_edgar",
        output_path=output_path,
        chunks=bounded_chunks,
        generated_at=generated_at,
        note=(
            f"Filings planned: {result.filings_planned}; "
            f"filings written: {result.filings_written}; "
            f"chunks before truncation: {result.chunks_written}; "
            f"chunks after per-CIK cap: {len(bounded_chunks)}."
        ),
    )
    console.print(
        f"[green]Live EDGAR refresh complete:[/green] "
        f"{result.filings_written} filing(s), "
        f"{len(bounded_chunks)} chunk(s) written to "
        f"{output_path.relative_to(ROOT).as_posix()}."
    )
    _print_company_summary(result.companies)
    return 0


if __name__ == "__main__":
    sys.exit(main())
