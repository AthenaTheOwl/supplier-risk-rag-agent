"""CLI entry point for sample or generated EDGAR corpus ingestion."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from rich.console import Console

from src.ingest.edgar_refresh import RefreshResult, refresh_edgar_corpus
from src.ingest.manifest import load_manifest
from src.ingest.sec_client import SECClient
from src.retrieval.index import build_chroma_collection, load_jsonl_corpus, load_sample_corpus

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest supplier-risk SEC filings.")
    parser.add_argument("--manifest", default="data/sample_manifest.json")
    parser.add_argument(
        "--full-fetch",
        action="store_true",
        help="Backward-compatible alias for --refresh-edgar.",
    )
    parser.add_argument(
        "--refresh-edgar",
        action="store_true",
        help="Fetch configured EDGAR filings and write a generated JSONL corpus.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch submissions metadata and print the filings that would be downloaded.",
    )
    parser.add_argument(
        "--output",
        default="data/generated/edgar_corpus/chunks.jsonl",
        help="Generated corpus JSONL output path.",
    )
    parser.add_argument(
        "--refresh-manifest",
        default="data/generated/edgar_corpus/manifest.json",
        help="Generated refresh manifest path.",
    )
    parser.add_argument(
        "--raw-cache",
        default="data/raw",
        help="Raw EDGAR filing cache path.",
    )
    parser.add_argument(
        "--requests-per-second",
        type=float,
        default=9.5,
        help="SEC request rate cap. Keep below SEC's 10 requests/second limit.",
    )
    parser.add_argument(
        "--build-chroma",
        default=None,
        help="Optional local Chroma persist path to build from the generated JSONL.",
    )
    return parser


async def _refresh_edgar(args: argparse.Namespace) -> RefreshResult:
    manifest = load_manifest(args.manifest)
    client = SECClient(
        raw_cache=args.raw_cache,
        requests_per_second=args.requests_per_second,
    )
    result = await refresh_edgar_corpus(
        manifest=manifest,
        client=client,
        output_path=args.output,
        refresh_manifest_path=args.refresh_manifest,
        source_manifest_path=args.manifest,
        dry_run=args.dry_run,
    )
    _print_refresh_result(result)
    if args.build_chroma and not args.dry_run:
        chunks = load_jsonl_corpus(args.output)
        build_chroma_collection(chunks, persist_path=args.build_chroma)
        console.print(
            f"Built Chroma collection at {args.build_chroma} from {len(chunks)} chunks."
        )
    return result


def _print_refresh_result(result: RefreshResult) -> None:
    mode = "DRY RUN" if result.dry_run else "REFRESH"
    console.print(
        f"{mode}: {result.filings_planned} filing(s) planned, "
        f"{result.filings_written} filing(s) written, "
        f"{result.chunks_written} chunk(s) generated."
    )
    for company_result in result.companies:
        planned = ", ".join(
            f"{filing.form} {filing.filing_date} {filing.accession}"
            for filing in company_result.planned_filings
        )
        console.print(f"{company_result.company.name}: {planned or 'no target filings'}")
    if not result.dry_run:
        console.print(f"Corpus JSONL: {result.output_path}")
        if result.manifest_path:
            console.print(f"Refresh manifest: {result.manifest_path}")


def main() -> None:
    args = build_parser().parse_args()
    if args.full_fetch or args.refresh_edgar:
        asyncio.run(_refresh_edgar(args))
        return
    chunks = load_sample_corpus(Path.cwd())
    console.print(
        f"Loaded {len(chunks)} checked-in sample chunks. "
        "Use --refresh-edgar for generated EDGAR corpus output."
    )


if __name__ == "__main__":
    main()
