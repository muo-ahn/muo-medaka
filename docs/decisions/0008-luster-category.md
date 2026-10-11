# ADR 0008 — A LUSTER trait category

- **Status**: Accepted
- **Date**: 2026-10-11
- **Context**: `TraitCategory` followed the sectioning of Kon et al. 2026 Table 1:
  body colour, body shape, fin morphology, eye morphology, scale, other. The JMA
  5th-edition manual (`jma5`) sections the hobby's traits differently and has a
  place for reflective light that is not a body colour: 体外光 (§3.4.2), with its
  形質補足 鱗光, and the iridophore group around it (§3.4). Nothing in our
  vocabulary could hold a trait of that kind. The one candidate already in the
  seed, miyuki, was left in BODY_COLOR with a note that "whether to add a luster
  category is an ADR question" (`data/seed/10-entities-traits.yaml`,
  `docs/handoff-breeder-vocabulary.md`). The manual's own description of 体外光
  (blue-white light on the back, thick, iridophores also on the fins) is not a
  colour of the body, and filing it under BODY_COLOR or SCALE would misdescribe it.

## Decision

1. **`TraitCategory.LUSTER` is added.** It is for traits whose defining feature is
   reflected light on the body surface rather than a pigment colour or a structure.
2. **A trait's category follows the sectioning of the source that defines it.**
   Kon traits keep their Kon Table 1 section; a trait first defined by the JMA
   manual takes the JMA section it sits in. This is a rule about provenance, not a
   claim that the two sectionings agree.
3. **Kon traits are not moved.** miyuki, rame, aurora, panda, toumeirin and the rest
   stay where Kon Table 1 puts them, even though JMA files miyuki and rame under the
   iridophore group. miyuki's definition in Table 1 also includes reduced
   melanophores and xanthophores, which a luster-only category would drop.
4. The first members are `taigaikou` (体外光) and `rinkou` (鱗光), both defined by
   `jma5` §3.4.2.

## Consequences

- Category is not evidence of identity. That miyuki is BODY_COLOR and taigaikou is
  LUSTER says nothing about whether they are the same biology; no trait-to-trait
  claim joins them (R-36, R-80). They meet only through the shared phenotype
  `ectopic dorsal iridophore`.
- A reader filtering on LUSTER will not see miyuki. That is accepted: the filter
  answers "what has the trade defined as a luster trait", and the miyuki entity's
  label note points at `taigaikou`.
- If a later pass wants Kon traits recategorised, it needs its own decision; the
  rule above makes "the source's sectioning" the default, so it would be a change
  to the rule, not an exception to it.
- The open item in `docs/handoff-breeder-vocabulary.md` (miyuki, category) is
  resolved by this record: category stays BODY_COLOR.
