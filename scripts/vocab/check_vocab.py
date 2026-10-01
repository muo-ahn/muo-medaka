# -*- coding: utf-8 -*-
"""Self-check for the breeder vocabulary outputs (AC-1..AC-5, AC-7 structure).
Usage: python check_vocab.py [REPO_ROOT]   -> exit 1 on any failure."""
import csv, os, re, sys, collections
import yaml

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(HERE))
D = os.path.join(REPO, "docs", "research")
TERMS = os.path.join(D, "breeder-vocabulary-2026-09.csv")
RELS = os.path.join(D, "breeder-vocabulary-relations-2026-09.csv")
DOC = os.path.join(D, "breeder-vocabulary-2026-09.md")
KINDS = {"TRAIT", "STRAIN", "MODIFIER", "JARGON"}
AXES = {"BODY_COLOR", "LUSTER", "PATTERN", "SCALE", "FIN", "BODY_SHAPE", "EYE", "OTHER"}
RELSET = {"same_as", "variant_spelling", "broader", "narrower", "composed_of", "collides_with", "seed_match"}
fails = []


def check(name, bad, total):
    ok = not bad
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {total - len(bad)}/{total}" + ("" if ok else f"  e.g. {bad[:3]}"))
    if not ok:
        fails.append(name)


T = list(csv.DictReader(open(TERMS, encoding="utf-8-sig")))
R = list(csv.DictReader(open(RELS, encoding="utf-8-sig")))
ids = {t["id"] for t in T}
seed = []
for f in ["10-entities-traits.yaml", "12-entities-breeder-traits.yaml"]:
    d = yaml.safe_load(open(os.path.join(REPO, "data", "seed", f), encoding="utf-8"))
    seed += [e["name"] for e in d["entities"] if e["label"] == "OrnamentalTrait"]

print(f"terms={len(T)} relations={len(R)} seed_traits={len(seed)}")
check("ids unique", [i for i, c in collections.Counter(t["id"] for t in T).items() if c > 1], len(T))
check("AC-1 term has >=1 source URL",
      [t["id"] for t in T if not re.search(r"https?://", t["source_urls"])], len(T))
check("AC-1 term has access date",
      [t["id"] for t in T if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \| \d{4}-\d{2}-\d{2})*", t["accessed"])], len(T))
check("AC-1 no-URL spelling marked unverified (term_ja 없음 rows)",
      [t["id"] for t in T if not t["term_ja"] and "term_ja 없음" not in t["unverified"]], len(T))
check("AC-2 kind in closed set", [t["id"] for t in T if t["kind"] not in KINDS], len(T))
check("AC-2 axis in closed set", [t["id"] for t in T if t["axis"] not in AXES], len(T))
check("AC-3 relation in closed set", [r["relation"] for r in R if r["relation"] not in RELSET], len(R))


def basis_ok(b):
    """source:/inferred: carry the evidence. The 2026-10 second pass adds two
    annotations that may ride along but never stand alone: revised: (which
    ruling changed the edge) and disputed: (sources disagree on it)."""
    parts = [p.strip() for p in b.split(" | ")]
    evidence = [p for p in parts if re.match(r"source:https?://\S+", p) or re.match(r"inferred:\S", p)]
    notes = [p for p in parts if re.match(r"(revised|disputed):\S", p)]
    return bool(evidence) and len(evidence) + len(notes) == len(parts)


check("AC-3 basis non-empty and source:/inferred:", [r["subject_id"] for r in R if not basis_ok(r["basis"])], len(R))
collide = {frozenset((r["subject_id"], r["object_id"])) for r in R if r["relation"] == "collides_with"}
check("2nd pass: a same_as on a colliding pair is marked disputed:",
      [f'{r["subject_id"]}~{r["object_id"]}' for r in R if r["relation"] == "same_as"
       and frozenset((r["subject_id"], r["object_id"])) in collide and "disputed:" not in r["basis"]], len(R))
check("AC-3 subject_id exists", [r["subject_id"] for r in R if r["subject_id"] not in ids], len(R))
check("AC-3 object_id exists / seed / blank",
      [r["object_id"] for r in R if r["object_id"] and r["object_id"] not in ids
       and not (r["object_id"].startswith("seed:") and r["object_id"][5:] in seed)], len(R))
unres = sum(1 for r in R if not r["object_id"])
print(f"       (unresolved object, label only: {unres} rows; relation types: "
      f"{dict(collections.Counter(r['relation'] for r in R))})")

doc = open(DOC, encoding="utf-8").read()
m = re.search(r"^## seed 대응표.*?(?=^## )", doc, re.S | re.M)
sec = m.group(0) if m else ""
rows = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| seed trait")]
names = [l.split("|")[1].strip().strip("`") for l in rows]
check("AC-4 every seed trait in coverage table", [s for s in seed if s not in names], len(seed))
status_ok = []
for s in seed:
    line = next((l for l in rows if l.split("|")[1].strip().strip("`") == s), "")
    has_rel = any(r["object_id"] == "seed:" + s for r in R)
    if not (has_rel or "lab only" in line or "no match found" in line):
        status_ok.append(s)
check("AC-4 each seed trait has a relation, 'lab only' or 'no match found'", status_ok, len(seed))
m5 = re.search(r"^## 이름 충돌.*?(?=^## )", doc, re.S | re.M)
coll = [l for l in (m5.group(0) if m5 else "").splitlines() if re.match(r"\| \d+ \|", l)]
check("AC-5 collision table present (>=8 rows)", [] if len(coll) >= 8 else ["rows=%d" % len(coll)], 1)
print(f"       (collision table rows: {len(coll)}; collides_with relations: "
      f"{sum(1 for r in R if r['relation'] == 'collides_with')})")
check("AC-7 saturation + stop-criterion section", [] if re.search(r"^## 포화 관찰과 종료 기준", doc, re.M) else ["missing"], 1)
m6 = re.search(r"^## 출처 검증 \(AC-6\).*?(?=^## )", doc, re.S | re.M)
sec6 = m6.group(0) if m6 else ""
check("AC-6 results recorded (sample seed + mismatch rate)",
      [] if ("random.seed(20260928)" in sec6 and "불일치율" in sec6 and "검증 대기" not in sec6) else ["missing"], 1)
flag = next((t for t in T if t["term_ja"] == "上物"), None)
check("AC-6 correction: 上物 flagged unverified", [] if flag and "출처 본문에 표기 없음" in flag["unverified"] else ["bv:0277"], 1)
print("RESULT:", "ALL PASS" if not fails else "FAIL " + ", ".join(fails))
sys.exit(1 if fails else 0)
