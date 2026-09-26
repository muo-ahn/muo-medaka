"""Do these query strings retrieve anything real?

Two jobs, in order:

1. Preflight Europe PMC with a known-positive control. The API answers an
   unparseable query with hitCount=0, which is indistinguishable from a real
   negative. Several OR-groups of TITLE_ABS:"phrase" AND-ed together is one
   such shape; five queries returned 0 from syntax alone during development.

2. Measure what a set of strings actually retrieves before building a search
   strategy on them. Run with no arguments and it probes every Phenotype name
   in the ontology -- 18 of 30 retrieved zero medaka papers, which is why the
   phenotype rung was not built on phenotype names.

    python .claude/skills/trait-literature-search/scripts/probe_retrieval.py
    python .claude/skills/trait-literature-search/scripts/probe_retrieval.py "enlarged scale" "fin ray"
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
SCOPE = '(medaka OR "Oryzias latipes")'
CONTROL = ('DOI:"10.1093/molbev/msag021"', 1, "Kon et al. 2026")
PAUSE = 0.34          # Europe PMC asks for considerate use; no key required.


def search(query, n=3):
    params = urllib.parse.urlencode({"query": query, "format": "json",
                                     "pageSize": n, "resultType": "lite",
                                     "sort": "CITED desc"})
    with urllib.request.urlopen(f"{URL}?{params}", timeout=45) as r:
        d = json.load(r)
    return d.get("hitCount", 0), [
        (it.get("pubYear"), it.get("title", "")[:70])
        for it in d.get("resultList", {}).get("result", [])]


def phenotype_names():
    names = set()
    for f in ("11-entities-genomic", "12-entities-breeder-traits"):
        p = Path("data/seed") / f"{f}.yaml"
        for e in yaml.safe_load(p.read_text("utf-8"))["entities"]:
            if e.get("label") == "Phenotype":
                names.add(e["name"])
    return sorted(names)


def main(argv):
    query, expected, label = CONTROL
    got, _ = search(query)
    print(f"control: {label} -> hitCount={got} (expect {expected})")
    if got != expected:
        print("\n  BACKEND NOT TRUSTWORTHY. Do not read 0 as 'no literature'.")
        return 1
    print()

    terms = argv or phenotype_names()
    dead = []
    for term in terms:
        try:
            n, top = search(f'{SCOPE} AND "{term}"')
        except Exception as exc:                      # noqa: BLE001
            print(f"  ERR  {term}: {exc}")
            continue
        print(f"  {n:>6}  {term}{'   <-- retrieves nothing' if not n else ''}")
        if 0 < n <= 5:
            for year, title in top[:2]:
                print(f"            ({year}) {title}")
        if not n:
            dead.append(term)
        time.sleep(PAUSE)

    print(f"\n  {len(dead)}/{len(terms)} strings retrieve zero medaka papers")
    if dead:
        print("  A search strategy built on these will look like a negative "
              "result and is not one.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
