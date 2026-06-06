"""DecisionRecord — typed artifact for decision-augmented RAG queries.

Closes the user-flagged decision-augmented-RAG gap (rank #6 in the
portfolio backlog synthesis). The agent's "what should I do about
supplier X?" path now produces a recoverable, validatable artifact —
not just a free-text answer.

The model mirrors the JSON Schema at ``schemas/decision_record.schema.json``
which the per-repo validator enforces; this Python side adds Pydantic
validation + a builder API that the agent loop consumes.

Status enum:
    supported              evidence backed the decision
    insufficient_evidence  retrieval succeeded but evidence missed the bar
    refused                agent declined to decide
"""

from __future__ import annotations

import datetime as _dt
import enum
import uuid
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS_DIR = REPO_ROOT / "ops" / "decision-records"


class DecisionStatus(str, enum.Enum):
    SUPPORTED = "supported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSED = "refused"


class EvidencePointer(BaseModel):
    """One verbatim citation backing a decision verdict."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(min_length=1)
    accession: str = Field(min_length=1)
    cik: str = Field(pattern=r"^[0-9]{1,10}$")
    section: str
    span_text: str = Field(min_length=1)
    span_offsets: tuple[int, int] | None = Field(default=None)


class DecisionRecord(BaseModel):
    """Per-query decision artifact (R-DECAUG-001 + DEC-DECAUG-001)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    query: str = Field(min_length=1, max_length=1000)
    status: DecisionStatus
    rule_id: str = Field(min_length=1)
    evidence_pointers: list[EvidencePointer] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    produced_at: _dt.datetime
    model: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _check_evidence_consistency(self) -> DecisionRecord:
        # The contract: supported decisions MUST cite evidence; refused
        # and insufficient_evidence decisions MUST NOT (citing here would
        # imply a verdict the status doesn't claim).
        if self.status == DecisionStatus.SUPPORTED and not self.evidence_pointers:
            raise ValueError(
                "DecisionRecord(status=supported) requires >= 1 evidence_pointer"
            )
        if self.status != DecisionStatus.SUPPORTED and self.evidence_pointers:
            raise ValueError(
                f"DecisionRecord(status={self.status.value}) must not carry "
                "evidence_pointers; clear them or change status to supported"
            )
        return self


def build_decision_record(
    *,
    query: str,
    status: DecisionStatus | str,
    rule_id: str,
    confidence: float,
    evidence_pointers: Iterable[EvidencePointer | dict] = (),
    produced_at: _dt.datetime | None = None,
    model: str | None = None,
    notes: str | None = None,
) -> DecisionRecord:
    """Construct a DecisionRecord with sane defaults.

    Generates a fresh UUIDv4 ``id``. ``produced_at`` defaults to the
    UTC timestamp of the call.
    """
    if isinstance(status, str):
        status = DecisionStatus(status)
    if produced_at is None:
        produced_at = _dt.datetime.now(_dt.timezone.utc)
    refs = [
        ep if isinstance(ep, EvidencePointer) else EvidencePointer.model_validate(ep)
        for ep in evidence_pointers
    ]
    return DecisionRecord(
        id=str(uuid.uuid4()),
        query=query,
        status=status,
        rule_id=rule_id,
        evidence_pointers=refs,
        confidence=confidence,
        produced_at=produced_at,
        model=model,
        notes=notes,
    )


def write_decision_record(
    record: DecisionRecord,
    *,
    records_dir: Path = DEFAULT_RECORDS_DIR,
) -> Path:
    """Persist a record under ops/decision-records/<id>.json."""
    records_dir.mkdir(parents=True, exist_ok=True)
    path = records_dir / f"{record.id}.json"
    path.write_text(
        record.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    return path


def read_decision_record(path: Path) -> DecisionRecord:
    return DecisionRecord.model_validate_json(path.read_text(encoding="utf-8"))


__all__ = [
    "DEFAULT_RECORDS_DIR",
    "DecisionRecord",
    "DecisionStatus",
    "EvidencePointer",
    "build_decision_record",
    "read_decision_record",
    "write_decision_record",
]
