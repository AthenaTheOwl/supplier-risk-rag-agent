from __future__ import annotations

import streamlit as st

from src.agent.answerer import SupplierRiskAgent
from src.agent.llm import LLMClient
from src.config import MissingKeyError, get_keys, get_model_config
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker


@st.cache_resource(show_spinner=False)
def load_agent(use_reranker: bool = False) -> SupplierRiskAgent:
    chunks = load_sample_corpus()
    reranker = None
    if use_reranker:
        # Lazy import keeps sentence-transformers off the default-path cost.
        from src.retrieval.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker()
    return SupplierRiskAgent(HybridRanker(chunks, reranker=reranker))


def sidebar_keys() -> None:
    with st.sidebar:
        st.markdown("### Bring your own key")
        st.caption(
            "Paste your API keys below to enable live Claude answers. Keys stay in "
            "this browser session (`st.session_state`). They are not logged, stored, "
            "or sent anywhere except the vendor SDK call you triggered."
        )
        anthropic_key = st.text_input(
            "Anthropic API key",
            type="password",
            value=st.session_state.get("anthropic_key", ""),
            help="Required for the Live Claude toggle. Without it the app still "
            "returns the deterministic cited answer.",
        )
        openai_key = st.text_input(
            "OpenAI API key",
            type="password",
            value=st.session_state.get("openai_key", ""),
            help="Optional. Only needed for OpenAI-backed experiments or live "
            "ingestion paths.",
        )
        st.session_state["anthropic_key"] = anthropic_key
        st.session_state["openai_key"] = openai_key
        st.divider()
        st.markdown("### Retrieval")
        use_reranker = st.checkbox(
            "Enable cross-encoder reranker (slower, may improve recall)",
            value=st.session_state.get("use_reranker", False),
            help=(
                "Off by default. When on, the hybrid ranker retrieves a wider "
                "candidate pool and a cross-encoder reorders the top-k. The "
                "model loads on first use (one-time ~80 MB download + a few "
                "seconds of CPU init); each query then pays ~150-400 ms of "
                "extra latency. The default hybrid stays the production path "
                "per DEC-RET-001."
            ),
        )
        st.session_state["use_reranker"] = use_reranker
        st.divider()
        st.caption(
            "No keys? The app still works. Deterministic retrieval, verbatim-span "
            "citations, and the four eval suites all run without vendor calls."
        )


def render_answer(query: str, use_live_llm: bool) -> None:
    use_reranker = bool(st.session_state.get("use_reranker", False))
    agent = load_agent(use_reranker=use_reranker)
    keys = None
    key_error = None
    try:
        keys = get_keys(st.session_state)
    except MissingKeyError as exc:
        key_error = str(exc)

    if key_error:
        st.info(f"{key_error} Showing deterministic retrieval preview without a live LLM call.")
        use_live_llm = False

    llm_client = LLMClient(keys, get_model_config()) if keys and use_live_llm else None
    try:
        answer = agent.answer(
            query,
            use_live_llm=use_live_llm and llm_client is not None,
            keys=keys,
            llm_client=llm_client,
        )
    except Exception as exc:
        st.error(f"Live LLM call failed: {exc.__class__.__name__}. Showing local cited answer.")
        answer = agent.answer(query, use_live_llm=False)

    if answer.refused:
        st.warning(answer.text)
    else:
        st.markdown(answer.text)

    st.divider()
    st.caption(f"Confidence: {answer.confidence:.3f}")
    with st.expander("Citations", expanded=True):
        if not answer.citations:
            st.write("No verified citations returned.")
        for citation in answer.citations:
            company = citation.metadata.get("company", "Unknown company")
            filing_type = citation.metadata.get("filing_type", "filing")
            year = citation.metadata.get("year", "unknown year")
            st.markdown(f"**[{citation.label}] {company} - {filing_type} {year}**")
            st.code(citation.span_text, language="text")
            st.caption(
                f"CIK {citation.cik} | {citation.accession} | {citation.section} | "
                f"offsets {citation.span_offsets[0]}-{citation.span_offsets[1]}"
            )


def main() -> None:
    st.set_page_config(page_title="Supplier Risk RAG Agent", layout="wide")
    sidebar_keys()

    st.title("Supplier Risk RAG Agent")
    st.caption(
        "Citation-faithful RAG over SEC EDGAR filings. Every claim points at a "
        "verbatim span in a real 10-K; unverified spans get refused, not "
        "paraphrased."
    )
    st.caption(
        "Try a starter question below, or write your own. Toggle **Live Claude** "
        "to rewrite the answer with your Anthropic key; leave it off for the "
        "deterministic cited answer."
    )

    example_queries = [
        "Which suppliers in this corpus disclosed export-control exposure?",
        "Which companies disclosed customer-concentration risk?",
        "Which firms mentioned advanced packaging capacity constraints?",
        "Where did filings mention supplier concentration or sole-source suppliers?",
    ]

    selected_example = st.selectbox("Starter questions", options=example_queries, index=0)
    query = st.text_input("Your question", value=selected_example)
    cols = st.columns([1, 1, 4])
    with cols[0]:
        live_llm = st.toggle("Live Claude", value=False)
    with cols[1]:
        ask = st.button("Ask", type="primary")

    if ask and query.strip():
        render_answer(query.strip(), live_llm)


if __name__ == "__main__":
    main()
