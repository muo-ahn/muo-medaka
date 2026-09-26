"""Turn the existing ontology into literature queries, and run them.

Issue #1 §1. The point of driving discovery from the graph rather than from a
fixed string like `medaka ornamental genetics` is reach: the papers that settle
a trait's genetics are frequently not ornamental-medaka papers at all. The Da
lesion was identified in developmental-biology work about dorsoventral
patterning; the reason anyone looks at potassium channels for fin length is a
zebrafish paper. Those are reachable only by expanding through the genes and
mechanisms the graph already holds.

So each trait yields a ladder of queries:

    trait name and aliases
      -> the laboratory mutants it is putatively identified with
        -> the genes those claims point at
          -> the mechanisms those genes participate in

    trait name
      -> the phenotypes it has
        -> the anatomy those phenotypes affect

The second ladder exists because the first one dead-ends on precisely the traits
that need discovering: a trait with no candidate gene yields only the trait rung,
and the trait rung searches this ontology's own vocabulary. Anatomy is the one
vocabulary the literature shares with us.

Each query records which entity and which rung produced it, so a paper's
`discovered_via` says why it was ever looked at.
"""

from __future__ import annotations

import html
import re
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from neo4j import Session

from .lexicon import AMBIGUOUS_SURFACE_FORMS

EUROPE_PMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

#: Europe PMC asks for considerate use and does not require a key. One request
#: at a time with a pause between them is well inside that.
REQUEST_INTERVAL_SECONDS = 0.34

#: Every query is scoped to the organism except the mechanism rung, which is
#: deliberately cross-species -- that rung exists to find the comparative work.
MEDAKA_SCOPE = '(medaka OR "Oryzias latipes")'

#: The anatomy rung's wide scope. Deliberately cross-species: half the papers
#: that name a medaka trait's causal gene are zebrafish papers, and `TITLE:
#: (medaka)` excludes those by construction.
FISH_SCOPE = (
    '(medaka OR zebrafish OR "Oryzias latipes" OR "Danio rerio" OR teleost OR fish)'
)

#: Shorter than this and a term retrieves noise whatever it is.
MIN_QUERY_TERM_LENGTH = 4

#: The anatomy rung's own floor, three rather than four. `fin` and `eye` are the
#: two most productive terms the rung has and both are three characters; a
#: four-character floor would silently delete them. See `_is_anatomy_searchable`
#: for why the anatomy rung can afford a term the other rungs cannot.
MIN_ANATOMY_TERM_LENGTH = 3

#: Europe PMC field prefix restricting a term to title and abstract. Applied
#: to the trait rung only; the gene and mechanism rungs deliberately search
#: full text, because a gene named only in a Results section is exactly the
#: finding those rungs exist to reach.
TITLE_ABS = "TITLE_ABS"

#: Title only. The anatomy rung uses this rather than TITLE_ABS: `fin` in an
#: abstract means nothing, `fin` in a title means the paper is about fins.
TITLE = "TITLE"


class DiscoveryTier(str):
    """Which rung of the expansion produced a query. Recorded as provenance."""

    TRAIT = "trait"
    MUTANT = "mutant"
    GENE = "gene"
    MECHANISM = "mechanism"
    ANATOMY = "anatomy"
    #: The same terms as ANATOMY, searched against every teleost rather than
    #: medaka alone. A separate tier string so `discovered_via` still says which
    #: of the two shapes found a paper -- they recover different papers.
    ANATOMY_WIDE = "anatomy-wide"


@dataclass(frozen=True)
class QuerySpec:
    """One literature query, with the reason it exists."""

    query: str
    tier: str
    origin_entity_id: str
    origin_entity_name: str

    @property
    def key(self) -> str:
        return f"{self.tier}:{self.origin_entity_id}"


@dataclass
class DiscoveredPaper:
    """A search hit, before anything has been decided about it."""

    title: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    year: int | None = None
    journal: str | None = None
    is_open_access: bool = False
    has_fulltext_xml: bool = False
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    discovered_via: str = ""
    discovery_tier: str = ""

    @property
    def identifier(self) -> str | None:
        return self.doi or self.pmid or self.pmcid


_EXPANSION_QUERY = """
MATCH (t:OrnamentalTrait {id: $id})
OPTIONAL MATCH (same:Claim {predicate: 'putatively_same_as'})--(t)
OPTIONAL MATCH (same)--(mutant:OrnamentalTrait) WHERE mutant <> t
OPTIONAL MATCH (gc:Claim)-[:SUBJECT]->(t)
OPTIONAL MATCH (gc)-[:OBJECT]->(g:Gene)
  WHERE gc.predicate IN ['associated_with_gene', 'caused_by_variant', 'modified_by']
  AND EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(gc) }
OPTIONAL MATCH (mc:Claim {predicate: 'participates_in'})-[:SUBJECT]->(g)
OPTIONAL MATCH (mc)-[:OBJECT]->(mech:BiologicalMechanism)
OPTIONAL MATCH (pc:Claim {predicate: 'has_phenotype'})-[:SUBJECT]->(t)
OPTIONAL MATCH (pc)-[:OBJECT]->(p:Phenotype)
  WHERE EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(pc) }
OPTIONAL MATCH (ac:Claim {predicate: 'affects_anatomy'})-[:SUBJECT]->(p)
OPTIONAL MATCH (ac)-[:OBJECT]->(a:Anatomy)
  WHERE EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(ac) }
RETURN t.name AS trait,
       coalesce(t.aliases, []) AS aliases,
       collect(DISTINCT mutant.name) AS mutants,
       collect(DISTINCT [m IN coalesce(mutant.aliases, []) | m]) AS mutant_aliases,
       collect(DISTINCT g.name) AS genes,
       collect(DISTINCT mech.name) AS mechanisms,
       collect(DISTINCT [a.name, coalesce(a.query_terms, [])]) AS anatomy
"""

_ALL_TRAITS = "MATCH (t:OrnamentalTrait) RETURN t.id AS id, t.name AS name ORDER BY t.name"


def _quote(term: str) -> str:
    return f'"{term}"' if " " in term else term


def _is_searchable(term: str) -> bool:
    """Whether a term is specific enough to retrieve on.

    A bad surface form in the *matcher* costs one false candidate. A bad one in
    the *query* costs a whole page of irrelevant papers that then get fetched,
    mined and registered. The Da mutant is the case that taught this: its alias
    `Da` is two characters, so `(medaka) AND (Da OR ...)` retrieves essentially
    every medaka paper ever published - toxicology, sperm motility, liver
    disease - because `da` occurs somewhere in all of them.

    But this is *not* the same test the lexicon applies. "dorsoventral
    patterning" is a poor thing to match in free text, where it is too generic
    to identify anything, and an excellent thing to search on, where it is
    precise. So only single-word generics and short tokens are dropped;
    multi-word scientific phrases are kept, which is what preserves the
    mechanism rung - the one rung that reaches outside the ornamental-medaka
    literature, and the reason this module exists.
    """
    stripped = term.strip()
    if len(stripped) < MIN_QUERY_TERM_LENGTH:
        return False
    if " " in stripped:
        return True
    return stripped.lower() not in AMBIGUOUS_SURFACE_FORMS


def _is_anatomy_searchable(term: str) -> bool:
    """The same test as `_is_searchable`, relaxed for the anatomy rung only.

    `eye`, `fin` and `scale` are the rung's three most productive terms and all
    three fail `_is_searchable`: `fin` and `eye` are below MIN_QUERY_TERM_LENGTH,
    and `scale` and `iris` are in AMBIGUOUS_SURFACE_FORMS. Passing anatomy
    through the general filter therefore deletes the rung, not the noise.

    Loosening the general filter instead is not an option -- it exists because
    the two-character alias `Da`, AND-ed against a full-text medaka scope, once
    retrieved every medaka paper ever published. What makes the anatomy rung
    safe with the same term is the *shape* of its queries, not the term: both
    are restricted to TITLE, and a word in a title is what the paper is about.
    `TITLE:"fin"` cannot behave like full-text `Da`. So the relaxation is scoped
    to this one rung and a three-character floor is still enforced, because a
    one- or two-character anatomy term would be a data error either way.
    """
    stripped = term.strip()
    if len(stripped) < MIN_ANATOMY_TERM_LENGTH:
        return False
    return any(ch.isalpha() for ch in stripped)


def _searchable(terms: Sequence[str]) -> list[str]:
    return [t for t in terms if t and _is_searchable(t)]


def _searchable_anatomy(terms: Sequence[str]) -> list[str]:
    return [t for t in terms if t and _is_anatomy_searchable(t)]


def _or_group(terms: Sequence[str], field: str | None = None, quote_all: bool = False) -> str:
    prefix = f"{field}:" if field else ""
    quote = (lambda t: f'"{t}"') if quote_all else _quote
    return " OR ".join(f"{prefix}{quote(t)}" for t in sorted(set(terms)) if t)


def expansion_terms(session: Session, trait_id: str) -> dict[str, list[str]]:
    """The terms reachable from one trait, grouped by expansion rung."""
    record = session.run(_EXPANSION_QUERY, id=trait_id).single()
    if record is None:
        return {}
    mutant_aliases = [a for group in record["mutant_aliases"] for a in group if a]
    # `query_terms` is what to search on and is often coarser than the node's
    # own name: the `dorsal fin` node searches as `fin`, because a paper about
    # dorsal fins rarely says so in its title. The fallback to `a.name` is here
    # rather than in the Cypher so the rung degrades to names on a graph where
    # the property has not been backfilled yet.
    anatomy = [
        term
        for name, query_terms in record["anatomy"]
        for term in ([t for t in (query_terms or []) if t] or ([name] if name else []))
    ]
    return {
        DiscoveryTier.TRAIT: [record["trait"], *record["aliases"]],
        DiscoveryTier.MUTANT: [*[m for m in record["mutants"] if m], *mutant_aliases],
        DiscoveryTier.GENE: [g for g in record["genes"] if g],
        DiscoveryTier.MECHANISM: [m for m in record["mechanisms"] if m],
        DiscoveryTier.ANATOMY: anatomy,
    }


def queries_for_trait(
    session: Session, trait_id: str, trait_name: str
) -> list[QuerySpec]:
    """Build the query ladder for one trait.

    A rung is skipped when it has no terms, so a trait with no candidate gene
    produces only the trait-level query rather than a malformed one.
    """
    terms = expansion_terms(session, trait_id)
    if not terms:
        return []

    specs: list[QuerySpec] = []

    trait_terms = _searchable(terms[DiscoveryTier.TRAIT] + terms[DiscoveryTier.MUTANT])
    if trait_terms:
        # Restricted to title and abstract, unlike the rungs below.
        #
        # Europe PMC searches full text by default, and a trait name appearing
        # anywhere in a paper is a weak signal in this corpus for one specific
        # reason: `hikari` is a major aquarium fish-food brand. Unrestricted, the
        # hikari query returns neurotoxicology and sperm-motility papers that
        # merely list what they fed the fish. Scoped to title and abstract it
        # returns the zic1/zic4 literature and nothing else, because a trait name
        # in the abstract means the paper is about the trait.
        specs.append(
            QuerySpec(
                query=f"{MEDAKA_SCOPE} AND ({_or_group(trait_terms, field=TITLE_ABS)})",
                tier=DiscoveryTier.TRAIT,
                origin_entity_id=trait_id,
                origin_entity_name=trait_name,
            )
        )

    genes = _searchable(terms[DiscoveryTier.GENE])
    if genes:
        specs.append(
            QuerySpec(
                query=f"{MEDAKA_SCOPE} AND ({_or_group(genes)})",
                tier=DiscoveryTier.GENE,
                origin_entity_id=trait_id,
                origin_entity_name=trait_name,
            )
        )
        mechanisms = _searchable(terms[DiscoveryTier.MECHANISM])
        if mechanisms:
            # Intentionally unscoped by organism. This is the rung that reaches
            # the zebrafish and mouse work a trait's mechanism rests on, and
            # scoping it to medaka would defeat its only purpose.
            specs.append(
                QuerySpec(
                    query=f"({_or_group(genes)}) AND ({_or_group(mechanisms)})",
                    tier=DiscoveryTier.MECHANISM,
                    origin_entity_id=trait_id,
                    origin_entity_name=trait_name,
                )
            )

    anatomy = _searchable_anatomy(terms[DiscoveryTier.ANATOMY])
    if anatomy:
        # Two scopes, both required. Measured 2026-09-26 by
        # `.claude/skills/trait-literature-search/scripts/anatomy_recall.py
        # --as-pipeline`, which reproduces exactly what `run_queries` sees --
        # pageSize 25 and no `sort` parameter, so Europe PMC relevance order --
        # against the 14 traits whose causal gene is named by a paper OTHER than
        # kon2026, using the same anatomy term map this rung reads:
        #
        #   tight  8/14   only tight: daruma, fused centrum
        #   wide   8/14   only wide:  reallongfin, yellow
        #   union 10/14
        #
        # Tight goes first because it is precise and nearly free: pools of 1-27
        # hits with the correct paper at rank 1-7. Wide is here because it is
        # the only thing that reaches the comparative literature -- reallongfin
        # and yellow are recovered by wide alone and both of their papers are
        # zebrafish papers that `TITLE:(medaka)` excludes by construction. The
        # two overlap heavily but neither subsumes the other, so dropping either
        # costs two traits.
        #
        # black, hirenaga, orochi and sanshoku are reached by neither: yang2018
        # is mammalian and tatarakis2021 is a single-cell atlas that never names
        # the gene in its title or abstract. That is this rung's ceiling, not a
        # bug in it.
        #
        # Do not add a `sort` parameter. Wide's pool reaches 1288 hits for `fin`,
        # so this rung does lean on the ordering -- but the same script run with
        # a citation sort scores 10/14 wide and 11/14 union, one trait better
        # (orochi, at rank 25), while ranking several results markedly worse:
        # yellow 4th under relevance against 33rd under citations, reallongfin
        # 10th against 40th, albino 2nd against 12th. A 1288-hit pool sorted by
        # citation count puts famous papers first, not relevant ones. Sorting is
        # the backend's business and would move every other rung too, for a
        # measured gain of one trait.
        titles = _or_group(anatomy, field=TITLE, quote_all=True)
        specs.append(
            QuerySpec(
                query=f"TITLE:(medaka) AND ({titles})",
                tier=DiscoveryTier.ANATOMY,
                origin_entity_id=trait_id,
                origin_entity_name=trait_name,
            )
        )
        specs.append(
            QuerySpec(
                query=f"({titles}) AND {FISH_SCOPE}",
                tier=DiscoveryTier.ANATOMY_WIDE,
                origin_entity_id=trait_id,
                origin_entity_name=trait_name,
            )
        )
    return specs


def all_queries(session: Session, limit_traits: int | None = None) -> list[QuerySpec]:
    traits = [dict(r) for r in session.run(_ALL_TRAITS)]
    if limit_traits:
        traits = traits[:limit_traits]
    specs: list[QuerySpec] = []
    for trait in traits:
        specs.extend(queries_for_trait(session, trait["id"], trait["name"]))
    return specs


class SearchBackend(Protocol):
    """Anything that can answer a literature query.

    A protocol so the pipeline can be exercised offline against a recorded
    fixture; the tests would otherwise depend on a third-party service being up
    and on its result set never changing.
    """

    def search(self, query: str, page_size: int) -> list[dict[str, Any]]: ...


class EuropePmcBackend:
    """Europe PMC REST search.

    Chosen over PubMed E-utilities because a single response carries the open
    access flag and full-text availability alongside the metadata, so deciding
    whether a paper is retrievable costs no extra request.
    """

    def __init__(self, client: httpx.Client | None = None, interval: float | None = None):
        self._client = client or httpx.Client(timeout=30.0)
        self._interval = REQUEST_INTERVAL_SECONDS if interval is None else interval
        self._last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request = time.monotonic()

    def search(self, query: str, page_size: int = 25) -> list[dict[str, Any]]:
        self._throttle()
        response = self._client.get(
            EUROPE_PMC_SEARCH,
            params={
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": page_size,
            },
        )
        response.raise_for_status()
        return response.json().get("resultList", {}).get("result", [])

    def close(self) -> None:
        self._client.close()


def _clean(value: Any) -> str:
    """Unescape HTML entities and strip inline tags."""
    if not value:
        return ""
    unescaped = html.unescape(str(value))
    return " ".join(re.sub(r"<[^>]+>", " ", unescaped).split())


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_result(raw: dict[str, Any], spec: QuerySpec) -> DiscoveredPaper:
    full_text_list = raw.get("fullTextIdList") or {}
    text_types = {
        t.get("availabilityCode") for t in (raw.get("fullTextUrlList") or {}).get(
            "fullTextUrl", []
        )
    }
    # Europe PMC returns titles and abstracts with entity-escaped inline markup
    # ("&lt;i&gt;Oryzias&lt;/i&gt;"). Left as-is it reaches the review queue and
    # the run report verbatim, and breaks word-boundary matching on any term
    # that was italicised - which for this corpus means the species and gene
    # names, the two things worth matching.
    return DiscoveredPaper(
        title=_clean(raw.get("title")).rstrip("."),
        doi=raw.get("doi"),
        pmid=raw.get("pmid"),
        pmcid=raw.get("pmcid"),
        year=_as_int(raw.get("pubYear")),
        journal=(raw.get("journalInfo") or {}).get("journal", {}).get("title"),
        is_open_access=raw.get("isOpenAccess") == "Y" or "OA" in text_types,
        # hasTextMinedTerms is not the same thing, so only the explicit flag and
        # a PMCID are trusted here; acquisition re-checks before it commits.
        has_fulltext_xml=raw.get("inEPMC") == "Y" or bool(full_text_list),
        authors=[
            a.get("fullName", "")
            for a in (raw.get("authorList") or {}).get("author", [])
            if a.get("fullName")
        ],
        abstract=_clean(raw.get("abstractText")) or None,
        discovered_via=spec.key,
        discovery_tier=spec.tier,
    )


def run_queries(
    backend: SearchBackend,
    specs: Sequence[QuerySpec],
    page_size: int = 25,
) -> Iterator[DiscoveredPaper]:
    """Execute each query, yielding parsed hits.

    Deduplication is not done here. A paper found by three different traits is
    three separate pieces of evidence about why it is relevant, and the registry
    merges them while keeping every `discovered_via`.
    """
    for spec in specs:
        for raw in backend.search(spec.query, page_size=page_size):
            paper = parse_result(raw, spec)
            if paper.identifier:
                yield paper
