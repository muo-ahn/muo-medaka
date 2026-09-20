# ADR 0002 — Extraction proposes; it never asserts

- **Status**: Accepted
- **Date**: 2026-09-20
- **Context**: [issue #1](https://github.com/muo-ahn/muo-medaka/issues/1), §4 "Extraction contract"

## Decision

The discovery pipeline extracts **co-mentions**, not readings. When two entities
the ontology already knows appear in one sentence, that sentence becomes a
`:Candidate` with the verbatim quote attached. A person assigns the evidence
level and accepts it, or rejects it. Nothing the pipeline produces enters the
ontology on its own.

The extractor does not parse sentences, does not decide what authors meant, and
does not resolve negation — it flags a negated sentence and leaves the reader to
read it.

## Why not do better

An LLM could read these papers and produce far richer claims. That is precisely
the risk. This repository exists because "this variety is caused by gene X"
circulates without its evidence grade until it hardens into fact (PRD §2.2, §5);
the seed data alone contains three source-level contradictions that a confident
reader would have flattened into one answer. An extractor that inferred claims
would manufacture exactly that failure at machine speed, and — worse — hand each
fabrication a provenance trail that looked respectable.

Co-mention plus the verbatim sentence is the strongest output available here
that cannot be wrong about what a paper says. It can be *irrelevant*; it cannot
be a misreading, because there is no reading.

Evidence level is handled the same way. Cue phrases (`genome editing`, `GWAS`,
`co-segregating`) suggest a level and the matched phrase is stored beside it, but
the candidate carries `UNKNOWN` until a human accepts it. A reviewer can check a
phrase; nobody can check a bare label.

## What this costs

- New ornamental traits cannot be discovered automatically. Naming an unfamiliar
  trait found in text is named-entity recognition, which is the inference above.
  New traits arrive when a person reads a quote in the queue.
- Gene symbols are the one exception, because gene nomenclature is an
  orthographic convention rather than a judgement: a lowercase token ending in a
  digit, next to a known entity, is proposed as a `:ProposedEntity`. Symbols
  without digits (`tyr`, `kita`, `pmela`) are invisible to that rule and stay
  invisible — loosening it would propose every noun in the paper.
- Recall is lower than a reading-based extractor would achieve.

The review queue is the scarce resource. Precision is worth more than recall
here, and a queue nobody trusts is a queue nobody reads.

## What the first real run changed

Four things were wrong in ways only real literature exposed, and each is now
pinned by a test:

1. **`Da` in a query.** A two-character alias retrieved essentially every medaka
   paper ever published. Query terms now go through a specificity rule.
2. **`hikari` in a full-text query.** Hikari is a major aquarium fish-food brand,
   so unrestricted search returned neurotoxicology papers that merely listed what
   they fed the fish. Trait queries are now scoped to title and abstract; gene
   and mechanism queries stay on full text, which is where their value is.
3. **A section allowlist.** Matching section titles against `Results`,
   `Discussion` and so on discarded two thirds of every article, because papers
   title their sections things like "Population genomic analyses". It is a
   denylist now — references and front matter out, everything else in.
4. **Sentence-local species detection.** A corn-snake paper contains sentences
   naming no species at all; judged individually they were medaka findings.
   Species is now determined from the paper's title and abstract and used as the
   default for every sentence in it.

## The acceptance path

Accepting a candidate constructs a `models.Claim` and calls the same
`ingest.ingest_claim` the seed loader uses. This is deliberate and was validated
the hard way: the first implementation of the comparative-evidence ceiling lived
partly on the `Claim` model (trait subjects) and partly in the seed loader (gene
subjects), and the acceptance path went through neither — so corn-snake evidence
about a medaka gene could be accepted at `FUNCTIONAL_VALIDATION`. The rule now
lives on the model, with the subject's species passed in by whoever knows it.

One write path, one set of rules. A second set would be a second set, and the
weaker one wins eventually.
