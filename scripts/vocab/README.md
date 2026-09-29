# scripts/vocab

Build scripts and raw research data behind
`docs/research/breeder-vocabulary-2026-09.csv` and
`docs/research/breeder-vocabulary-relations-2026-09.csv` — a term list and
relation table mapping Japanese/Korean breeder vocabulary onto the ontology.
See `docs/handoff-breeder-vocabulary.md` for the job that produced them and
`.harness/rulings.md` (R-01..R-15) for the decisions baked into the code below.

## Files

| file | what it is |
|---|---|
| `color.tsv`, `morph.tsv`, `strain.tsv` | the three collected term tables (body color/pattern/luster, body shape/fin/eye morphology, named strains+modifiers+jargon), one axis-lane per file |
| `build_morph.py` | generates `morph.tsv` from transcribed source data (writes into this directory) |
| `build_strain.py` | generates `strain.tsv` from transcribed source data (writes into this directory) |
| `build_vocab.py` | merges `color.tsv` + `morph.tsv` + `strain.tsv` into the two output CSVs under `docs/research/`, plus the `fragments/` tables pasted into the write-up doc. Stable term/relation ids persist in `ids.json`. |
| `check_vocab.py` | self-check (AC-1..AC-5, AC-7 structure) over the generated CSVs; exits 1 on failure |
| `ids.json` | persisted stable ids, read and rewritten by `build_vocab.py` on every run |
| `color_sources.md`, `morph_sources.md`, `strain_sources.md` | per-lane source log: pages visited, what each one contributed, saturation notes |
| `fragments/` | small `.md`/`.json` tables `build_vocab.py` regenerates each run, meant to be pasted into the research write-up |
| `raw/` | fetched third-party page text, not committed (see below) |

## Run order

`color.tsv` was collected by hand (no build script for it in this directory).
To regenerate everything downstream of the three TSVs:

```
python scripts/vocab/build_morph.py
python scripts/vocab/build_strain.py
python scripts/vocab/build_vocab.py
python scripts/vocab/check_vocab.py
```

`build_vocab.py` and `check_vocab.py` default to the repo root derived from
their own location (two directories up); pass a path as the first argument to
override, e.g. `python scripts/vocab/build_vocab.py D:\other-checkout`.

Regeneration is meant to be byte-identical to what's already committed under
`docs/research/` as long as `color.tsv`/`morph.tsv`/`strain.tsv`/`ids.json`
are unchanged.

## `raw/` (not committed)

`scripts/vocab/raw/` is gitignored — these are full-text captures of
third-party pages, same policy as `data/fulltext/` elsewhere in this repo.
`build_vocab.py` reads `raw/jma5.txt` and `raw/aqualab_yougo.txt` at run time
(to attribute relations to a source page, ruling R-09); the other two files
were reference material used while transcribing `morph.tsv`/`strain.tsv` by
hand and are not read by any script. Re-running the build scripts from a
fresh checkout needs at least the two files `build_vocab.py` reads.

| file | fetched from |
|---|---|
| `jma5.txt` | https://jma-medaka.com/wp-content/uploads/2022/08/250901_【公式】品種分類マニュアル_第５版.pdf (JMA breed classification manual, 5th ed.; extracted with `pdftotext -enc UTF-8`) |
| `aqualab_yougo.txt`, `aqualab_yougo.html` | https://www.practical-aqualabo.com/medaka-yougoshu/ |
| `dc.html` | https://gall.dcinside.com/board/view/?id=fish&no=985428 |
| `hz_notes.txt` | notes transcribed from pages under https://hinsyu-zukan.satumano-medakayasan.com/ (strain listing pages, see `HZROOT`/`H()` in `build_strain.py`); not a single-page capture, so no single URL fully accounts for it |
