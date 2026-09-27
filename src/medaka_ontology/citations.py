"""Find papers by following Europe PMC citations from papers the seed cites.

The keyword ladder in `discovery.py` finds a paper only if it uses the words the
ontology already has. A citation link finds it because it engages with a paper
someone already read. Measured 2026-09 (`docs/research/enrich-yield-2026-09.md`):
3 seeds, 106 unique citers, 4 that add or change a claim, 9 HTTP calls.

This module only decides *which papers*. What happens to them afterwards --
registration as DISCOVERED, full-text acquisition, co-mention extraction -- is
the existing pipeline, unchanged, and nothing here becomes a claim (ADR 0002).

The screen, in order, with a count after each step:

    raw           every link row for every seed and direction
    deduped       one row per paper: by PMID, then by normalised title,
                  a published (MED) record preferred over its preprint (PPR)
    not yet known not in the seed (PMID or DOI), not already in the registry
    medaka        title OR abstract names medaka or Oryzias

The last step reads the abstract, not just the title. A medaka paper does not
always say so in its title (kawanishi2013 is titled "the teleost trunk"), and
the abstract costs nothing extra: it arrives in the same batched `core` search
that supplies the DOI and PMCID.

Needs no Neo4j. The pipeline passes in what the registry already holds; the dry
run passes only the seed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from .discovery import DiscoveredPaper, DiscoveryTier, QuerySpec, _as_int, _clean, parse_result

DIRECTIONS = ("forward", "backward")

#: IDs per batched abstract search. The measurement used 20 and it held.
ABSTRACT_BATCH_SIZE = 20

#: Bounded on the left only, so `medakas` and `Oryzias latipes` both match and
#: nothing matches inside an unrelated word.
_MEDAKA = re.compile(r"\b(medaka|oryzias)", re.IGNORECASE)

#: A preprint and the published article are one paper. MED sorts first.
_SOURCE_RANK = {"MED": 0, "PMC": 1}


class CitationBackend(Protocol):
    """Link lookups plus the ordinary search, which fetches abstracts."""

    def links(self, pmid: str, direction: str) -> list[dict[str, Any]]: ...

    def search(self, query: str, page_size: int) -> list[dict[str, Any]]: ...


@dataclass
class ScreenedPaper:
    """One unique paper that survived the screen, with every route to it."""

    paper: DiscoveredPaper
    routes: list[str] = field(default_factory=list)

    def discovered(self) -> list[DiscoveredPaper]:
        """One record per route. The registry merges them onto one node and
        keeps every `discovered_via`, exactly as it does for a paper two keyword
        queries both found."""
        return [
            replace(self.paper, discovered_via=route, discovery_tier=DiscoveryTier.CITATION)
            for route in self.routes
        ]


@dataclass
class CitationScreen:
    """Counts after each filter step, and what was kept."""

    seeds: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)
    raw: int = 0
    deduped: int = 0
    not_yet_known: int = 0
    medaka: int = 0
    no_abstract: int = 0
    kept: list[ScreenedPaper] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "raw": self.raw,
            "deduped": self.deduped,
            "not_yet_known": self.not_yet_known,
            "medaka": self.medaka,
            "no_abstract": self.no_abstract,
        }

    def discovered(self, limit: int | None = None) -> list[DiscoveredPaper]:
        kept = self.kept[:limit] if limit else self.kept
        return [record for item in kept for record in item.discovered()]


def normalise_title(title: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", _clean(title).lower()).split())


def mentions_medaka(title: str | None, abstract: str | None) -> bool:
    return bool(_MEDAKA.search(f"{title or ''} {abstract or ''}"))


def route_for(direction: str, seed_pmid: str) -> str:
    """`discovered_via` for a citation find: `citation:forward:24803434`."""
    return _spec(direction, seed_pmid).key


def _spec(direction: str, seed_pmid: str) -> QuerySpec:
    return QuerySpec(
        query="",
        tier=DiscoveryTier.CITATION,
        origin_entity_id=f"{direction}:{seed_pmid}",
        origin_entity_name=seed_pmid,
    )


@dataclass
class _Row:
    source: str
    id: str
    title: str
    year: int | None
    #: (direction, seed pmid) for every link that reached this paper.
    routes: list[tuple[str, str]]

    @property
    def pmid(self) -> str | None:
        return self.id if self.source == "MED" else None


def seed_identifiers(seed_dir: Path | None = None) -> tuple[list[str], set[str], set[str]]:
    """The seed's PMIDs (the default seeds), and every PMID and DOI it holds."""
    from .loader import load_dir

    bundle = load_dir(seed_dir) if seed_dir else load_dir()
    pmids = [p.pmid for p in bundle.papers if p.pmid]
    dois = {p.doi.lower() for p in bundle.papers if p.doi}
    return pmids, set(pmids), dois


def _dedupe(rows: Sequence[_Row]) -> list[_Row]:
    ordered = sorted(rows, key=lambda r: _SOURCE_RANK.get(r.source, 9))
    by_id: dict[tuple[str, str], _Row] = {}
    by_title: dict[str, _Row] = {}
    unique: list[_Row] = []
    for row in ordered:
        title_key = normalise_title(row.title)
        keeper = by_id.get((row.source, row.id)) or (by_title.get(title_key) if title_key else None)
        if keeper is not None:
            keeper.routes.extend(r for r in row.routes if r not in keeper.routes)
            continue
        by_id[(row.source, row.id)] = row
        if title_key:
            by_title[title_key] = row
        unique.append(row)
    return unique


def _fetch_core(
    backend: CitationBackend, rows: Sequence[_Row]
) -> dict[tuple[str, str], dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for start in range(0, len(rows), ABSTRACT_BATCH_SIZE):
        batch = rows[start : start + ABSTRACT_BATCH_SIZE]
        query = " OR ".join(f"EXT_ID:{r.id}" for r in batch)
        # EXT_ID matches across sources, so ask for more rows than IDs.
        for raw in backend.search(query, page_size=len(batch) * 2):
            key = (str(raw.get("source", "")), str(raw.get("id", "")))
            found.setdefault(key, raw)
    return found


def _paper_for(row: _Row, core: dict[str, Any] | None) -> DiscoveredPaper:
    spec = _spec(*row.routes[0])
    if core is not None:
        return parse_result(core, spec)
    # Not returned by the batch search. Kept, with what the link row carries,
    # rather than dropped: the registry records it and acquisition says why its
    # full text could not be had.
    return DiscoveredPaper(
        title=_clean(row.title).rstrip("."),
        pmid=row.pmid,
        year=row.year,
        discovered_via=spec.key,
        discovery_tier=spec.tier,
    )


def screen_citations(
    backend: CitationBackend,
    seed_pmids: Iterable[str],
    directions: Sequence[str] = ("forward",),
    known_pmids: Iterable[str] = (),
    known_dois: Iterable[str] = (),
) -> CitationScreen:
    """Follow links from each seed and run the four-step screen."""
    seeds = list(dict.fromkeys(seed_pmids))
    known_p = set(known_pmids) | set(seeds)
    known_d = {d.lower() for d in known_dois}
    screen = CitationScreen(seeds=seeds, directions=list(directions))

    rows: list[_Row] = []
    for seed in seeds:
        for direction in directions:
            for raw in backend.links(seed, direction):
                screen.raw += 1
                if not raw.get("id"):
                    # An unresolved reference: nothing to fetch or register.
                    continue
                rows.append(
                    _Row(
                        source=str(raw.get("source") or ""),
                        id=str(raw["id"]),
                        title=str(raw.get("title") or ""),
                        year=_as_int(raw.get("pubYear")),
                        routes=[(direction, seed)],
                    )
                )

    unique = _dedupe(rows)
    screen.deduped = len(unique)

    unknown = [r for r in unique if r.pmid not in known_p]
    core = _fetch_core(backend, unknown)

    for row in unknown:
        paper = _paper_for(row, core.get((row.source, row.id)))
        if (paper.pmid and paper.pmid in known_p) or (paper.doi and paper.doi.lower() in known_d):
            continue
        screen.not_yet_known += 1
        if not paper.abstract:
            screen.no_abstract += 1
        if not mentions_medaka(paper.title, paper.abstract):
            continue
        screen.medaka += 1
        screen.kept.append(
            ScreenedPaper(paper=paper, routes=[route_for(d, s) for d, s in row.routes])
        )
    return screen
