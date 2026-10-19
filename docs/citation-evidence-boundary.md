# A real quote can still name the wrong filing

The citation verifier now checks the citation's CIK, accession and section against
the retrieved chunk before checking its span. Previously a valid chunk ID and
verbatim span could pass while one of those filing identity fields had been
replaced. The negative tests independently alter each field and require rejection.
They failed against the prior verifier and pass with the identity check.

This closes a specific attribution gap. It does not establish that the cited
passage entails every sentence in an answer, that a filing is current, or that a
retrieved excerpt is a complete account of the supplier's risk. A verified quote
should be described at that scope.

For a later AIP evaluation pilot, keep the current deterministic retrieval and
default model configuration fixed. Add matched cases for a correct citation,
wrong filing identity, unsupported paraphrase and a later contradictory filing.
Have a checker inspect the retrieved passages and the question before seeing the
answer author's claim that citation quality passed. Score attribution, semantic
support, recency and appropriate refusal separately.

The current code and offline suites establish attribution and exact-span checks.
The semantic and contradictory-filing experiment remains proposed. A prompt or
model change still requires the repository's paired evaluation records and must
not be inferred from a stronger test fixture alone.

The reviewer experiment is motivated by
[Audit Without Verification](https://arxiv.org/abs/2609.07680), while
[AI Product Team's evaluation workflow](https://github.com/3orionkings/ai-product-team/blob/main/workflows/evaluate-feature.md)
offers a way to freeze criteria and keep failure slices visible. No private brief
content, live filing fetch, API call, prompt change or deployment is included.
