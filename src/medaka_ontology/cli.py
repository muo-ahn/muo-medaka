"""Command-line entry point."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .candidates import (
    AcceptanceError,
    accept_candidate,
    candidate_counts,
    pending_candidates,
    pending_proposed_genes,
    reject_candidate,
)
from .config import DOSSIER_DIR, EXPORT_DIR, SEED_DIR
from .convergence import gene_claim_violations
from .db import Neo4jUnavailableError, graph_counts, install_schema, session_scope
from .discovery import all_queries
from .dossier import render_trait
from .ingest import ingest_bundle, unprocessed_papers
from .loader import SeedValidationError, load_dir
from .models import slugify
from .pipeline import RunLimits
from .pipeline import run as run_pipeline
from .queries import disputed_claims, list_traits, review_queue, search, shared_genes
from .registry import papers_in_states, state_counts
from .vocabulary import EvidenceLevel, PaperState, Stance


def _use_utf8_output() -> None:
    """Dossiers carry em dashes, arrows and -- for traits whose Japanese labels
    are recorded -- kana and kanji. On a Windows console still defaulting to a
    legacy code page, writing any of that raises UnicodeEncodeError and takes the
    command down mid-render. A terminal that cannot show UTF-8 cannot show this
    data at all, so the stream is switched rather than the content flattened.

    Runs before `Console()` is constructed, since rich captures the encoding of
    the stream it is given.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_use_utf8_output()

app = typer.Typer(
    help="Evidence-backed ornamental trait ontology for medaka.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


@app.command()
def validate(
    seed_dir: Path = typer.Option(SEED_DIR, help="Directory of seed YAML files"),
) -> None:
    """Parse and cross-check the seed files. Touches no database."""
    try:
        bundle = load_dir(seed_dir)
    except SeedValidationError as exc:
        _fail(f"seed validation failed:\n{exc}")
        return
    console.print(
        f"[green]OK[/green] {len(bundle.papers)} papers, "
        f"{len(bundle.entities)} entities, {len(bundle.claims)} claims"
    )
    disputed = [c for c in bundle.claims if c.is_disputed]
    if disputed:
        console.print(f"[yellow]{len(disputed)} claim(s) carry contradicting evidence[/yellow]")
        for claim in disputed:
            console.print(
                f"  - {claim.subject.name} --{claim.predicate.value}--> {claim.object.name}"
            )
    known = gene_claim_violations(bundle)
    if known:
        console.print(
            f"[yellow]{len(known)} gene claim(s) on the known-violations list, "
            "awaiting a data fix[/yellow]"
        )
        for (trait, gene), why in sorted(known.items()):
            console.print(f"  - {trait} --associated_with_gene--> {gene}: {why}")


@app.command()
def init() -> None:
    """Create Neo4j constraints and indexes. Idempotent."""
    try:
        with session_scope() as session:
            applied = install_schema(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]schema installed[/green] ({len(applied)} statements)")


@app.command()
def load(
    seed_dir: Path = typer.Option(SEED_DIR, help="Directory of seed YAML files"),
) -> None:
    """Validate the seed files and ingest them. Safe to re-run."""
    try:
        bundle = load_dir(seed_dir)
    except SeedValidationError as exc:
        _fail(f"seed validation failed:\n{exc}")
        return
    try:
        with session_scope() as session:
            install_schema(session)
            report = ingest_bundle(session, bundle)
            counts = graph_counts(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return

    console.print("[bold]Run report[/bold]")
    console.print(
        f"  ingested: {report.papers} papers, {report.entities} entities, "
        f"{report.claims} claims, {report.evidence} evidence"
    )
    console.print(f"  graph now: {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}")
    console.print(f"  pending review: {report.pending_review}")
    if report.disputed_claims:
        console.print(f"[yellow]  disputed claims ({len(report.disputed_claims)}):[/yellow]")
        for line in report.disputed_claims:
            console.print(f"    - {line}")


@app.command()
def status() -> None:
    """Node counts and unprocessed-paper backlog."""
    try:
        with session_scope() as session:
            counts = graph_counts(session)
            backlog = unprocessed_papers(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("label", "count")
    for label, count in sorted(counts.items()):
        table.add_row(label, str(count))
    console.print(table)
    console.print(f"papers not yet full-text processed: {len(backlog)}")


@app.command()
def traits() -> None:
    """List every ornamental trait with its claim count."""
    try:
        with session_scope() as session:
            rows = list_traits(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("trait", "category", "composite", "claims")
    for row in rows:
        table.add_row(
            row["name"],
            row.get("category") or "",
            "yes" if row.get("is_composite") else "",
            str(row["claims"]),
        )
    console.print(table)


@app.command()
def dossier(
    name: str = typer.Argument(..., help="Trait name, e.g. hikari"),
    out: Path | None = typer.Option(None, help="Write to this file instead of stdout"),
) -> None:
    """Render the human-readable trait dossier. PRD §13."""
    try:
        with session_scope() as session:
            text = render_trait(session, name)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    except KeyError as exc:
        _fail(str(exc))
        return
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        console.print(f"[green]wrote[/green] {out}")
    else:
        console.print(text, markup=False, highlight=False)


@app.command("dossier-all")
def dossier_all(
    out_dir: Path = typer.Option(DOSSIER_DIR, help="Directory to write dossiers into"),
) -> None:
    """Render a dossier for every trait."""
    try:
        with session_scope() as session:
            names = [row["name"] for row in list_traits(session)]
            out_dir.mkdir(parents=True, exist_ok=True)
            for name in names:
                # Slugged, because trait names include spaces and parentheses
                # ("panda (pa) lab mutant") and those make for filenames that are
                # awkward in a shell and in a diff. The trait's own name is the
                # first line of every file.
                path = out_dir / f"{slugify(name)}.md"
                path.write_text(render_trait(session, name), encoding="utf-8")
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]wrote {len(names)} dossiers[/green] to {out_dir}")


@app.command()
def review() -> None:
    """Show the human-review queue. PRD §12."""
    try:
        with session_scope() as session:
            rows = review_queue(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("[green]review queue empty[/green]")
        return
    table = Table("subject", "predicate", "object", "sup", "con", "reasons", "note")
    for row in rows:
        table.add_row(
            row["subject"],
            row["predicate"],
            row["object"],
            str(row["supports"]),
            str(row["contradicts"]),
            ", ".join(row.get("reasons") or []),
            row.get("note") or "",
        )
    console.print(table)
    console.print(f"{len(rows)} claim(s) pending")
    console.print(
        "Set `review_status` and `review_note` on a :Claim to record a decision; "
        "the loader never overwrites either. Claim content comes from the seed "
        "files and is rewritten on every load."
    )


@app.command()
def disputed() -> None:
    """Claims with evidence on both sides. PRD §9."""
    try:
        with session_scope() as session:
            rows = disputed_claims(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no disputed claims")
        return
    table = Table("subject", "predicate", "object", "reasons")
    for row in rows:
        table.add_row(
            row["subject"], row["predicate"], row["object"], ", ".join(row.get("reasons") or [])
        )
    console.print(table)


@app.command("shared-genes")
def shared_genes_cmd() -> None:
    """Traits that share a gene. PRD §1.

    Pairs related by subsumption are excluded: an umbrella class and its member
    share a locus by construction, not by biology.
    """
    try:
        with session_scope() as session:
            rows = shared_genes(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no shared genes recorded")
        return
    table = Table("trait A", "trait B", "shared genes", "contested")
    for row in rows:
        table.add_row(
            row["trait_a"],
            row["trait_b"],
            ", ".join(row["shared_genes"]),
            "yes" if row["contested"] else "",
        )
    console.print(table)
    console.print(
        "Pairs related by subsumption are excluded, and a link with no supporting "
        "evidence is not a shared gene. 'contested' means at least one of the two "
        "links also carries contradicting evidence."
    )


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Free-text query over entity names and aliases"),
    limit: int = typer.Option(20),
) -> None:
    """Full-text search over entity names and aliases."""
    try:
        with session_scope() as session:
            rows = search(session, query, limit=limit)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("label", "name", "score")
    for row in rows:
        table.add_row(row["label"], row["name"], f"{row['score']:.2f}")
    console.print(table)


# ---------------------------------------------------------------------------
# Discovery pipeline. Issue #1.
# ---------------------------------------------------------------------------


@app.command()
def queries(
    limit_traits: int | None = typer.Option(None, help="Only the first N traits"),
    show: int = typer.Option(20, help="How many queries to print"),
) -> None:
    """Show the literature queries the current ontology generates.

    Run this before `pipeline` to see what a run would ask for. The queries are
    built from the graph, so they change as the ontology grows - which is the
    whole mechanism by which discovery expands.
    """
    try:
        with session_scope() as session:
            specs = all_queries(session, limit_traits=limit_traits)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    table = Table("tier", "origin", "query")
    for spec in specs[:show]:
        table.add_row(spec.tier, spec.origin_entity_name, spec.query)
    console.print(table)
    console.print(f"{len(specs)} queries generated; showing {min(show, len(specs))}")


@app.command()
def pipeline(
    max_queries: int = typer.Option(12, help="Cap on literature queries this run"),
    max_papers: int = typer.Option(15, help="Cap on papers fetched this run"),
    page_size: int = typer.Option(25, help="Results per query"),
    max_traits: int | None = typer.Option(None, help="Only expand the first N traits"),
    skip_discovery: bool = typer.Option(
        False, help="Process the existing backlog without searching"
    ),
    no_abstract_fallback: bool = typer.Option(
        False, help="Skip papers whose full text is unavailable rather than mining the abstract"
    ),
) -> None:
    """Run one discovery cycle: search, acquire, extract, stage for review.

    Nothing this command produces enters the ontology. Everything lands in the
    candidate queue; `accept` is the only path into the graph.
    """
    limits = RunLimits(
        max_traits=max_traits,
        max_queries=max_queries,
        page_size=page_size,
        max_papers_to_acquire=max_papers,
        include_abstract_only=not no_abstract_fallback,
    )
    try:
        with session_scope() as session:
            report = run_pipeline(session, limits=limits, skip_discovery=skip_discovery)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return

    path = report.write()
    console.print("[bold]Run report[/bold]")
    console.print(
        f"  queries: {report.queries_run}, hits: {report.hits}, "
        f"new papers: {report.papers_new}, already known: {report.papers_already_known}"
    )
    console.print(
        f"  full text: {report.fulltext_acquired} acquired, "
        f"{report.fulltext_failed} unavailable ({report.abstract_only} mined from abstract)"
    )
    console.print(
        f"  candidates: {report.candidates_new} new, "
        f"{report.candidates_duplicate} already staged; "
        f"proposed genes: {report.proposed_genes}"
    )
    if report.new_paper_titles:
        console.print("[green]  newly discovered:[/green]")
        for title in report.new_paper_titles[:10]:
            console.print(f"    - {title[:100]}")
    if report.failures:
        console.print(f"[yellow]  {len(report.failures)} acquisition failure(s):[/yellow]")
        for failure in report.failures[:5]:
            console.print(f"    - {failure['paper']}: {failure['reason'][:80]}")
    console.print(f"  paper states: {report.paper_states}")
    console.print(f"  written to {path}")


@app.command()
def papers(
    state: str | None = typer.Option(None, help="Filter to one processing state"),
    limit: int = typer.Option(30),
) -> None:
    """Papers in the registry, by processing state. Issue #1 §2."""
    try:
        with session_scope() as session:
            if state:
                try:
                    wanted = [PaperState(state.upper())]
                except ValueError:
                    _fail(
                        f"unknown state {state!r}; expected one of "
                        f"{[s.value for s in PaperState]}"
                    )
                    return
                rows = papers_in_states(session, wanted, limit=limit)
            else:
                rows = []
            counts = state_counts(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return

    table = Table("state", "count")
    for name, count in sorted(counts.items()):
        table.add_row(name, str(count))
    console.print(table)

    if rows:
        detail = Table("title", "doi", "discovered via")
        for row in rows:
            detail.add_row(
                (row["title"] or "")[:70],
                row["doi"] or "",
                ", ".join((row["discovered_via"] or [])[:2]),
            )
        console.print(detail)


@app.command()
def candidates(
    limit: int = typer.Option(20),
    full: bool = typer.Option(False, help="Print the whole quote rather than a snippet"),
) -> None:
    """Staged proposals awaiting a decision. Issue #1 §7.

    These are co-mentions, not readings. The quote is the evidence; the
    suggested level is a cue match and carries no authority.
    """
    try:
        with session_scope() as session:
            rows = pending_candidates(session, limit=limit)
            counts = candidate_counts(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no pending candidates")
        console.print(f"counts: {counts}")
        return
    for row in rows:
        console.print(
            f"[bold]{row['id']}[/bold]  {row['subject']} --{row['predicate']}--> "
            f"{row['object']}"
        )
        cue = f" (cue: {row['level_cue']})" if row["level_cue"] else ""
        flags = []
        if row["negated"]:
            flags.append("NEGATED - the sentence may deny this")
        if row["species"] and not str(row["species"]).lower().startswith("oryzias"):
            flags.append(f"comparative: {row['species']}")
        console.print(
            f"  suggested: {row['suggested_level']}{cue}"
            + (f"  [yellow]{'; '.join(flags)}[/yellow]" if flags else "")
        )
        quote = row["quote"] if full else (row["quote"] or "")[:220]
        console.print(f"  \"{quote}\"")
        console.print(f"  {row['section']} · {(row['paper_title'] or '')[:70]}")
        console.print("")
    console.print(f"{len(rows)} shown; counts: {counts}")


@app.command()
def accept(
    candidate_id: str = typer.Argument(..., help="Candidate id from `candidates`"),
    level: str = typer.Option(..., help="Evidence level YOU are assigning"),
    contradicts: bool = typer.Option(False, help="Record as contradicting, not supporting"),
    note: str | None = typer.Option(None, help="Your interpretation, kept on the claim"),
) -> None:
    """Accept a candidate into the ontology at an evidence level you choose.

    The level is yours, not the extractor's suggestion. The vocabulary shape
    check and the comparative-evidence ceiling both apply here, so an accept
    that would create an unsound claim is refused.
    """
    try:
        chosen = EvidenceLevel(level.upper())
    except ValueError:
        _fail(f"unknown level {level!r}; expected one of {[x.value for x in EvidenceLevel]}")
        return
    try:
        with session_scope() as session:
            claim_id = accept_candidate(
                session,
                candidate_id,
                chosen,
                Stance.CONTRADICTS if contradicts else Stance.SUPPORTS,
                note,
            )
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    except AcceptanceError as exc:
        _fail(f"cannot accept: {exc}")
        return
    console.print(f"[green]accepted[/green] into claim {claim_id}")


@app.command()
def reject(
    candidate_id: str = typer.Argument(...),
    note: str | None = typer.Option(None, help="Why, so the same call is not re-litigated"),
) -> None:
    """Reject a candidate. It stays recorded so it is not re-proposed as new."""
    try:
        with session_scope() as session:
            reject_candidate(session, candidate_id, note)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    except AcceptanceError as exc:
        _fail(str(exc))
        return
    console.print("[green]rejected[/green]")


@app.command("proposed-genes")
def proposed_genes_cmd() -> None:
    """Gene symbols seen beside known entities but absent from the ontology."""
    try:
        with session_scope() as session:
            rows = pending_proposed_genes(session)
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    if not rows:
        console.print("no proposed genes")
        return
    table = Table("symbol", "resolution", "seen near", "paper")
    for row in rows:
        resolution = row["resolution"]
        if row["collides_with"]:
            resolution += f" ({', '.join(row['collides_with'][:2])})"
        table.add_row(
            row["symbol"],
            resolution,
            ", ".join((row["near_entities"] or [])[:3]),
            (row["paper_title"] or "")[:52],
        )
    console.print(table)
    console.print(
        f"{len(rows)} proposal(s). These are orthographic guesses from gene "
        "nomenclature, not identifications - confirm against a gene database "
        "before adding any to data/seed/. A resolution other than NEW means the "
        "symbol already exists somewhere in the graph; adding it again would "
        "split one concept across two nodes."
    )


@app.command()
def export(
    out_dir: Path = typer.Option(EXPORT_DIR, help="Directory to write the dump into"),
) -> None:
    """Dump the whole graph to JSONL.

    The knowledge must not be trapped in a Docker volume; this is the backup path
    the storage ADR promises.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    nodes_path = out_dir / f"nodes-{stamp}.jsonl"
    rels_path = out_dir / f"relationships-{stamp}.jsonl"
    try:
        with session_scope() as session:
            with nodes_path.open("w", encoding="utf-8") as fh:
                for record in session.run(
                    "MATCH (n) RETURN labels(n) AS labels, properties(n) AS props"
                ):
                    fh.write(
                        json.dumps(
                            {"labels": record["labels"], "properties": record["props"]},
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n"
                    )
            with rels_path.open("w", encoding="utf-8") as fh:
                for record in session.run(
                    "MATCH (a)-[r]->(b) "
                    "RETURN a.id AS start, type(r) AS type, b.id AS end, "
                    "properties(r) AS props"
                ):
                    fh.write(
                        json.dumps(dict(record), ensure_ascii=False, default=str) + "\n"
                    )
    except Neo4jUnavailableError as exc:
        _fail(str(exc))
        return
    console.print(f"[green]exported[/green] {nodes_path.name}, {rels_path.name}")


if __name__ == "__main__":
    app()
