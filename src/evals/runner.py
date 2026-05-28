from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from src.agent.answerer import SupplierRiskAgent
from src.config import get_model_config
from src.evals.abstention import evaluate_abstention
from src.evals.citation_faithfulness import evaluate_citations
from src.evals.regression import evaluate_regression
from src.evals.retrieval_quality import evaluate_retrieval
from src.evals.run_evidence import (
    build_run_evidence_fields,
    emit_event,
    emit_run,
    load_prompt_files,
    make_event,
    new_run_id,
)
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker

console = Console()

GATES = {
    "retrieval_quality": ("recall_at_5", 0.70),
    "citation_faithfulness": ("faithfulness", 0.95),
    "supplier_risk_questions": ("answer_quality", 0.80),
    "refusal_cases": ("refusal_precision", 0.85),
}

# Event-ledger and run-record output directories. Tests may redirect
# these via environment variables to avoid polluting the repo's ops/
# tree on every CI run.
EVENT_LEDGER_ENV = "SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR"
RUN_RECORDS_ENV = "SUPPLIER_RISK_RAG_RUN_RECORDS_DIR"

# Actor descriptor for events emitted by the runner. The runner is a
# system actor; downstream consumers dispatch on event.type.
ACTOR_KIND = "system"
ACTOR_ID = "supplier-risk-rag-agent-evals"

# Per-suite gate-check labels. These names land in
# ``gate_results_summary.gates_passed`` / ``gates_failed``.
GATE_LABELS = {
    "retrieval_quality": "recall_at_5_threshold",
    "citation_faithfulness": "citation_faithfulness_threshold",
    "supplier_risk_questions": "answer_quality_threshold",
    "refusal_cases": "refusal_precision_threshold",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _event_ledger_dir() -> Path:
    override = os.environ.get(EVENT_LEDGER_ENV)
    if override:
        return Path(override)
    return _repo_root() / "ops" / "event-ledger"


def _run_records_dir() -> Path:
    override = os.environ.get(RUN_RECORDS_ENV)
    if override:
        return Path(override)
    return _repo_root() / "ops" / "run-records"


def _load_cases(name: str) -> list[dict[str, Any]]:
    path = _repo_root() / "eval_suites" / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return list(payload.get("cases", []))


def _suite_determinism(name: str) -> dict[str, Any] | None:
    """Return the determinism block from a suite YAML, if present.

    The suites ship without a ``determinism:`` block today; this
    helper is in place so a later suite that pins a sampler seed or
    temperature gets the field populated automatically.
    """
    path = _repo_root() / "eval_suites" / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    block = payload.get("determinism")
    if isinstance(block, dict):
        return block
    return None


def _retrieval_config_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    """Capture the retrieval surface for the tool-schemas hash.

    The weights live as named constants inside
    ``src/retrieval/ranker.py`` (60/25/15 hybrid plus the 0.03
    zero-overlap fallback per DEC-RET-001). Pinning them here means a
    future change in either place perturbs the hash, which is what we
    want.
    """
    return {
        "ranker": "hybrid_bm25_cosine_overlap",
        "bm25_weight": 0.60,
        "vector_weight": 0.25,
        "overlap_weight": 0.15,
        "zero_overlap_fallback": 0.03,
        "top_k": 5,
        "candidate_pool": args.candidate_pool if args.reranker else None,
        "with_reranker": bool(args.reranker),
    }


def _reranker_config_snapshot(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.reranker:
        return None
    return {
        "model": args.reranker,
        "candidate_pool": args.candidate_pool,
    }


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


def _record_suite_run(
    suite_name: str,
    metrics: dict[str, Any],
    cases: list[dict[str, Any]],
    args: argparse.Namespace,
    *,
    started_at: str,
    finished_at: str,
) -> tuple[str, Path]:
    """Emit Event ledger + Run record for one suite execution.

    Returns ``(run_id, run_record_path)`` so the caller can report
    where the records landed.
    """
    run_id = new_run_id()
    spec_id = f"eval_suites/{suite_name}.yaml"
    ledger_path = _event_ledger_dir() / f"{run_id}.jsonl"
    record_path = _run_records_dir() / f"{run_id}.json"

    prompts_dir = _repo_root() / "src" / "agent" / "prompts"
    extraction, answer_p, refusal_p = load_prompt_files(prompts_dir)

    model_config = get_model_config()
    retrieval_config = _retrieval_config_snapshot(args)
    reranker_config = _reranker_config_snapshot(args)
    embedding_model = "hashing"  # DEC-RET-002 default

    # Build the replay-equivalence fields up-front so we can include
    # the pair of snapshot hashes in the pipeline.start event for the
    # consumer's bridge packet.
    fields = build_run_evidence_fields(
        extraction_prompt=extraction,
        answer_prompt=answer_p,
        refusal_prompt=refusal_p,
        retrieval_config=retrieval_config,
        llm_provider=model_config.provider,
        llm_model=model_config.model,
        embedding_model=embedding_model,
        reranker_config=reranker_config,
        repo_path=_repo_root(),
        gate_events=[],  # populated below after the gate events fire
        determinism=_suite_determinism(suite_name),
    )

    # 1) pipeline.start
    start_event = make_event(
        event_type="pipeline.start",
        actor_kind=ACTOR_KIND,
        actor_id=ACTOR_ID,
        payload={
            "suite": suite_name,
            "case_count": len(cases),
            "prompt_snapshot_hash": fields.fields["prompt_snapshot_hash"],
            "tool_schemas_snapshot_hash": fields.fields["tool_schemas_snapshot_hash"],
            "llm_provider": model_config.provider,
            "llm_model": model_config.model,
            "embedding_model": embedding_model,
            "with_reranker": bool(args.reranker),
        },
        run_id=run_id,
        spec_id=spec_id,
        created_at=started_at,
    )
    emit_event(start_event, ledger_path)

    # 2) tool.call.completed describing the aggregate ranker + agent
    # surface the suite touched. The runner does not break down per
    # case (would balloon the ledger); a single per-suite
    # tool.call.completed records the surface plus the suite-level
    # metrics. This matches the shape consumers expect: per-run
    # rollups for tool calls, per-gate event for thresholds.
    tool_event = make_event(
        event_type="tool.call.completed",
        actor_kind=ACTOR_KIND,
        actor_id=ACTOR_ID,
        payload={
            "tool_id": _tool_id_for_suite(suite_name),
            "status": "ok",
            "case_count": len(cases),
            "gate_metric": metrics["gate_metric"],
            "score": float(metrics[metrics["gate_metric"]]),
            "threshold": float(metrics["threshold"]),
        },
        run_id=run_id,
        spec_id=spec_id,
        parent_event_id=start_event["event_id"],
    )
    emit_event(tool_event, ledger_path)

    # 3) gate.check.passed / gate.check.failed for the suite-level
    # threshold. The gate_name maps one-to-one to the labels in
    # GATE_LABELS.
    gate_name = GATE_LABELS[suite_name]
    gate_event_type = "gate.check.passed" if metrics["passed"] else "gate.check.failed"
    gate_event = make_event(
        event_type=gate_event_type,
        actor_kind=ACTOR_KIND,
        actor_id=ACTOR_ID,
        payload={
            "gate_name": gate_name,
            "score": float(metrics[metrics["gate_metric"]]),
            "threshold": float(metrics["threshold"]),
        },
        run_id=run_id,
        spec_id=spec_id,
        parent_event_id=tool_event["event_id"],
    )
    emit_event(gate_event, ledger_path)

    # Rebuild fields now that we have the gate event so
    # gate_results_summary populates.
    fields = build_run_evidence_fields(
        extraction_prompt=extraction,
        answer_prompt=answer_p,
        refusal_prompt=refusal_p,
        retrieval_config=retrieval_config,
        llm_provider=model_config.provider,
        llm_model=model_config.model,
        embedding_model=embedding_model,
        reranker_config=reranker_config,
        repo_path=_repo_root(),
        gate_events=[gate_event],
        determinism=_suite_determinism(suite_name),
    )

    # 4) Assemble + write Run record.
    status = "done" if metrics["passed"] else "failed"
    run: dict[str, Any] = {
        "id": run_id,
        "spec_id": spec_id,
        "agent_id": f"{model_config.provider}:{model_config.model}",
        "runtime": "supplier-risk-rag-agent-evals",
        "workspace_id": _repo_root().as_posix(),
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "inputs": [{"kind": "eval_suite", "ref": spec_id}],
        "outputs": [],
    }
    run.update(fields.fields)
    emit_run(run, record_path)

    # 5) gate.run.evidence_recorded — the terminal event so the
    # validator can cross-check that a Run record exists.
    evidence_event = make_event(
        event_type="gate.run.evidence_recorded",
        actor_kind=ACTOR_KIND,
        actor_id=ACTOR_ID,
        payload={
            "fields_populated": list(fields.populated),
            "record_path": record_path.relative_to(_repo_root()).as_posix()
            if record_path.is_relative_to(_repo_root())
            else record_path.as_posix(),
        },
        run_id=run_id,
        spec_id=spec_id,
        parent_event_id=gate_event["event_id"],
    )
    emit_event(evidence_event, ledger_path)

    return run_id, record_path


def _tool_id_for_suite(suite_name: str) -> str:
    """Map a suite to the dotted tool surface it exercises."""
    return {
        "retrieval_quality": "ranker.search",
        "citation_faithfulness": "agent.answer+citation.verify",
        "supplier_risk_questions": "agent.answer",
        "refusal_cases": "agent.answer+refusal.decision",
    }[suite_name]


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
    parser.add_argument(
        "--no-emit-evidence",
        action="store_true",
        help="Skip writing run-evidence ledger + Run records. CI normally leaves emission on.",
    )
    return parser


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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

    results: dict[str, dict[str, Any]] = {}
    evidence_paths: list[tuple[str, str, Path]] = []  # (suite, run_id, record_path)

    for name in suite_names:
        started_at = _utc_now()
        metrics = _evaluate_suite(name, ranker, agent)
        finished_at = _utc_now()
        results[name] = metrics
        if not args.no_emit_evidence:
            cases = _load_cases(name)
            run_id, record_path = _record_suite_run(
                name,
                metrics,
                cases,
                args,
                started_at=started_at,
                finished_at=finished_at,
            )
            evidence_paths.append((name, run_id, record_path))

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

    if evidence_paths:
        console.print("[dim]Run-evidence records:[/dim]")
        for suite_name, run_id, record_path in evidence_paths:
            rel = record_path
            try:
                rel = record_path.relative_to(_repo_root())
            except ValueError:
                pass
            console.print(f"  {suite_name}: {run_id} -> {rel.as_posix() if hasattr(rel, 'as_posix') else rel}")

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
