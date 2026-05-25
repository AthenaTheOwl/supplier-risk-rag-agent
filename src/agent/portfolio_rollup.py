"""Investor portfolio rollup over verified filing excerpts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.retrieval.citations import Citation, citation_from_chunk, verify_citations
from src.retrieval.index import DocumentChunk
from src.retrieval.ranker import HybridRanker, SearchResult, tokenize

LINE_SPLIT_RE = re.compile(r"[\s,]+")
KEY_VALUE_RE = re.compile(r"^([A-Za-z_]+)[:=](.+)$")
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
CIK_RE = re.compile(r"^\d{1,10}$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class HoldingParseError(ValueError):
    """Raised when pasted holdings cannot be parsed."""

    def __init__(self, messages: Sequence[str]) -> None:
        self.messages = list(messages)
        super().__init__("; ".join(self.messages))


@dataclass(frozen=True)
class ParsedHolding:
    identifier: str
    identifier_type: str
    weight: float
    raw_weight: float
    line_number: int


@dataclass(frozen=True)
class ResolvedHolding:
    requested_identifiers: tuple[str, ...]
    identifier_type: str
    weight: float
    cik: str | None
    ticker: str | None
    company: str | None
    missing_reason: str | None = None

    @property
    def label(self) -> str:
        if self.ticker and self.company:
            return f"{self.ticker} ({self.company})"
        if self.company:
            return self.company
        return ", ".join(self.requested_identifiers)

    @property
    def is_supported(self) -> bool:
        return self.cik is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "requested_identifiers": list(self.requested_identifiers),
            "identifier_type": self.identifier_type,
            "weight": self.weight,
            "cik": self.cik,
            "ticker": self.ticker,
            "company": self.company,
            "missing_reason": self.missing_reason,
        }


@dataclass(frozen=True)
class RiskCategory:
    key: str
    title: str
    query: str
    evidence_tokens: frozenset[str]
    min_token_hits: int = 1
    min_score: float = 0.15


@dataclass(frozen=True)
class RiskEvidence:
    holding: ResolvedHolding
    citation: Citation
    score: float

    def as_dict(self) -> dict[str, object]:
        return {
            "holding": self.holding.as_dict(),
            "score": self.score,
            "citation": self.citation.as_dict(),
        }


@dataclass(frozen=True)
class RiskCard:
    category: RiskCategory
    status: str
    evidence_weight: float
    evidence: tuple[RiskEvidence, ...]
    missing_holdings: tuple[ResolvedHolding, ...]
    refused_reason: str | None = None

    @property
    def citations(self) -> list[Citation]:
        return [item.citation for item in self.evidence]

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.category.key,
            "title": self.category.title,
            "status": self.status,
            "evidence_weight": self.evidence_weight,
            "evidence": [item.as_dict() for item in self.evidence],
            "missing_holdings": [holding.as_dict() for holding in self.missing_holdings],
            "refused_reason": self.refused_reason,
        }


@dataclass(frozen=True)
class PortfolioRollup:
    holdings: tuple[ResolvedHolding, ...]
    cards: tuple[RiskCard, ...]
    refused: bool
    refused_reason: str | None = None

    @property
    def citations(self) -> list[Citation]:
        return [citation for card in self.cards for citation in card.citations]

    def as_dict(self) -> dict[str, object]:
        return {
            "refused": self.refused,
            "refused_reason": self.refused_reason,
            "holdings": [holding.as_dict() for holding in self.holdings],
            "cards": [card.as_dict() for card in self.cards],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def to_markdown(self) -> str:
        lines = ["# Investor portfolio supplier-risk rollup", ""]
        if self.refused and self.refused_reason:
            lines.extend([f"Refusal: {self.refused_reason}", ""])

        lines.append("## Holdings")
        for holding in self.holdings:
            weight = _format_weight(holding.weight)
            if holding.is_supported:
                lines.append(f"- {holding.label}: {weight}")
            else:
                lines.append(f"- {holding.label}: {weight}; insufficient evidence")

        lines.append("")
        lines.append("## Risk cards")
        for card in self.cards:
            lines.extend(["", f"### {card.category.title}", f"Status: {card.status}"])
            lines.append(
                "Portfolio weight with verified evidence: "
                f"{_format_weight(card.evidence_weight)}"
            )
            if card.refused_reason:
                lines.append(f"Reason: {card.refused_reason}")
            for item in card.evidence:
                citation = item.citation
                lines.append(
                    f"- {item.holding.label} ({_format_weight(item.holding.weight)}): "
                    f"{citation.span_text} [{citation.label}]"
                )
            if card.missing_holdings:
                missing = ", ".join(holding.label for holding in card.missing_holdings)
                lines.append(f"- Insufficient evidence for: {missing}")

        if self.citations:
            lines.extend(["", "## Verified citations"])
            for citation in self.citations:
                company = citation.metadata.get("company", "Unknown company")
                filing_type = citation.metadata.get("filing_type", "filing")
                year = citation.metadata.get("year", "unknown year")
                lines.append(
                    f"- [{citation.label}] {company}, {filing_type} {year}, "
                    f"{citation.section}, {citation.accession}, "
                    f"offsets {citation.span_offsets[0]}-{citation.span_offsets[1]}"
                )
        return "\n".join(lines).strip() + "\n"


RISK_CATEGORIES: tuple[RiskCategory, ...] = (
    RiskCategory(
        key="supplier",
        title="Supplier and source exposure",
        query=(
            "supplier concentration single-source limited-source supply chain disruptions "
            "logistics contract manufacturers"
        ),
        evidence_tokens=frozenset(
            {
                "supplier",
                "suppliers",
                "source",
                "sources",
                "supply",
                "chain",
                "logistics",
                "contract",
                "manufacturers",
            }
        ),
        min_token_hits=2,
        min_score=0.15,
    ),
    RiskCategory(
        key="concentration",
        title="Customer concentration exposure",
        query=(
            "customer concentration large customers distributors revenue delayed capital "
            "spending customer inventories"
        ),
        evidence_tokens=frozenset(
            {"customer", "customers", "distributors", "revenue", "capital", "inventories"}
        ),
        min_token_hits=2,
        min_score=0.15,
    ),
    RiskCategory(
        key="export_control",
        title="Export-control and trade exposure",
        query=(
            "export controls China restrictions licensing trade restrictions shipments "
            "data center products"
        ),
        evidence_tokens=frozenset(
            {"export", "controls", "china", "restrictions", "licensing", "trade", "shipments"}
        ),
        min_token_hits=2,
        min_score=0.15,
    ),
    RiskCategory(
        key="taiwan",
        title="Taiwan geographic exposure",
        query="Taiwan geopolitical water shortages power interruptions earthquakes fabs foundries",
        evidence_tokens=frozenset({"taiwan"}),
        min_token_hits=1,
        min_score=0.15,
    ),
    RiskCategory(
        key="ai_capacity",
        title="AI capacity and advanced packaging exposure",
        query=(
            "advanced packaging capacity constraints AI data center foundry capacity "
            "wafer fabrication demand exceeds available capacity"
        ),
        evidence_tokens=frozenset(
            {
                "advanced",
                "packaging",
                "capacity",
                "foundry",
                "foundries",
                "wafer",
                "fabrication",
                "data",
                "center",
            }
        ),
        min_token_hits=2,
        min_score=0.15,
    ),
)


def parse_holdings(text: str) -> list[ParsedHolding]:
    """Parse newline-delimited holdings as ticker-or-CIK plus optional weight."""

    messages: list[str] = []
    pending: list[tuple[str, str, float | None, int]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            identifier, weight = _parse_line(line)
            identifier_type, normalized_identifier = _parse_identifier(identifier)
            pending.append((normalized_identifier, identifier_type, weight, line_number))
        except HoldingParseError as exc:
            messages.extend(f"line {line_number}: {message}" for message in exc.messages)

    if not pending and not messages:
        messages.append("paste at least one holding as a ticker or CIK")

    explicit_count = sum(1 for _, _, weight, _ in pending if weight is not None)
    if 0 < explicit_count < len(pending):
        messages.append("provide weights for every holding or omit weights from every holding")

    if messages:
        raise HoldingParseError(messages)

    raw_weights = [weight if weight is not None else 1.0 for _, _, weight, _ in pending]
    total = sum(raw_weights)
    if total <= 0:
        raise HoldingParseError(["portfolio weights must sum to a positive number"])

    parsed: list[ParsedHolding] = []
    for (identifier, identifier_type, _weight, line_number), raw_weight in zip(
        pending, raw_weights, strict=True
    ):
        parsed.append(
            ParsedHolding(
                identifier=identifier,
                identifier_type=identifier_type,
                weight=raw_weight / total,
                raw_weight=raw_weight,
                line_number=line_number,
            )
        )
    return parsed


def build_portfolio_rollup(
    holdings: Sequence[ParsedHolding],
    ranker: HybridRanker,
    *,
    categories: Sequence[RiskCategory] = RISK_CATEGORIES,
    top_k: int = 3,
) -> PortfolioRollup:
    resolved = tuple(_resolve_holdings(holdings, ranker.chunks))
    supported = [holding for holding in resolved if holding.is_supported]
    cards: list[RiskCard] = []

    for category in categories:
        evidence: list[RiskEvidence] = []
        missing: list[ResolvedHolding] = [
            holding for holding in resolved if not holding.is_supported
        ]

        for holding in supported:
            assert holding.cik is not None
            results = ranker.search(category.query, top_k=top_k, filters={"cik": holding.cik})
            selected = _select_evidence(category, results)
            if selected is None:
                missing.append(holding)
                continue
            result, span = selected
            label = f"{_citation_prefix(category)}{len(evidence) + 1}"
            citation = citation_from_chunk(result.chunk, span, label=label)
            verify_citations([citation], results)
            evidence.append(RiskEvidence(holding=holding, citation=citation, score=result.score))

        if evidence:
            cards.append(
                RiskCard(
                    category=category,
                    status="supported",
                    evidence_weight=sum(item.holding.weight for item in evidence),
                    evidence=tuple(evidence),
                    missing_holdings=tuple(missing),
                )
            )
        else:
            cards.append(
                RiskCard(
                    category=category,
                    status="insufficient_evidence",
                    evidence_weight=0.0,
                    evidence=(),
                    missing_holdings=tuple(missing),
                    refused_reason=(
                        "No retrieved filing excerpt met the category evidence threshold "
                        "for the supplied holdings."
                    ),
                )
            )

    refused_reason = None
    if not supported:
        refused_reason = "None of the supplied holdings matched a ticker or CIK in the corpus."
    elif not any(card.evidence for card in cards):
        refused_reason = "No portfolio risk card had verified filing evidence."

    return PortfolioRollup(
        holdings=resolved,
        cards=tuple(cards),
        refused=refused_reason is not None,
        refused_reason=refused_reason,
    )


def rollup_from_text(text: str, ranker: HybridRanker) -> PortfolioRollup:
    return build_portfolio_rollup(parse_holdings(text), ranker)


def _parse_line(line: str) -> tuple[str, float | None]:
    identifier: str | None = None
    weight_text: str | None = None
    messages: list[str] = []

    for token in [part for part in LINE_SPLIT_RE.split(line) if part]:
        key_value = KEY_VALUE_RE.match(token)
        if key_value:
            key = key_value.group(1).lower()
            value = key_value.group(2).strip()
            if key in {"ticker", "symbol", "cik"}:
                if identifier is not None:
                    messages.append("only one identifier is allowed per line")
                identifier = value
            elif key in {"weight", "wt", "w"}:
                if weight_text is not None:
                    messages.append("only one weight is allowed per line")
                weight_text = value
            else:
                messages.append(f"unknown field {key!r}")
            continue

        if identifier is None:
            identifier = token
        elif weight_text is None:
            weight_text = token
        else:
            messages.append(f"unexpected token {token!r}")

    if identifier is None:
        messages.append("missing ticker or CIK")

    weight = None
    if weight_text is not None:
        try:
            weight = _parse_weight(weight_text)
        except HoldingParseError as exc:
            messages.extend(exc.messages)

    if messages:
        raise HoldingParseError(messages)
    assert identifier is not None
    return identifier, weight


def _parse_identifier(value: str) -> tuple[str, str]:
    cleaned = value.strip().upper()
    cik_candidate = cleaned.removeprefix("CIK").removeprefix(":")
    if CIK_RE.match(cik_candidate):
        return "cik", cik_candidate.zfill(10)
    if TICKER_RE.match(cleaned):
        return "ticker", cleaned
    raise HoldingParseError([f"{value!r} is not a valid ticker or CIK"])


def _parse_weight(value: str) -> float:
    cleaned = value.strip()
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        parsed = float(cleaned)
    except ValueError as exc:
        raise HoldingParseError([f"{value!r} is not a valid weight"]) from exc
    if parsed <= 0:
        raise HoldingParseError(["weights must be positive"])
    return parsed


def _resolve_holdings(
    holdings: Sequence[ParsedHolding],
    chunks: Iterable[DocumentChunk],
) -> list[ResolvedHolding]:
    by_cik, by_ticker = _corpus_lookup(chunks)
    buckets: dict[str, ResolvedHolding] = {}

    for holding in holdings:
        cik: str | None
        if holding.identifier_type == "cik":
            cik = holding.identifier if holding.identifier in by_cik else None
        else:
            cik = by_ticker.get(holding.identifier)

        if cik is None:
            key = f"missing:{holding.identifier_type}:{holding.identifier}"
            existing = buckets.get(key)
            if existing is None:
                buckets[key] = ResolvedHolding(
                    requested_identifiers=(holding.identifier,),
                    identifier_type=holding.identifier_type,
                    weight=holding.weight,
                    cik=None,
                    ticker=holding.identifier if holding.identifier_type == "ticker" else None,
                    company=None,
                    missing_reason="not found in the loaded filing corpus",
                )
            else:
                buckets[key] = _merge_holding(existing, holding.identifier, holding.weight)
            continue

        info = by_cik[cik]
        existing = buckets.get(cik)
        if existing is None:
            buckets[cik] = ResolvedHolding(
                requested_identifiers=(holding.identifier,),
                identifier_type=holding.identifier_type,
                weight=holding.weight,
                cik=cik,
                ticker=info.get("ticker"),
                company=info.get("company"),
            )
        else:
            buckets[cik] = _merge_holding(existing, holding.identifier, holding.weight)

    return list(buckets.values())


def _merge_holding(existing: ResolvedHolding, identifier: str, weight: float) -> ResolvedHolding:
    identifiers = tuple(dict.fromkeys([*existing.requested_identifiers, identifier]))
    return ResolvedHolding(
        requested_identifiers=identifiers,
        identifier_type=existing.identifier_type,
        weight=existing.weight + weight,
        cik=existing.cik,
        ticker=existing.ticker,
        company=existing.company,
        missing_reason=existing.missing_reason,
    )


def _corpus_lookup(
    chunks: Iterable[DocumentChunk],
) -> tuple[dict[str, dict[str, str | None]], dict[str, str]]:
    by_cik: dict[str, dict[str, str | None]] = {}
    by_ticker: dict[str, str] = {}
    for chunk in chunks:
        ticker = str(chunk.metadata.get("ticker", "")).upper() or None
        company = str(chunk.metadata.get("company", "")) or None
        by_cik.setdefault(chunk.cik, {"ticker": ticker, "company": company})
        if ticker:
            by_ticker[ticker] = chunk.cik
    return by_cik, by_ticker


def _select_evidence(
    category: RiskCategory,
    results: Sequence[SearchResult],
) -> tuple[SearchResult, str] | None:
    candidates: list[tuple[int, float, int, SearchResult, str]] = []
    for result in results:
        if result.score < category.min_score:
            continue
        for sentence in _sentences(result.chunk.text):
            token_hits = len(set(tokenize(sentence)) & category.evidence_tokens)
            if token_hits < category.min_token_hits:
                continue
            candidates.append((token_hits, result.score, -len(sentence), result, sentence))
    if not candidates:
        return None
    _, _, _, result, sentence = max(candidates, key=lambda item: (item[0], item[1], item[2]))
    return result, sentence


def _sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]
    return sentences or [text.strip()]


def _citation_prefix(category: RiskCategory) -> str:
    prefixes = {"export_control": "EXP", "ai_capacity": "AIC"}
    return prefixes.get(category.key, category.key[:3].upper())


def _format_weight(value: float) -> str:
    return f"{value * 100:.1f}%"
