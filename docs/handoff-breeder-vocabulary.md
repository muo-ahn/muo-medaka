# Handoff: breeder vocabulary → seed

Written 2026-09-29, at the end of the session that built the breeder vocabulary.
The next session can start from this file alone.

## Where things stand

The vocabulary job is done and verified, but **nothing is committed**.

| path | state |
|---|---|
| `docs/research/breeder-vocabulary-2026-09.md` | the write-up (Korean). Seed findings are in §seed에 대한 발견 |
| `docs/research/breeder-vocabulary-2026-09.csv` | 628 terms, every row with a source URL |
| `docs/research/breeder-vocabulary-relations-2026-09.csv` | 967 relations, closed set of 6 types |
| `.harness/spec.md` | the spec for the vocabulary job. AC-1..AC-7 all pass |
| `.harness/rulings.md` | R-01..R-15, one line each |
| this file | — |

All of the above are untracked. The current branch is `ci-neo4j`, which also
holds **unrelated uncommitted CI work** (`.github/workflows/ci.yml`,
`tests/test_graph_integration.py`, `tests/test_pipeline_integration.py`). Do
not commit the vocabulary on top of it.

**The build scripts now live in the repo**, at `scripts/vocab/` (see its
README.md for the run order). The original file list noted here was
incomplete — it also included `build_morph.py`, `build_strain.py`, and the
`fragments/` directory of tables pasted into the write-up doc, alongside
`build_vocab.py`, `check_vocab.py`, `ids.json`, the three TSVs, and the
`*_sources.md` logs. `raw/` (fetched third-party page text, including but not
limited to the JMA manual) was copied too but is gitignored, so it stays on
disk only; a fresh checkout needs to re-fetch it before a full rebuild. See
`scripts/vocab/README.md` for what each raw file is and where it came from.

## What the user asked for next

In order, stated 2026-09-29, then paused ("일단 handoff.md만"):

1. Commit the vocabulary on a **new branch** cut from `main` (not `ci-neo4j`).
   Only the untracked files listed above; leave the CI work where it is.
2. **(a) Reflect the seed findings in `data/seed/`.**

Write a new `.harness/spec.md` for (a) before starting — the current spec lists
seed edits as a non-goal. Keep the old one's AC list in its `## 변경 이력`
or move it aside; do not silently overwrite it.

## The (a) worklist

From §seed에 대한 발견 of the write-up. The JMA manual (改良メダカ品種分類マニュアル
第5版, 2025-09, free PDF at jma-medaka.com) is the anchor source. It is the
manual `01-sources-breeder.yaml` says was "not cited, deliberately" because
nobody had read it. It has now been read, so it can be added as a `:Paper`,
and the comment there should be updated.

| seed trait | now | finding | confidence |
|---|---|---|---|
| tenme | unverified label 天眼 | no page uses 天眼. Kon's "small pupil" matches JMA スモールアイ; one breeder blog calls that 点目 (てんめ) | 点目 is **one source**, no printed reading. Keep it in `unverified_labels`, not `japanese_name` |
| hikari | label 光; description says the dorsal fin is shaped like a **pelvic** fin | hobby writes ヒカリ; 光 is the luster word. JMA and hinsyu-zukan both say the dorsal fin copies the **anal** fin | label: strong. Description: check Kon 2026 Table 1 wording first — if Kon says pelvic, record the disagreement, don't just overwrite |
| kuroaka | 黒赤 | hobby writes 赤黒 (hinsyu-zukan); JMA two-colour notation 黒オレンジ | strong |
| fukumaku | 腹膜 | 腹膜 is the body part; trait is 腹膜青 / 腹膜光 | medium — pick using Kon's "blue" |
| akabuchi | 赤斑 | no page writes 赤斑; nearest is the 白朱赤 family. 朱赤斑 means something else | leave unverified, note it |
| black | 黒 | ブラック; bare 黒 reads as wild-type 黒メダカ | partial |
| nijikin | 虹金 | no page, no matching hobby trait | note "no hobby term found" |
| fusahire | unverified 房ヒレ | only フサヒレ is attested | already flagged in the seed comment |
| miyuki | category BODY_COLOR | JMA treats 幹之 as 体外光, a luster trait | category decision; there is no LUSTER in `TraitCategory`, so this is a vocabulary change → ADR territory. Raise it, don't do it inside (a) |
| Da mutant | lab-only aliases | hobby name Daタイプ (= ヒカリ体型) exists | alias? Check PRD §8: aliases are naming variants, not biological identity |
| gold | no label | 黄金 is two things: おうごん (body colour) vs こがね (a GEX strain) | label only with the reading |
| longfin | — | **do not** attach ロングフィン. The hobby term has ≥4 definitions, none equal to Kon's | confirms the existing warning in `12-entities-breeder-traits.yaml` |

Rules to respect while editing (all already in the repo):

- `japanese_name` only for strings a source actually prints; everything else goes
  in `unverified_labels` with `UNVERIFIED_LABEL` in `review_reasons`.
- A new breeder source goes in `01-sources-breeder.yaml` with URL, access date
  and a note on what it does and doesn't say.
- Finish with `python -m medaka_ontology.cli validate` and `pytest`.

## Open items the user has not decided

- The authority order used (JMA > 도감 > 번식장 > 블로그) is provisional.
- Whether strain names (328 collected, not saturated) become an ontology layer.
  That would need a `composed_of`-style predicate and an ADR.
- Korean renderings are thin (Naver was blocked); 111 relations point at terms
  not yet collected (top: シルバー, 緑, 金色, ヒレ黄, 赤黒).
- 上物 (bv:0277) is flagged unverified: its only cited source does not print it.
