"""Read and cross-validate the YAML seed files.

Validation happens before anything touches the database, so a seed file with a
typo'd gene name fails loudly at load time instead of quietly minting a second
`gene:adyc5` node that no query will ever find.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .config import SEED_DIR
from .models import COMPARATIVE_CEILING, MEDAKA, Claim, Entity, Paper, SeedBundle
from .vocabulary import EVIDENCE_RANK, NodeLabel


class SeedValidationError(ValueError):
    """Raised with every problem found, not just the first."""


def load_file(path: Path) -> SeedBundle:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SeedValidationError(f"{path.name}: top level must be a mapping")
    return SeedBundle(
        source_file=path.name,
        papers=[Paper(**p) for p in raw.get("papers", [])],
        entities=[Entity(**e) for e in raw.get("entities", [])],
        claims=[Claim(**c) for c in raw.get("claims", [])],
    )


def load_dir(seed_dir: Path | None = None) -> SeedBundle:
    """Merge every `*.yaml` in the seed directory into one bundle.

    Files are read in sorted order so numeric prefixes (`00-papers.yaml`) express
    a reading order, though the loader itself does not depend on it -- all
    cross-references are resolved after every file is parsed.
    """
    seed_dir = seed_dir or SEED_DIR
    paths = sorted(seed_dir.glob("*.yaml"))
    if not paths:
        raise SeedValidationError(f"no seed files found in {seed_dir}")

    merged = SeedBundle(source_file=str(seed_dir))
    errors: list[str] = []
    for path in paths:
        try:
            bundle = load_file(path)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        merged.papers.extend(bundle.papers)
        merged.entities.extend(bundle.entities)
        merged.claims.extend(bundle.claims)

    if errors:
        raise SeedValidationError("\n".join(errors))

    validate(merged)
    return merged


def validate(bundle: SeedBundle) -> None:
    """Check cross-file references and duplicate definitions."""
    errors: list[str] = []

    paper_keys: dict[str, Paper] = {}
    for paper in bundle.papers:
        if paper.key in paper_keys:
            errors.append(f"duplicate paper key {paper.key!r}")
        paper_keys[paper.key] = paper

    # Two different keys pointing at one DOI would create one node with two
    # handles, which silently splits a paper's evidence in the seed files.
    by_doi: dict[str, str] = {}
    for paper in bundle.papers:
        if not paper.doi:
            continue
        doi = paper.doi.lower()
        if doi in by_doi and by_doi[doi] != paper.key:
            errors.append(f"papers {by_doi[doi]!r} and {paper.key!r} share DOI {doi}")
        by_doi.setdefault(doi, paper.key)

    entity_ids: dict[str, Entity] = {}
    for entity in bundle.entities:
        if entity.id in entity_ids:
            first = entity_ids[entity.id]
            if first.name != entity.name or first.label is not entity.label:
                errors.append(f"id collision on {entity.id}: {first.name} vs {entity.name}")
            else:
                errors.append(f"duplicate entity definition {entity.id}")
        entity_ids[entity.id] = entity

    for claim in bundle.claims:
        where = f"claim {claim.predicate.value} {claim.subject.name} -> {claim.object.name}"
        for ref in (claim.subject, claim.object):
            if ref.id not in entity_ids:
                errors.append(
                    f"{where}: references undefined {ref.label.value} {ref.name!r} "
                    f"(expected an entity with id {ref.id})"
                )
        for ev in claim.evidence:
            if ev.paper not in paper_keys:
                errors.append(f"{where}: evidence cites unknown paper key {ev.paper!r}")

        # The subject's own species is only knowable once every entity is parsed,
        # which is why this half of the comparative-ceiling rule lives here rather
        # than on the Claim. The trait/phenotype half is enforced on the model.
        subject = entity_ids.get(claim.subject.id)
        subject_is_medaka = (
            subject is not None
            and subject.label not in {NodeLabel.HUMAN_GENE, NodeLabel.HUMAN_PHENOTYPE}
            and (subject.species or MEDAKA).lower().startswith("oryzias")
        )
        if subject_is_medaka:
            for ev in claim.evidence:
                if ev.is_comparative and ev.rank > EVIDENCE_RANK[COMPARATIVE_CEILING]:
                    errors.append(
                        f"{where}: {ev.species} evidence recorded at {ev.level.value}, "
                        f"above the comparative ceiling {COMPARATIVE_CEILING.value} "
                        f"for a claim about a medaka entity"
                    )

    if errors:
        raise SeedValidationError("\n".join(sorted(set(errors))))


def resolve_paper_ids(bundle: SeedBundle) -> dict[str, str]:
    """Map the seed files' short paper handles to graph ids."""
    return {paper.key: paper.id for paper in bundle.papers}
