"""Does the anatomy rung recover the answers we already know, and under which
organism scope?

Retrieval is not the test. `probe_retrieval.py` answers "does this string find
anything"; this answers "does it find the RIGHT paper", which is the only
question that decides whether a rung is worth building.

Two things it measures, both of which changed the design (2026-09-26):

1. The denominator. Ten traits have their gene from `kon2026` alone. That GWAS
   is already in the repo and its title carries no anatomy noun, so no anatomy
   query can recover it, and counting those as failures measures nothing. The
   honest denominator is the 14 traits whose gene is named by some OTHER paper
   -- the traits this rung exists for.

2. The scope. Tight and wide recover different traits: the misses under
   `TITLE:(medaka)` are zebrafish papers that scope excludes by construction.
   That is why the rung emits both. Re-measured 2026-09-26 after dropping the
   "oculocutaneous" alias for slc45a2, which had been matching oca2 abstracts:
   pipeline tight 8, wide 7, union 9 of 14; probe tight 8, wide 9, union 10.

    python .claude/skills/trait-literature-search/scripts/anatomy_recall.py
    python .claude/skills/trait-literature-search/scripts/anatomy_recall.py --as-pipeline

`--as-pipeline` measures what `discovery.run_queries` actually sees -- 25 results
in Europe PMC's relevance order -- rather than the 50 citation-sorted results a
hand probe defaults to. Those are different questions and they got different
answers, so the flag exists to stop the convenient one being quoted for the real
one.
"""

from __future__ import annotations

import collections
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from converge import GeneGraph, load_seed  # noqa: E402

from medaka_ontology.vocabulary import NodeLabel, Predicate  # noqa: E402

URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CONTROL = ('DOI:"10.1093/molbev/msag021"', 1)
PAUSE = 0.34
PAGE = 50

#: The seed paper this repo is built on. A trait whose gene comes only from here
#: is not evidence about the rung either way.
OWN_GWAS = "kon2026"

SCOPES = {
    "tight (TITLE:medaka)": 'TITLE:(medaka) AND TITLE:("{t}")',
    "wide  (teleost)": 'TITLE:("{t}") AND (medaka OR zebrafish OR "Oryzias latipes"'
                       ' OR "Danio rerio" OR teleost OR fish)',
}


def anatomy_terms(bundle):
    """phenotype -> the query terms the graph reaches for it.

    Derived from the affects_anatomy claims and each Anatomy node's
    query_terms, the same path the discovery rung takes, rather than kept as a
    hand copy. The hand copy drifted: it gave hypomelanism and orange spotting
    pigment-cell terms that the seed deliberately withholds (SKILL.md, "Two
    phenotypes deliberately have no anatomy edge").
    """
    anatomy = {e.name: e for e in bundle.entities if e.label is NodeLabel.ANATOMY}
    out = collections.defaultdict(set)
    for claim in bundle.claims:
        if claim.predicate is not Predicate.AFFECTS_ANATOMY:
            continue
        part = anatomy.get(claim.object.name)
        if part is not None:
            out[claim.subject.name] |= set(part.query_terms or [part.name])
    return out


#: Papers name a gene by more than its symbol, and a missed alias reads as a
#: failed rung.
ALIAS = {
    "kitlga": ["kit ligand", "kitlg"],
    # Not "oculocutaneous": that word also matches every oca2 abstract, and oca2
    # is albino's gene, not yellow's. It credited slc45a2 with oca2 papers.
    "slc45a2": ["b locus"],
    "tyr": ["tyrosinase"],
    "and2": ["actinodin"],
    "oca2": ["oculocutaneous albinism"],
    "zic1": ["zic"],
    "zic4": ["zic"],
    "pnp4a": ["purine nucleoside phosphorylase"],
    "kcnq5a": ["kcnq"],
    "kcna10": ["kcna"],
    "kcna3": ["kcna"],
    "kcnd3": ["kcnd"],
    "abcb6a": ["abcb6"],
    "atp6ap2": ["prorenin receptor"],
    "chn1": ["chimerin"],
}


def search(query, n=PAGE, sort="CITED desc"):
    fields = {"query": query, "format": "json", "pageSize": n, "resultType": "core"}
    if sort:
        fields["sort"] = sort
    params = urllib.parse.urlencode(fields)
    with urllib.request.urlopen(f"{URL}?{params}", timeout=60) as response:
        data = json.load(response)
    blobs = [
        f"{item.get('title') or ''} {item.get('abstractText') or ''}".lower()
        for item in data.get("resultList", {}).get("result", [])
    ]
    return data.get("hitCount", 0), blobs


def finds(blobs, gene):
    patterns = [re.compile(rf"\b{re.escape(w)}\b")
                for w in [gene.lower(), *ALIAS.get(gene.lower(), [])]]
    for index, blob in enumerate(blobs, 1):
        if any(p.search(blob) for p in patterns):
            return index
    return None


def externally_named(bundle):
    """trait -> papers other than the seed GWAS that name its gene."""
    out = collections.defaultdict(set)
    for claim in bundle.claims:
        if claim.predicate is not Predicate.ASSOCIATED_WITH_GENE:
            continue
        for evidence in claim.evidence:
            if evidence.paper != OWN_GWAS:
                out[claim.subject.name].add(evidence.paper)
    return out


def main(argv):
    as_pipeline = "--as-pipeline" in argv
    page = 25 if as_pipeline else PAGE
    sort = None if as_pipeline else "CITED desc"
    mode = ("pipeline (pageSize 25, relevance order)" if as_pipeline
            else "probe (pageSize 50, citation order)")
    print(f"mode: {mode}")

    query, expected = CONTROL
    got, _ = search(query, n=1)
    print(f"control -> hitCount={got} (expect {expected})")
    if got != expected:
        print("\n  BACKEND NOT TRUSTWORTHY. Do not read 0 as 'no literature'.")
        return 1

    bundle = load_seed()
    graph = GeneGraph(bundle)
    pheno_of, genes_of = graph.phenotypes, graph.gene_claims
    anatomy = anatomy_terms(bundle)
    external = externally_named(bundle)
    targets = sorted(t for t in external if pheno_of.get(t) and genes_of.get(t))
    print(f"\n{len(targets)} traits whose gene is named outside {OWN_GWAS}\n")

    cache = {}
    recovered = collections.defaultdict(set)
    for label, template in SCOPES.items():
        print(f"=== scope: {label}")
        for trait in targets:
            terms = sorted({t for p in pheno_of[trait] for t in anatomy.get(p, ())})
            best, pool = None, 0
            for term in terms:
                query = template.format(t=term)
                if query not in cache:
                    cache[query] = search(query, n=page, sort=sort)
                    time.sleep(PAUSE)
                hits, blobs = cache[query]
                pool = max(pool, hits)
                for gene in genes_of[trait]:
                    rank = finds(blobs, gene)
                    if rank and (best is None or rank < best[0]):
                        best = (rank, gene, term, hits)
            if best:
                recovered[label].add(trait)
                rank, gene, term, hits = best
                print(f"  {trait:<16} OK   {gene} at rank {rank}/{min(hits, page)}"
                      f' via "{term}" ({hits} hits)')
            else:
                papers = ",".join(sorted(external[trait]))
                print(f"  {trait:<16} --   not recovered "
                      f"(best pool {pool} hits; {papers})")
        print(f"  -> {len(recovered[label])}/{len(targets)}\n")

    union = set().union(*recovered.values())
    print(f"union of scopes: {len(union)}/{len(targets)}")
    for label, traits in recovered.items():
        others = set().union(*(v for k, v in recovered.items() if k != label))
        unique = sorted(traits - others)
        print(f"  only {label}: {', '.join(unique) or '-'}")
    missed = sorted(set(targets) - union)
    print(f"  reached by neither: {', '.join(missed) or '-'}")
    print("\n  A rung built on one scope throws away the traits the other one "
          "reaches. That is why the ladder emits both.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
