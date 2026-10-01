"""Audit the first-pass vocabulary unification (PR #10) mechanically.

Run from anywhere:

    python audit_vocab.py <repo-root> [<out.csv>]

Reads the two CSVs under docs/research/ and the seed YAML, prints a report and
writes one row per finding to <out.csv>, by default
<repo-root>/docs/research/vocabulary-audit-2026-10.csv (never the cwd). It
changes no data: every fix lives in the seed or in the second-pass rulings, so
a finding and the decision taken on it stay separable.

Checks, the three the 2026-10 job asked for:

1. scattered synonyms -- two rows that normalise to the same string, or share
   an English/Korean rendering, with no relation between them;
2. wrong merges -- `same_as` read transitively joins two terms the table itself
   says collide, or joins two different seed traits; one row built from lanes
   that disagree on what the word is;
3. orthographic drift -- the seed's romanisation versus the trade's English
   spelling of the same term, and seed labels the survey attests but the seed
   still files as unverified (or does not carry at all).
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(sys.argv[1])
TERMS = ROOT / "docs/research/breeder-vocabulary-2026-09.csv"
RELS = ROOT / "docs/research/breeder-vocabulary-relations-2026-09.csv"
SEED = ROOT / "data/seed"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs/research/vocabulary-audit-2026-10.csv"

_HIRA = {chr(c): chr(c + 0x60) for c in range(0x3041, 0x3097)}


def norm_ja(text: str) -> str:
    """Fold width, hiragana/katakana, ヶ/ケ, spaces and middle dots.

    The long-vowel mark and dakuten are kept: folding dakuten would merge ヒレ
    and ビレ, which the trade keeps apart only by context.
    """
    t = unicodedata.normalize("NFKC", text)
    t = "".join(_HIRA.get(ch, ch) for ch in t)
    t = t.replace("ヶ", "ケ").replace("ヵ", "カ")
    return re.sub(r"[\s・･　]", "", t)


def norm_romaji(text: str) -> str:
    """Fold Hepburn / wapuro / macron spellings of one romanised word."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[^a-z]", "", t)
    for a, b in (("ou", "o"), ("oo", "o"), ("uu", "u"), ("aa", "a"), ("ii", "i"), ("ee", "e")):
        t = t.replace(a, b)
    return t


def norm_ko(text: str) -> str:
    return re.sub(r"[\s()（）\-·]", "", unicodedata.normalize("NFKC", text))


def strip_reading(label: str) -> str:
    return re.sub(r"（.*?）|\(.*?\)", "", label)


def load():
    terms = list(csv.DictReader(TERMS.open(encoding="utf-8-sig")))
    rels = list(csv.DictReader(RELS.open(encoding="utf-8-sig")))
    entities = []
    for path in sorted(SEED.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for e in raw.get("entities", []):
            entities.append(derive_names({**e, "_file": path.name}))
    return terms, rels, entities


def derive_names(e: dict) -> dict:
    """Entities written with `labels` (ADR 0005) get the three older name fields
    the checks below read, folded the way models.Entity._derive_from_labels does:
    the attested PREFERRED ja label is japanese_name, other attested labels are
    aliases, unverified ones unverified_labels. The audit therefore reads the
    pre-labels seed (the baseline) and the current one with the same checks."""
    labels = e.get("labels")
    if not labels:
        return e
    ja = next(
        (
            lab for lab in labels
            if lab.get("lang") == "ja" and lab.get("kind") == "PREFERRED"
            and lab.get("status", "ATTESTED") == "ATTESTED"
        ),
        None,
    )
    out = dict(e, _has_labels=True)
    out["japanese_name"] = ja["text"] if ja else None
    out["aliases"] = [
        lab["text"] for lab in labels
        if lab.get("status", "ATTESTED") == "ATTESTED" and lab is not ja
    ]
    out["unverified_labels"] = [
        lab["text"] for lab in labels if lab.get("status", "ATTESTED") != "ATTESTED"
    ]
    return out


ROWS: list[dict] = []


def add(check: str, severity: str, subject: str, detail: str) -> None:
    ROWS.append({"check": check, "severity": severity, "subject": subject, "detail": detail})


def pairs(rels, kinds):
    return {
        frozenset((r["subject_id"], r["object_id"]))
        for r in rels
        if r["relation"] in kinds and r["object_id"]
    }


def check_scattered(terms, rels):
    # Linked = reachable through any naming relation, so a chain A=B=C does not
    # report A,C as scattered.
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in (tuple(p) for p in pairs(
            rels, {"same_as", "variant_spelling", "narrower", "broader", "collides_with"})):
        parent[find(a)] = find(b)
    linked = {frozenset((a, b)) for a in parent for b in parent if find(a) == find(b)}
    by_id = {t["id"]: t for t in terms}

    def report(check, key_fn, label):
        groups = defaultdict(set)
        for t in terms:
            for key in key_fn(t):
                if key:
                    groups[key].add(t["id"])
        for key, ids in sorted(groups.items()):
            ids = sorted(ids)
            if len(ids) < 2:
                continue
            unlinked = [
                (a, b)
                for i, a in enumerate(ids)
                for b in ids[i + 1 :]
                if frozenset((a, b)) not in linked
            ]
            if unlinked:
                names = ", ".join(
                    f"{i} {by_id[i]['term_ja']} [{by_id[i]['kind']}/{by_id[i]['axis']}]" for i in ids
                )
                add(check, "medium", key, f"{label} {key!r} shared by {names}; "
                    f"{len(unlinked)} pair(s) unrelated")

    report("1-scattered:ja-normalised", lambda t: [norm_ja(t["term_ja"])], "normalised ja")

    def en_keys(t):
        out = []
        for part in re.split(r"\s*/\s*", t["term_en"]):
            part = re.sub(r"\(.*?\)", "", part).strip()
            if part and "inferred" not in t["term_en"] and len(norm_romaji(part)) > 3:
                out.append(norm_romaji(part))
        return out

    report("1-scattered:en", en_keys, "English/romaji rendering")
    report(
        "1-scattered:ko",
        lambda t: [norm_ko(p) for p in re.split(r"\s*[/,]\s*", t["term_ko"]) if p.strip()],
        "Korean rendering",
    )


def check_wrong_merges(terms, rels):
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in rels:
        # A same_as marked disputed: is a recorded disagreement between sources,
        # which no transitive reading may cross (build_vocab.py, R-38).
        if (
            r["relation"] in {"same_as", "variant_spelling"}
            and r["object_id"]
            and "disputed:" not in r["basis"]
        ):
            a, b = find(r["subject_id"]), find(r["object_id"])
            parent[a] = b
    clusters = defaultdict(set)
    for x in list(parent):
        clusters[find(x)].add(x)
    by_id = {t["id"]: t for t in terms}

    def show(ms):
        return ", ".join(f"{m} {by_id.get(m, {}).get('term_ja', '?')}" for m in sorted(ms))

    for r in rels:
        if r["relation"] != "collides_with" or not r["object_id"]:
            continue
        a, b = r["subject_id"], r["object_id"]
        if a in parent and b in parent and find(a) == find(b):
            add("2-wrong-merge:collision-inside-same_as-cluster", "high",
                f"{a} {r['subject_term']} ~ {b} {r['object_term']}",
                f"marked collides_with, yet joined by a same_as chain: {show(clusters[find(a)])}")

    seed_of = defaultdict(set)
    for r in rels:
        if r["relation"] == "seed_match":
            seed_of[r["subject_id"]].add(r["object_id"])
    for _, members in clusters.items():
        seeds = set().union(*(seed_of.get(m, set()) for m in members))
        if len(seeds) > 1:
            add("2-wrong-merge:same_as-cluster-spans-seed-traits", "high", ", ".join(sorted(seeds)),
                f"one same_as cluster maps to {len(seeds)} seed traits: {show(members)}")

    for t in terms:
        notes = t["notes"]
        if "kind 이견" in notes:
            add("2-wrong-merge:row-merged-across-kinds", "low", f"{t['id']} {t['term_ja']}",
                f"kind={t['kind']}; lanes disagreed on what the word is: "
                + re.sub(r"\s+", " ", notes)[:220])


def check_seed(terms, rels, entities):
    by_id = {t["id"]: t for t in terms}
    matches = defaultdict(list)
    for r in rels:
        if r["relation"] == "seed_match":
            matches[r["object_id"].removeprefix("seed:")].append(r)

    owners = defaultdict(set)
    for e in entities:
        jn = e.get("japanese_name")
        for s in [jn and strip_reading(jn), *e.get("unverified_labels", []), *e.get("aliases", [])]:
            if s:
                owners[norm_ja(s).lower()].add(e["name"])
    for key, names in sorted(owners.items()):
        if len(names) > 1:
            add("3-seed:same-label-on-two-entities", "medium", key, f"carried by {sorted(names)}")

    for e in entities:
        if e.get("label") != "OrnamentalTrait":
            continue
        name = e["name"]
        unverified = {norm_ja(s) for s in e.get("unverified_labels", [])}
        jn = e.get("japanese_name")
        attested = {norm_ja(strip_reading(a)) for a in e.get("aliases", [])}
        carried = unverified | attested | ({norm_ja(strip_reading(jn))} if jn else set())
        for r in matches.get(name, []):
            t = by_id.get(r["subject_id"])
            if t is None:
                continue
            key = norm_ja(t["term_ja"])
            tier = t["best_tier"][:1]
            sourced = r["basis"].startswith("source:")
            if key in unverified and sourced and tier in {"1", "2"} and not t["unverified"]:
                add("3-seed:attested-label-filed-unverified", "high", f"{name} / {t['term_ja']}",
                    f"{t['id']} is a tier-{tier} seed_match on a source: basis with no "
                    f"unverified flag, but the seed keeps it in unverified_labels")
            elif key not in carried and sourced and tier in {"1", "2"}:
                add("3-seed:attested-synonym-missing", "medium", f"{name} / {t['term_ja']}",
                    f"{t['id']} (tier {tier}, {t['kind']}) matches this trait on a source: basis "
                    "and is on no label field of the entity")
            elif key not in carried and not sourced:
                add("3-seed:inferred-match-not-recorded", "low", f"{name} / {t['term_ja']}",
                    f"{t['id']} seed_match is inferred ({r['basis'][:80]}); fine to leave off, "
                    "listed for completeness")
            for part in re.split(r"\s*/\s*", t["term_en"]):
                part = re.sub(r"\(.*?\)", "", part).strip()
                recorded = {a.lower() for a in e.get("aliases", [])}
                if (
                    part
                    and part.isascii()
                    and norm_romaji(part) == norm_romaji(name)
                    and part.lower().replace(" ", "") != name.lower().replace(" ", "")
                    and part.lower() not in recorded
                ):
                    add("3-orthography:romanisation-variant", "low", f"{name} ~ {part}",
                        f"{t['id']}: the trade's English spells the seed id {part!r}; "
                        "the seed records neither spelling as a label")
        if jn and "（" in jn:
            add("3-orthography:reading-inside-label", "medium", f"{name} {jn}",
                "the reading is written into the label because japanese_name has no "
                "reading field; an exact search for the bare kanji misses it")
        if jn and e.get("unverified_labels") and not e.get("_has_labels"):
            add("3-structure:single-slot-japanese-name", "medium", name,
                f"japanese_name={jn!r} plus unverified_labels={e['unverified_labels']}: "
                "a one-string field forces a second attested string into the unverified list")
        # The ASCII-only alias rule belongs to the pre-labels seed: with labels a
        # sourced Japanese synonym is expected in `aliases`, and each label says
        # which source prints it.
        if (
            not e.get("_has_labels")
            and e.get("aliases")
            and any(not a.isascii() for a in e["aliases"])
        ):
            add("3-structure:non-ascii-alias", "low", name, str(e["aliases"]))
        if name != name.lower():
            add("3-orthography:case", "low", name,
                "mixed-case id (as Kon prints it); a lower-case lookup must fold case")


def check_csv_internal(terms):
    """Reading/romaji and Korean consistency inside the CSV itself."""
    for t in terms:
        ja, rd = t["term_ja"], t["reading"]
        if rd and re.search(r"[A-Za-z]", rd):
            add("3-orthography:reading-not-kana", "low", f"{t['id']} {ja}", f"reading={rd!r}")
        if ja != unicodedata.normalize("NFKC", ja) and "（" not in ja and "）" not in ja:
            add("3-orthography:width-variant-in-term", "low", f"{t['id']} {ja}",
                f"NFKC form {unicodedata.normalize('NFKC', ja)!r}")
    ko_by_ja = defaultdict(set)
    for t in terms:
        for p in re.split(r"\s*[/,]\s*", t["term_ko"]):
            if p.strip():
                ko_by_ja[t["id"]].add(p.strip())
    for tid, kos in ko_by_ja.items():
        normed = {norm_ko(k) for k in kos}
        if len(kos) > 1 and len(normed) < len(kos):
            add("3-orthography:korean-spacing-variant", "low", tid, f"{sorted(kos)}")


def main():
    terms, rels, entities = load()
    check_scattered(terms, rels)
    check_wrong_merges(terms, rels)
    check_seed(terms, rels, entities)
    check_csv_internal(terms)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["check", "severity", "subject", "detail"])
        w.writeheader()
        w.writerows(sorted(ROWS, key=lambda r: (r["check"], r["subject"])))
    by = defaultdict(list)
    for r in ROWS:
        by[r["check"]].append(r)
    for check, rows in sorted(by.items()):
        print(f"\n## {check} ({len(rows)})")
        for r in rows:
            print(f"- [{r['severity']}] {r['subject']}: {r['detail']}")
    print(f"\n{len(ROWS)} findings -> {OUT}")


if __name__ == "__main__":
    main()
