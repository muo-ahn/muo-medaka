"""Fetch full text, and record why when it cannot be had.

Issue #1 §3. Machine-readable full text is preferred over anything scraped, and
a failure is written down rather than quietly degraded into "we'll just use the
abstract" -- because evidence extracted from an abstract and evidence extracted
from a Results section are not the same thing, and the graph has to be able to
say which it got.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx

from .config import REPO_ROOT

EUROPE_PMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"

FULLTEXT_CACHE = REPO_ROOT / "data" / "cache" / "fulltext"

#: Never mined. A reference list co-mentions everything with everything, so
#: leaving it in would make every gene appear alongside every trait.
#:
#: This is a denylist rather than an allowlist of wanted sections, and the
#: distinction cost a debugging round to find. Papers do not title their sections
#: "Results" -- the seed paper's are "Genome-wide association studies of
#: ornamental phenotypes", "Population genomic analyses" and so on. Matching
#: against a list of expected names discarded most of the article and produced a
#: run that looked like it worked and extracted almost nothing.
SKIP_SECTIONS = (
    "reference",
    "acknowledg",
    "funding",
    "author contribution",
    "supplementary",
    "supporting information",
    "conflict of interest",
    "competing interest",
    "data availability",
    "ethics",
    "abbreviation",
)


class AcquisitionFailure(str):
    NO_PMCID = "no PMCID; not in Europe PMC full-text corpus"
    NOT_OPEN_ACCESS = "not open access"
    HTTP_ERROR = "full-text request failed"
    EMPTY = "full-text response was empty"
    UNPARSEABLE = "full-text XML could not be parsed"


@dataclass
class FullText:
    """Acquired full text plus where it came from."""

    paper_id: str
    source: str
    sections: dict[str, str] = field(default_factory=dict)
    cached_path: Path | None = None

    @property
    def mineable_text(self) -> str:
        """Sections worth extracting from, concatenated."""
        return "\n\n".join(
            body for name, body in self.sections.items() if _is_evidence_section(name)
        )

    def section_for(self, needle: str) -> str | None:
        """Which section a snippet came from, for provenance on the evidence."""
        for name, body in self.sections.items():
            if needle in body:
                return name
        return None


@dataclass
class AcquisitionResult:
    paper_id: str
    ok: bool
    fulltext: FullText | None = None
    reason: str | None = None


def _is_evidence_section(name: str) -> bool:
    lowered = name.lower()
    return not any(skip in lowered for skip in SKIP_SECTIONS)


class FullTextBackend(Protocol):
    def fetch_xml(self, pmcid: str) -> str: ...


class EuropePmcFullTextBackend:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=60.0)

    def fetch_xml(self, pmcid: str) -> str:
        response = self._client.get(EUROPE_PMC_FULLTEXT.format(pmcid=pmcid))
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        self._client.close()


def _node_text(node: ET.Element) -> str:
    """All descendant text, with tags stripped.

    `itertext` rather than a targeted walk, because JATS body paragraphs are full
    of inline markup (italics on gene symbols, cross-references, superscripts)
    and every one of those would otherwise cut a sentence in half -- taking a
    co-mention with it.
    """
    return " ".join(" ".join(node.itertext()).split())


def parse_jats(xml_text: str) -> dict[str, str]:
    """Pull titled sections out of a JATS article."""
    root = ET.fromstring(xml_text)
    sections: dict[str, str] = {}

    for abstract in root.iter("abstract"):
        text = _node_text(abstract)
        if text:
            sections["Abstract"] = text
        break

    for index, sec in enumerate(root.iter("sec")):
        title_node = sec.find("title")
        title = _node_text(title_node) if title_node is not None else f"Section {index + 1}"
        # Paragraphs only: nested <sec> children are visited by this same loop,
        # so taking the whole subtree here would duplicate them.
        body = " ".join(_node_text(p) for p in sec.findall("p"))
        if body.strip():
            sections[title or f"Section {index + 1}"] = body.strip()
    return sections


def acquire(
    paper: dict,
    backend: FullTextBackend,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> AcquisitionResult:
    """Get one paper's full text, preferring the cache.

    `paper` is a registry row: it must carry `id`, and may carry `pmcid`.
    """
    paper_id = paper["id"]
    cache_dir = cache_dir or FULLTEXT_CACHE
    pmcid = paper.get("pmcid")

    if not pmcid:
        return AcquisitionResult(paper_id, ok=False, reason=AcquisitionFailure.NO_PMCID)

    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{pmcid}.xml"

    if use_cache and cached.exists() and cached.stat().st_size > 0:
        xml_text = cached.read_text(encoding="utf-8")
        source = f"cache:{cached.name}"
    else:
        try:
            xml_text = backend.fetch_xml(pmcid)
        except Exception as exc:
            return AcquisitionResult(
                paper_id, ok=False, reason=f"{AcquisitionFailure.HTTP_ERROR}: {exc}"
            )
        if not xml_text.strip():
            return AcquisitionResult(paper_id, ok=False, reason=AcquisitionFailure.EMPTY)
        cached.write_text(xml_text, encoding="utf-8")
        source = EUROPE_PMC_FULLTEXT.format(pmcid=pmcid)

    try:
        sections = parse_jats(xml_text)
    except ET.ParseError as exc:
        return AcquisitionResult(
            paper_id, ok=False, reason=f"{AcquisitionFailure.UNPARSEABLE}: {exc}"
        )

    if not sections:
        return AcquisitionResult(paper_id, ok=False, reason=AcquisitionFailure.EMPTY)

    return AcquisitionResult(
        paper_id,
        ok=True,
        fulltext=FullText(
            paper_id=paper_id, source=source, sections=sections, cached_path=cached
        ),
    )
