"""A provider may order verified evidence but cannot publish new claims."""

from __future__ import annotations

import json

import pytest

from src.agent.answerer import SupplierRiskAgent
from src.config import Keys
from src.retrieval.citations import verify_citations
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker

QUERY = "Which companies disclosed customer-concentration risk?"
FORGED = "Fabricated audit claim ZXQ-928471 is proven."
OFFLINE_KEYS = Keys(anthropic_key="fake-offline-test")
ORDER = json.dumps({"citation_labels": ["C4", "C3", "C2", "C1"]})


class FakeLLM:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = 0

    def complete(self, *args: object, **kwargs: object) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.text


@pytest.fixture
def agent() -> SupplierRiskAgent:
    return SupplierRiskAgent(HybridRanker(load_sample_corpus()))


@pytest.mark.parametrize("response", [
    FORGED + " [C1]",
    FORGED + " [C999]",
    "",
    "   ",
    "{not JSON}",
    'Here is your answer: {"citation_labels":["C1","C2","C3","C4"]}',
    json.dumps({"citation_labels": ["C1", "C2", "C3", "C4"], "answer": FORGED}),
    json.dumps({"citation_labels": ["C1", "C2", "C3", "C999"]}),
    json.dumps({"citation_labels": ["C1", "C1", "C3", "C4"]}),
    json.dumps({"citation_labels": ["C1", "C2", "C3"]}),
    json.dumps({"citation_labels": []}),
    json.dumps({"citation_labels": "C1,C2,C3,C4"}),
    json.dumps({"citation_labels": [1, "C2", "C3", "C4"]}),
    "null",
    '{"citation_labels":[],"citation_labels":["C1","C2","C3","C4"]}',
    # A fence is stripped only when it wraps the whole reply around one JSON object.
    "Here is the order:\n```json\n" + ORDER + "\n```",
    "```json\n" + ORDER + "\n```\n" + FORGED,
    "```json\n" + FORGED + "\n" + ORDER + "\n```",
    "```json\n{not JSON}\n```",
    "```json\n" + ORDER + ORDER + "\n```",
    "```json\n" + ORDER + "\n```\n```json\n" + ORDER + "\n```",
    "```json\n" + ORDER,
    "```json " + ORDER + " ```",
    "```python\n" + ORDER + "\n```",
    "```json\n" + json.dumps({"citation_labels": ["C1", "C2", "C3"]}) + "\n```",
])
def test_invalid_live_output_keeps_only_verified_local_answer(
    agent: SupplierRiskAgent, response: str,
) -> None:
    deterministic = agent.answer(QUERY)
    client = FakeLLM(response)
    answer = agent.answer(QUERY, use_live_llm=True, keys=OFFLINE_KEYS, llm_client=client)
    assert answer.text == deterministic.text
    assert FORGED not in answer.text
    assert answer.citations == deterministic.citations
    assert not answer.refused
    assert answer.generation_mode == "live_rejected"
    assert answer.generation_reason
    assert client.calls == 1


def test_live_order_is_complete_permutation_of_original_verified_evidence(
    agent: SupplierRiskAgent,
) -> None:
    deterministic = agent.answer(QUERY)
    labels = [c.label for c in reversed(deterministic.citations)]
    client = FakeLLM(json.dumps({"citation_labels": labels}))
    answer = agent.answer(QUERY, use_live_llm=True, keys=OFFLINE_KEYS, llm_client=client)
    assert [c.label for c in answer.citations] == labels
    assert {c.label: c.as_dict() for c in answer.citations} == {
        c.label: c.as_dict() for c in deterministic.citations
    }
    assert [answer.text.index(c.span_text) for c in answer.citations] == sorted(
        answer.text.index(c.span_text) for c in answer.citations
    )
    assert "citation_labels" not in answer.text
    assert verify_citations(answer.citations, load_sample_corpus()) == answer.citations
    assert answer.generation_mode == "live_ordered"
    assert not answer.generation_reason
    assert client.calls == 1


@pytest.mark.parametrize("response", [
    "```json\n" + ORDER + "\n```",
    "```\n" + ORDER + "\n```",
    "\n  ```json\n" + ORDER + "\n```\n\n",
    "```json\r\n" + json.dumps({"citation_labels": ["C4", "C3", "C2", "C1"]}, indent=2) + "\r\n```",
    "\n\t " + ORDER + " \n",
])
def test_fenced_or_padded_single_object_is_accepted(
    agent: SupplierRiskAgent, response: str,
) -> None:
    deterministic = agent.answer(QUERY)
    client = FakeLLM(response)
    answer = agent.answer(QUERY, use_live_llm=True, keys=OFFLINE_KEYS, llm_client=client)
    assert answer.generation_mode == "live_ordered"
    assert not answer.generation_reason
    assert [c.label for c in answer.citations] == ["C4", "C3", "C2", "C1"]
    assert {c.label: c.as_dict() for c in answer.citations} == {
        c.label: c.as_dict() for c in deterministic.citations
    }
    assert "```" not in answer.text
    assert client.calls == 1


def test_provider_failure_has_distinct_safe_fallback_metadata(agent: SupplierRiskAgent) -> None:
    deterministic = agent.answer(QUERY)
    client = FakeLLM(error=RuntimeError("private provider detail must not reach the answer"))
    answer = agent.answer(QUERY, use_live_llm=True, keys=OFFLINE_KEYS, llm_client=client)
    assert answer.text == deterministic.text
    assert answer.generation_mode == "live_failed"
    assert answer.generation_reason
    assert "RuntimeError" in answer.generation_reason
    assert "private provider detail" not in answer.generation_reason
    assert client.calls == 1


def test_refusal_never_calls_provider(agent: SupplierRiskAgent) -> None:
    client = FakeLLM(FORGED)
    answer = agent.answer(
        "Who won the Super Bowl?", use_live_llm=True, keys=OFFLINE_KEYS, llm_client=client,
    )
    assert answer.refused
    assert not answer.citations
    assert answer.generation_mode == "deterministic"
    assert client.calls == 0
