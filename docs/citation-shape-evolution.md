# Citation shape evolution

[DEC-CIT-002](../decisions/DEC-CIT-002-citations-carry-filing-level-identifiers.md)
flagged the `Citation` dataclass as `reversible: false` because the
shape is consumed by `app.py`, the verifier, the answerer, the eval
suite, and the tests. Dropping a field requires touching every
consumer in lockstep. This note sketches the V2 evolution path so a
future change has a documented forward route that does not require
a hard cutover.

## current shape

The dataclass lives at `src/retrieval/citations.py`:

```python
@dataclass(frozen=True)
class Citation:
    label: str
    cik: str
    accession: str
    section: str
    span_text: str
    span_offsets: tuple[int, int]
    chunk_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

Eight fields total (the seven named in DEC-CIT-002 plus `label`).
`as_dict()` returns a serializable view; `citation_from_chunk`
builds a citation from a retrieved chunk and a verbatim span and
raises on missing spans.

Consumers today:

- `app.py` reads `as_dict()` to render the citations expander
  (label, company, filing_type, year, cik, accession, section,
  span_text, span_offsets).
- `src/agent/answerer.py` constructs `Citation` objects through
  `citation_from_chunk` and passes them through `verify_citations`.
- `src/retrieval/citations.py` `verify_citations` reads
  `chunk_id`, `span_offsets`, and `span_text` to check the cited
  span against retrieved chunks.
- `eval_suites/citation_faithfulness.yaml` cases run through the
  full answerer + verifier pipeline; the verifier's pass/fail is
  the suite's signal.
- `tests/test_citations.py` constructs `Citation` instances
  directly and asserts the verifier behavior on the dataclass
  shape.

## why a field shrink is irreversible today

Removing a field — say, `section` — would silently break the
citations expander in `app.py`, the verifier's chunk-id lookup, and
every test that constructs a `Citation` with the old shape. The
frozen dataclass makes mutation impossible, which is the intended
guarantee for an audit artifact, but it also means a shape change
ripples through every constructor call site.

A field add is safer because the frozen-dataclass constructor with
default values can absorb new fields without breaking older
constructor sites. The `metadata` dict already serves as the
forward-compatibility escape hatch for fields not yet promoted.
But a field add still requires the verifier and the renderer to
know how to handle the new field, and consumers that round-trip
through `as_dict()` need to know whether to forward it.

## proposed CitationV2 shape

`CitationV2` would live alongside `Citation` in
`src/retrieval/citations.py`. The V2 shape adds fields without
removing any, and adds a structured `provenance` field that
captures the retrieval path that produced the citation:

```python
@dataclass(frozen=True)
class CitationV2:
    # Every field from V1, unchanged.
    label: str
    cik: str
    accession: str
    section: str
    span_text: str
    span_offsets: tuple[int, int]
    chunk_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    # New in V2.
    retrieval_rank: int = 0           # Where in the top-k this chunk landed.
    retrieval_score: float = 0.0      # The hybrid-ranker combined score.
    verifier_version: str = "v1"      # Which verifier signed this off.
    source_url: str | None = None     # SEC EDGAR canonical URL if known.
```

The four new fields are all additive. `retrieval_rank` and
`retrieval_score` carry forward debugging signal that today gets
lost between the ranker and the renderer. `verifier_version` makes
the audit trail explicit when the verifier evolves.
`source_url` is the forward-looking field a future ingestion
path can populate when the full EDGAR fetch is in scope.

A conversion helper `citation_v1_to_v2(c1: Citation) -> CitationV2`
maps every V1 field across and fills the new fields with defaults.
A reverse helper `citation_v2_to_v1(c2: CitationV2) -> Citation`
drops the new fields. Both helpers stay in tree for the dual-type
period.

## migration path

The dual-type period is the heart of the reversibility story. The
forward path is:

1. **Land V2 alongside V1.** No consumer changes. The verifier,
   the answerer, the renderer, the eval suite, and the tests all
   keep operating on `Citation`. `CitationV2` ships in the module
   but is unused.
2. **Wire one consumer to V2.** Pick the lowest-stakes consumer
   first — the citations expander in `app.py`. Add a feature flag
   on `ModelConfig` (`citation_shape_version`, default `"v1"`)
   that selects which shape `render_answer` reads. With the flag
   off, V1 ships unchanged; with the flag on, V2 renders the
   extra fields.
3. **Run the four-suite gate.** The verifier still operates on
   V1; the eval suite still passes. The gate confirms that the
   dual-type wiring did not regress citation faithfulness.
4. **Promote the next consumer.** Wire the verifier to accept
   both shapes (the `_to_chunk` helper already accepts
   `DocumentChunk` or any `SearchResult`-like object via duck
   typing; the same pattern extends to V1/V2). Re-run the gate.
5. **Switch the answerer's default to V2.** The answerer
   constructs citations through `citation_from_chunk`; the V2
   factory becomes the default, and V1 is built by downgrading
   through `citation_v2_to_v1` when a consumer explicitly opts
   in. Re-run the gate.
6. **Deprecate V1.** After at least one release cycle with V2 as
   the default, mark V1 deprecated in a follow-up DEC. Remove
   the V1 dataclass only after every consumer has migrated.

A field shrink — the move that DEC-CIT-002 flagged as irreversible
— is a special case of step 6. To shrink V1's shape, ship the
shrunk shape as V2, migrate consumers across the dual-type period,
and remove V1 in a later commit. The shrink is no longer a
single-commit shape change; it is a multi-release migration with
an eval gate at every step.

## conditions for V2 ship

The V2 dataclass is a sketch today, not a commit. It ships when:

- A real consumer needs a field V1 cannot supply. The
  `source_url` field is the likeliest trigger — once the
  full-EDGAR fetch lands, a citation should resolve to a clickable
  SEC URL, and putting that on the dataclass is cleaner than
  packing it into `metadata`.
- The full-EDGAR ingestion is in scope and the larger corpus
  starts producing citation candidates where retrieval rank and
  score carry interpretive signal a reviewer needs.
- A second verifier version is on the roadmap and the audit
  trail benefits from knowing which verifier signed off.

If none of those conditions are present, V1 stays canonical and
the V2 sketch stays in this design note. The DEC-CIT-002
amendment captures the policy: forward-thinking does not require
the V2 dataclass to land before a real consumer needs it.

## conditions for reversing course

The V2 sketch gets discarded if:

- The metadata dict turns out to be the right home for every new
  field we have proposed. If `source_url`, `retrieval_score`, and
  `verifier_version` can live in `metadata` without losing
  type-safety in their consumers, the V2 dataclass adds
  ceremony for no audit benefit.
- A field shrink is never needed across the V1 lifetime. The
  dataclass is small (eight fields); the worst case is one or
  two of the seven DEC-CIT-002 fields turning out to be
  unnecessary. If that does not happen in 2026, the V2 sketch
  was a useful exercise but not a needed commit.
- The eval gate catches a problem with the V2 wiring that the
  dual-type approach cannot fix. The current design assumes the
  verifier can accept either shape; if a future verifier change
  makes that infeasible, the V2 sketch needs a redesign before
  any consumer migrates.

In any of those cases, the canonical answer is the same: V1
stays, the sketch stays in this note as a documented
not-taken path, and the DEC-CIT-002 lock-in stands.
