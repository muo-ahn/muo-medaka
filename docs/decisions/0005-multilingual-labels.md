# ADR 0005 — Multilingual labels

- **Status**: Accepted
- **Date**: 2026-10-01
- **Context**: Until now an entity had three name fields: `japanese_name` (one
  string), `aliases` (sourced, in practice ASCII) and `unverified_labels`
  (reconstruction). The breeder-vocabulary survey (2026-09, 628 terms, PR #10)
  showed the three do not fit the data. A trait has one preferred Japanese name
  *and* several attested synonyms (yellow: 黄, ヒメダカ, 緋目高); a Japanese word
  has a reading that tells it apart from a homograph (黄金 read おうごん, a trait,
  against 黄金 read こがね, a GEX strain); the same word has Korean and romanised
  renderings the trade prints (히메다카, Kohaku). A single `japanese_name` forced one
  attested string into the unverified list (R-26), and writing the reading into
  the string (黄金（おうごん）, R-20) broke exact search for the bare word. The
  second-pass audit (docs/research/vocabulary-audit-2026-10.md) found the pattern
  in four places.

## Decision

### The ontology has no language restriction

**Entity names may be written in any language, mixed freely: English, Japanese,
Korean, or any other.** Nothing in the vocabulary, the loader or the graph limits
a label to a language, and none will be added. A trait may carry labels in several
languages at once, and a new language needs no schema change, only a label with
its tag.

What the ontology does require is that a string says **which language it is in**
and **who prints it**.

**For strains and traits from the trade, the Japanese original is the reference
and renderings in other languages sit beside it as synonyms.** The trade is
Japanese, its names are coined in Japanese, and a Korean 히카리 or an English
"hikari" is a rendering of ヒカリ, not a rival name. This is a convention about
which label is PREFERRED and which hang off it, not a rule about what may be
written. The romanised `name` stays the entity's identifier (it is what the seed
paper prints and it is stable); it is not claimed to be anybody's spelling.

### A `Label` per name

`Entity.labels` is a list of `Label`:

| field | meaning |
|---|---|
| `text` | the string, exactly as printed |
| `lang` | BCP 47 tag: `ja`, `ja-Latn` (romanised Japanese), `ko`, `en`, `zh-Hant` ... |
| `kind` | `PREFERRED` (at most one per language), `SYNONYM`, `ROMANIZATION`, `VARIANT` (the same word spelled differently: kana against kanji, a misspelling a source prints) |
| `reading` | how it is read, in kana for Japanese. Separate from `text`, so an exact search for 黄金 finds it and おうごん still tells it from こがね |
| `status` | `ATTESTED` or `UNVERIFIED` |
| `sources` | `Paper.key` of each source that prints it |
| `vocab` | `bv:NNNN` rows of `docs/research/breeder-vocabulary-2026-09.csv` |
| `note` | why, when the reason is not obvious |

An `ATTESTED` label must name a source or a survey row; the model refuses one that
does not. A label with no source is kept, as `UNVERIFIED`, and its entity must
carry `UNVERIFIED_LABEL` (PRD §2.4, enforced by a test). Unsourced text therefore
never reads as sourced, which is the property the old field split existed to
protect and which a flat ban on non-ASCII aliases only approximated.

`vocab` is checked against the survey, not just for existence: a test requires that
a cited row print the label's own string in the label's language (kana, width and
katakana/hiragana folded), and that a `jma5` source be cited only when the row
lists the 5th-edition manual.

### The old fields are derived, not removed

`japanese_name`, `aliases` and `unverified_labels` are filled from `labels` when
it is set: the attested PREFERRED `ja` label becomes `japanese_name`, every other
attested label an alias, every unverified one an unverified label. Dossier, query,
lexicon, resolution and full-text search read those fields and keep working. Writing
both on one entity is an error, not a merge, because two places to write a name is
two sources of truth.

In the graph a label is also a `:Label` node (`LABEL_OF` the entity, `ATTESTED_BY`
its papers), so "which source prints this synonym" is a query, and the dossier
prints a `Names` section from a flat `labels_display` copy on the entity.

## Consequences

- Seed traits were migrated to `labels` with the per-trait provenance comments kept.
  Korean labels are attached only where the survey's `term_ko` is a clean rendering
  of one word; mixed or glossed cells (시로메다카(白メダカ)) are not.
- Several decisions the old structure forced were reversed (R-43, R-44): ヒメダカ is
  an attested label of yellow, スモールアイ of tenme.
- ロングフィン is **not** attached to longfin or hirenaga, and Daタイプ is **not** on
  the laboratory Da mutant: those were identity claims, not spellings (R-41,
  PRD §8).
- Labels cost a node each, 107 in the seed today; not a concern at this scale.
