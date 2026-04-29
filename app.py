from __future__ import annotations

import streamlit as st

from src.agent.answerer import SupplierRiskAgent
from src.agent.llm import LLMClient
from src.config import MissingKeyError, get_keys, get_model_config
from src.retrieval.index import load_sample_corpus
from src.retrieval.ranker import HybridRanker


@st.cache_resource(show_spinner=False)
def load_agent() -> SupplierRiskAgent:
    chunks = load_sample_corpus()
    return SupplierRiskAgent(HybridRanker(chunks))


def sidebar_keys() -> None:
    with st.sidebar:
        st.markdown("### API keys")
        st.caption("Your keys stay in this browser session. They are not logged or stored.")
        anthropic_key = st.text_input(
            "Anthropic API key",
            type="password",
            value=st.session_state.get("anthropic_key", ""),
        )
        openai_key = st.text_input(
            "OpenAI API key",
            type="password",
            value=st.session_state.get("openai_key", ""),
            help="Only needed for live ingestion or OpenAI-backed experiments.",
        )
        st.session_state["anthropic_key"] = anthropic_key
        st.session_state["openai_key"] = openai_key


def render_answer(query: str, use_live_llm: bool) -> None:
    agent = load_agent()
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
    st.caption("SEC filing excerpts in, cited answers out.")

    example_queries = [
        "Which companies disclosed customer-concentration risk?",
        "What export-control exposure was cited in 2024 filings?",
        "Which firms mentioned advanced packaging capacity constraints?",
        "Where did filings mention supplier concentration or sole-source suppliers?",
    ]

    selected_example = st.selectbox("Examples", options=example_queries, index=0)
    query = st.text_input("Question", value=selected_example)
    cols = st.columns([1, 1, 4])
    with cols[0]:
        live_llm = st.toggle("Live Claude", value=False)
    with cols[1]:
        ask = st.button("Ask", type="primary")

    if ask and query.strip():
        render_answer(query.strip(), live_llm)


if __name__ == "__main__":
    main()
