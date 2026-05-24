from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from src.agent.answerer import SupplierRiskAgent
from src.evals.abstention import evaluate_abstention
from src.evals.citation_faithfulness import evaluate_citations
from src.evals.regression import evaluate_regression
from src.evals.retrieval_quality import evaluate_retrieval
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker

console = Console()

GATES = {
    "retrieval_quality": ("recall_at_5", 0.70),
    "citation_faithfulness": ("faithfulness", 0.95),
    "supplier_risk_questions": ("answer_quality", 0.80),
    "refusal_cases": ("refusal_precision", 0.85),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_cases(name: str) -> list[dict[str, Any]]:
    path = _repo_root() / "eval_suites" / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return list(payload.get("cases", []))


def _evaluate_suite(name: str, ranker: HybridRanker, agent: SupplierRiskAgent) -> dict[str, Any]:
    cases = _load_cases(name)
    if name == "retrieval_quality":
        metrics = asdict(evaluate_retrieval(cases, ranker))
    elif name == "citation_faithfulness":
        metrics = asdict(evaluate_citations(cases, agent))
    elif name == "supplier_risk_questions":
        metrics = asdict(evaluate_regression(cases, agent))
    elif name == "refusal_cases":
        metrics = asdict(evaluate_abstention(cases, agent))
    else:
        raise ValueError(f"Unknown suite: {name}")
    gate_metric, threshold = GATES[name]
    metrics["gate_metric"] = gate_metric
    metrics["threshold"] = threshold
    metrics["passed"] = float(metrics[gate_metric]) >= threshold
    return metrics


def _write_html_report(path: Path, results: dict[str, dict[str, Any]]) -> None:
    rows = []
    for name, metrics in results.items():
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{metrics['gate_metric']}</td>"
            f"<td>{float(metrics[metrics['gate_metric']]):.3f}</td>"
            f"<td>{float(metrics['threshold']):.3f}</td>"
            f"<td>{'pass' if metrics['passed'] else 'fail'}</td>"
            "</tr>"
        )
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Supplier Risk RAG Baseline Eval Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2328; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }
    th { background: #f6f8fa; }
  </style>
</head>
<body>
  <h1>Supplier Risk RAG Baseline Eval Report</h1>
  <p>Deterministic CI run over the checked-in sample corpus. No API keys required.</p>
  <table>
    <thead>
      <tr><th>Suite</th><th>Gate metric</th><th>Score</th><th>Threshold</th><th>Status</th></tr>
    </thead>
    <tbody>
"""
    html += "\n".join(rows)
    html += """
    </tbody>
  </table>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic supplier-risk RAG evals.")
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", *GATES.keys()],
        help="Eval suite to run.",
    )
    parser.add_argument("--report", default=None, help="Optional HTML report path.")
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Optional JSON metrics output path (for experiment tracking).",
    )
    parser.add_argument(
        "--reranker",
        default=None,
        help=(
            "Optional cross-encoder model name to use as reranker. "
            "Examples: cross-encoder/ms-marco-MiniLM-L-6-v2, BAAI/bge-reranker-base. "
            "Off by default; baseline CI runs without reranking."
        ),
    )
    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=50,
        help="When --reranker is set, retrieve this many candidates before reranking.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    reranker = None
    if args.reranker:
        from src.retrieval.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker(model_name=args.reranker)
    ranker = HybridRanker(
        load_sample_corpus(_repo_root()),
        reranker=reranker,
        candidate_pool=args.candidate_pool,
    )
    agent = SupplierRiskAgent(ranker)
    suite_names = list(GATES.keys()) if args.suite == "all" else [args.suite]
    results = {name: _evaluate_suite(name, ranker, agent) for name in suite_names}

    table = Table(title="Supplier-risk evals")
    table.add_column("Suite")
    table.add_column("Metric")
    table.add_column("Score", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Status")
    for name, metrics in results.items():
        metric_name = metrics["gate_metric"]
        table.add_row(
            name,
            metric_name,
            f"{float(metrics[metric_name]):.3f}",
            f"{float(metrics['threshold']):.3f}",
            "pass" if metrics["passed"] else "fail",
        )
    console.print(table)

    if args.report:
        _write_html_report(Path(args.report), results)

    if args.json_path:
        json_path = Path(args.json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "config": {
                "suite": args.suite,
                "reranker": args.reranker,
                "candidate_pool": args.candidate_pool if args.reranker else None,
                "with_reranker": bool(args.reranker),
            },
            "results": results,
        }
        json_path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")

    failed = [name for name, metrics in results.items() if not metrics["passed"]]
    if failed:
        raise SystemExit(f"Eval gate failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
