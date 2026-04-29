"""CLI entry point for sample or full EDGAR ingestion."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from rich.console import Console

from src.ingest.manifest import load_manifest
from src.ingest.sec_client import SECClient
from src.retrieval.index import load_sample_corpus

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest supplier-risk SEC filings.")
    parser.add_argument("--manifest", default="data/sample_manifest.json")
    parser.add_argument(
        "--full-fetch",
        action="store_true",
        help="Fetch filing metadata from EDGAR.",
    )
    return parser


async def _full_fetch(manifest_path: str) -> None:
    manifest = load_manifest(manifest_path)
    client = SECClient()
    for company in manifest.ciks:
        submissions = await client.fetch_company_submissions(company.cik)
        forms = submissions.get("filings", {}).get("recent", {}).get("form", [])
        matching = [form for form in forms if form in manifest.filing_types]
        console.print(f"{company.name}: found {len(matching)} recent target filings")


def main() -> None:
    args = build_parser().parse_args()
    if args.full_fetch:
        asyncio.run(_full_fetch(args.manifest))
        return
    chunks = load_sample_corpus(Path.cwd())
    console.print(f"Loaded {len(chunks)} checked-in sample chunks. Use --full-fetch for EDGAR.")


if __name__ == "__main__":
    main()
