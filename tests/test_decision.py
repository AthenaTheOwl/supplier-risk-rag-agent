"""Tests for src.agent.decision (DecisionRecord artifact)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from src.agent.decision import (
    DecisionRecord,
    DecisionStatus,
    EvidencePointer,
    build_decision_record,
    read_decision_record,
    write_decision_record,
)


REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO / "ops" / "decision-records"


def _sample_ep() -> EvidencePointer:
    return EvidencePointer(
        chunk_id="nvda-10k-2024-supplier-concentration",
        accession="0001045810-24-000316",
        cik="1045810",
        section="Item 1A",
        span_text="example verbatim span",
    )


def test_build_decision_record_generates_uuid_and_timestamp() -> None:
    rec = build_decision_record(
        query="Should we tier-up NVIDIA?",
        status=DecisionStatus.SUPPORTED,
        rule_id="tier1-evidence-bar",
        confidence=0.8,
        evidence_pointers=[_sample_ep()],
    )
    assert len(rec.id) == 36
    assert rec.produced_at.tzinfo is not None


def test_supported_requires_evidence_pointer() -> None:
    with pytest.raises(ValueError, match="requires"):
        build_decision_record(
            query="Should we tier-up NVIDIA?",
            status="supported",
            rule_id="tier1-evidence-bar",
            confidence=0.8,
            evidence_pointers=[],
        )


def test_refused_must_not_carry_evidence_pointers() -> None:
    with pytest.raises(ValueError, match="must not carry"):
        build_decision_record(
            query="Should we tier-up NVIDIA?",
            status="refused",
            rule_id="out-of-scope",
            confidence=0.0,
            evidence_pointers=[_sample_ep()],
        )


def test_insufficient_evidence_allows_empty_pointers() -> None:
    rec = build_decision_record(
        query="Is supplier ASE tier-1?",
        status=DecisionStatus.INSUFFICIENT_EVIDENCE,
        rule_id="tier1-evidence-bar",
        confidence=0.31,
        evidence_pointers=[],
    )
    assert rec.evidence_pointers == []


def test_write_and_read_round_trip(tmp_path: Path) -> None:
    rec = build_decision_record(
        query="Should we tier-up NVIDIA?",
        status=DecisionStatus.SUPPORTED,
        rule_id="tier1-evidence-bar",
        confidence=0.82,
        evidence_pointers=[_sample_ep()],
        produced_at=dt.datetime(2026, 6, 5, 18, 0, tzinfo=dt.timezone.utc),
    )
    path = write_decision_record(rec, records_dir=tmp_path)
    assert path.name.endswith(".json")
    assert path.parent == tmp_path
    loaded = read_decision_record(path)
    assert loaded == rec


def test_dict_evidence_pointers_are_validated() -> None:
    rec = build_decision_record(
        query="Should we tier-up NVIDIA?",
        status="supported",
        rule_id="tier1-evidence-bar",
        confidence=0.5,
        evidence_pointers=[
            {
                "chunk_id": "x",
                "accession": "y",
                "cik": "123",
                "section": "Item 1A",
                "span_text": "z",
            }
        ],
    )
    assert isinstance(rec.evidence_pointers[0], EvidencePointer)


def test_cik_pattern_enforced() -> None:
    with pytest.raises(ValueError):
        EvidencePointer(
            chunk_id="x",
            accession="y",
            cik="not-a-cik",
            section="Item 1A",
            span_text="z",
        )


def test_confidence_bounded_0_1() -> None:
    with pytest.raises(ValueError):
        build_decision_record(
            query="x",
            status="refused",
            rule_id="r",
            confidence=1.5,
        )


def test_bundled_sample_supported_parses_clean() -> None:
    rec = read_decision_record(SAMPLES / "sample-supported.json")
    assert rec.status == DecisionStatus.SUPPORTED
    assert rec.evidence_pointers


def test_bundled_sample_insufficient_parses_clean() -> None:
    rec = read_decision_record(SAMPLES / "sample-insufficient.json")
    assert rec.status == DecisionStatus.INSUFFICIENT_EVIDENCE
    assert rec.evidence_pointers == []
