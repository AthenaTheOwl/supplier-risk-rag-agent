from pathlib import Path

from src.agent.answerer import SupplierRiskAgent
from src.agent.planner import plan_query
from src.agent.tools import RetrievalTools
from src.config import Keys, get_cli_keys, sec_user_agent
from src.evals.abstention import evaluate_abstention
from src.evals.citation_faithfulness import evaluate_citations
from src.evals.regression import evaluate_regression
from src.evals.retrieval_quality import evaluate_retrieval
from src.retrieval.index import load_jsonl_corpus, load_sample_corpus
from src.retrieval.ranker import HybridRanker


class FakeLLM:
    def complete(self, messages: list[dict[str, str]], *, system: str, max_tokens: int) -> str:
        assert messages
        assert system
        assert max_tokens > 0
        return "Live rewrite [C1]"


def test_planner_adds_domain_subqueries() -> None:
    plan = plan_query("What export controls affected advanced packaging capacity?")
    assert "export controls china restrictions" in plan.subqueries
    assert "advanced packaging capacity constraints" in plan.subqueries


def test_retrieval_tools_filter_and_get_section() -> None:
    ranker = HybridRanker(load_sample_corpus())
    tools = RetrievalTools(ranker)
    filtered = tools.filter_by_cik("export controls China", "0000937966")
    sections = tools.get_section("0000937966", "Risk Factors")
    assert filtered
    assert all(result.chunk.cik == "0000937966" for result in filtered)
    assert sections


def test_live_answer_branch_uses_supplied_client() -> None:
    agent = SupplierRiskAgent(HybridRanker(load_sample_corpus()))
    answer = agent.answer(
        "Which companies disclosed customer-concentration risk?",
        use_live_llm=True,
        keys=Keys(anthropic_key="sk-test"),
        llm_client=FakeLLM(),
    )
    assert answer.text.startswith("Live rewrite")
    assert answer.citations


def test_eval_modules_return_passing_metrics() -> None:
    """Run the four eval suites (retrieval, citations, regression,
    abstention) under the deterministic, no-vendor-keys path and
    assert each suite hits its threshold. Exercises the four-suite
    eval gate without any LLM call.

    Covers: R-EVL-001, R-EVL-002, R-EVL-003.
    """
    ranker = HybridRanker(load_sample_corpus())
    agent = SupplierRiskAgent(ranker)
    retrieval = evaluate_retrieval(
        [
            {
                "query": "Which filing mentions lithography systems and China licensing?",
                "expected_accessions": ["0000937966-24-000033"],
            }
        ],
        ranker,
    )
    citations = evaluate_citations(
        [{"query": "Which companies disclosed customer-concentration risk?"}],
        agent,
    )
    regression = evaluate_regression(
        [
            {
                "query": "Which company cited delayed product launches by major customers?",
                "expected_accessions": ["0001730168-24-000016"],
                "required_terms": ["product launches"],
            }
        ],
        agent,
    )
    abstention = evaluate_abstention(
        [{"query": "Who won the Super Bowl?", "expected_refusal": True}],
        agent,
    )
    assert retrieval.recall_at_5 == 1.0
    assert citations.faithfulness == 1.0
    assert regression.answer_quality == 1.0
    assert abstention.refusal_precision == 1.0


def test_cli_key_helpers_and_jsonl_loader(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("SEC_USER_AGENT", "Example Agent test@example.com")
    keys = get_cli_keys(require_anthropic=True, require_openai=True)
    assert keys.source == "cli-env"
    assert sec_user_agent() == "Example Agent test@example.com"

    sample = tmp_path / "sample.jsonl"
    sample.write_text(
        '{"cik":"1","accession":"a","section":"Risk","text":"supplier risk",'
        '"metadata":{"company":"X"}}\n',
        encoding="utf-8",
    )
    loaded = load_jsonl_corpus(sample)
    assert loaded[0].id == "0000000001:a:risk:0"
