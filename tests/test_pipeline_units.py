"""Offline tests for the discovery pipeline's judgement calls.

Every behaviour here was a bug first. The pipeline's first run against real
literature returned neurotoxicology papers, discarded two thirds of every
article it did fetch, and filed corn-snake results as medaka findings. These
tests pin the fixes so the next change to a regex does not quietly undo them.

Nothing here touches the network or a database.
"""

from __future__ import annotations

import pytest

from medaka_ontology.acquisition import _is_evidence_section, parse_jats
from medaka_ontology.discovery import (
    _EXPANSION_QUERY,
    DiscoveryTier,
    QuerySpec,
    _is_anatomy_searchable,
    _is_searchable,
    _or_group,
    parse_result,
    queries_for_trait,
)
from medaka_ontology.extraction import (
    PREDICATE_PREFERENCE,
    detect_level,
    detect_paper_species,
    detect_species,
    extract_from_text,
    predicate_for,
)
from medaka_ontology.lexicon import (
    Lexicon,
    SurfaceForm,
    find_mentions,
    is_ambiguous,
    sentences,
)
from medaka_ontology.models import MEDAKA
from medaka_ontology.registry import _STATE_RANK, paper_id_for
from medaka_ontology.resolution import propose_new_genes
from medaka_ontology.vocabulary import (
    ACTIONABLE_PAPER_STATES,
    EvidenceLevel,
    NodeLabel,
    PaperState,
    Predicate,
)


def _form(text: str, label: NodeLabel, name: str | None = None) -> SurfaceForm:
    name = name or text
    return SurfaceForm(
        text=text,
        entity_id=f"{label.value.lower()}:{name}",
        entity_name=name,
        label=label,
        ambiguous=is_ambiguous(text),
    )


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon(
        forms=[
            _form("orochi", NodeLabel.ORNAMENTAL_TRAIT),
            _form("hikari", NodeLabel.ORNAMENTAL_TRAIT),
            _form("black", NodeLabel.ORNAMENTAL_TRAIT),
            _form("deme", NodeLabel.ORNAMENTAL_TRAIT),
            _form("adcy5", NodeLabel.GENE),
            _form("zic1", NodeLabel.GENE),
            _form("hyper-melanism", NodeLabel.PHENOTYPE),
        ]
    )


# --- lexicon: the ambiguity rule -------------------------------------------


def test_common_english_trait_names_are_ambiguous():
    """`black`, `gold` and `deme` are trait names here and ordinary words
    everywhere else. `deme` is worst: in a genetics paper it almost always means
    a local population."""
    for word in ("black", "white", "gold", "deme", "panda"):
        assert is_ambiguous(word), word


def test_distinctive_names_are_not_ambiguous():
    for word in ("orochi", "hirenaga", "toumeirin", "adcy5", "kcnq5a"):
        assert not is_ambiguous(word), word


def test_short_tokens_are_always_ambiguous():
    assert is_ambiguous("Da")
    assert is_ambiguous("fm")


def test_ambiguous_form_alone_is_not_a_mention(lexicon):
    """A sentence about coal mining must not produce a `black` trait mention."""
    hits = find_mentions("The samples were black after firing.", lexicon)
    assert hits == []


def test_ambiguous_form_counts_when_a_safe_form_corroborates(lexicon):
    hits = find_mentions("Expression of adcy5 was higher in black individuals.", lexicon)
    names = {h.entity_name for h in hits}
    assert "adcy5" in names
    assert "black" in names


def test_ambiguous_form_counts_when_the_organism_is_named(lexicon):
    hits = find_mentions("In medaka, the black strain shows more melanophores.", lexicon)
    assert "black" in {h.entity_name for h in hits}


def test_word_boundaries_are_respected(lexicon):
    assert find_mentions("blackberry cultivars", lexicon) == []


def test_sentence_splitting_survives_citations():
    text = "Kon et al. 2026 found a deletion. It was homozygous in 16 of 18 fish."
    assert len(sentences(text)) == 2


# --- discovery: query terms ------------------------------------------------


def test_two_letter_alias_never_reaches_a_query():
    """`Da` retrieved every medaka paper ever published, because `da` occurs in
    all of them."""
    assert not _is_searchable("Da")


def test_single_generic_word_never_reaches_a_query():
    assert not _is_searchable("black")
    assert not _is_searchable("swallow")


def test_multiword_scientific_phrases_stay_searchable():
    """The lexicon calls these ambiguous because they are useless for matching
    text. As retrieval keys they are precise, and dropping them would delete the
    mechanism rung - the only rung that reaches outside the ornamental
    literature."""
    assert _is_searchable("dorsoventral patterning")
    assert _is_searchable("chromatophore development")


def test_distinctive_trait_names_stay_searchable():
    assert _is_searchable("orochi")
    assert _is_searchable("Da mutant")


def test_field_prefix_is_applied_to_every_term():
    grouped = _or_group(["hikari", "Da mutant"], field="TITLE_ABS")
    assert grouped.count("TITLE_ABS:") == 2
    assert 'TITLE_ABS:"Da mutant"' in grouped


# --- discovery: the anatomy rung -------------------------------------------


class _FakeResult:
    def __init__(self, record: dict | None):
        self._record = record

    def single(self) -> dict | None:
        return self._record


class _FakeSession:
    """Stands in for a Neo4j session by returning one prepared expansion row.

    The Cypher itself is not executed here, so what these tests pin is the
    Python side: which rows become terms, and which terms become queries.
    """

    def __init__(self, record: dict | None):
        self._record = record

    def run(self, query: str, **params):
        return _FakeResult(self._record)


def _expansion_row(anatomy: list[list] | None = None, **overrides) -> dict:
    row = {
        "trait": "kagamirin",
        "aliases": [],
        "mutants": [],
        "mutant_aliases": [],
        "genes": [],
        "mechanisms": [],
        # Each entry is [name, query_terms], as the Cypher collects it.
        "anatomy": anatomy if anatomy is not None else [],
    }
    row.update(overrides)
    return row


def _anatomy_specs(record: dict) -> list[QuerySpec]:
    specs = queries_for_trait(_FakeSession(record), "trait:kagamirin", "kagamirin")
    return [
        s
        for s in specs
        if s.tier in (DiscoveryTier.ANATOMY, DiscoveryTier.ANATOMY_WIDE)
    ]


def test_anatomy_rung_emits_both_scopes():
    """Measured through the real pipeline (relevance order, pageSize 25) on the
    14 traits whose gene is named by a paper other than kon2026: tight 8/14,
    wide 8/14, union 10/14. Neither subsumes the other -- wide alone recovers
    reallongfin and yellow (zebrafish papers that `TITLE:(medaka)` excludes by
    construction), tight alone recovers daruma and fused centrum. Dropping
    either query costs two traits."""
    tight, wide = _anatomy_specs(_expansion_row(anatomy=[["dorsal fin", ["fin"]]]))

    assert tight.tier == DiscoveryTier.ANATOMY
    assert tight.query == 'TITLE:(medaka) AND (TITLE:"fin")'

    assert wide.tier == DiscoveryTier.ANATOMY_WIDE
    assert wide.query.startswith('(TITLE:"fin") AND (')
    # The wide scope's whole purpose: the zebrafish papers that name the gene.
    assert "zebrafish" in wide.query
    assert "medaka" not in wide.query.split(" AND ")[0]


def test_the_two_scopes_are_distinguishable_in_provenance():
    """`discovered_via` has to say which shape found a paper, or the measurement
    above cannot be repeated on the next corpus."""
    tight, wide = _anatomy_specs(_expansion_row(anatomy=[["scale", ["scale"]]]))
    assert tight.key != wide.key


def test_anatomy_terms_come_from_query_terms_not_the_node_name():
    """The searchable unit is coarser than the ontology's unit: a paper about
    dorsal fins says `fin` in its title, not `dorsal fin`."""
    tight, _ = _anatomy_specs(_expansion_row(anatomy=[["dorsal fin", ["fin"]]]))
    assert '"fin"' in tight.query
    assert "dorsal fin" not in tight.query


def test_anatomy_terms_fall_back_to_the_node_name():
    """The field is being backfilled by another change; until it lands, and for
    any node it misses, the rung must still produce a query."""
    tight, _ = _anatomy_specs(_expansion_row(anatomy=[["peritoneum", []]]))
    assert '"peritoneum"' in tight.query

    tight_null, _ = _anatomy_specs(_expansion_row(anatomy=[["peritoneum", None]]))
    assert '"peritoneum"' in tight_null.query


def test_unsupported_anatomy_claim_produces_no_query():
    """An unsupported claim must not be able to drive a search. The guard is the
    `EXISTS { MATCH (:Evidence)-[:SUPPORTS]->(ac) }` in the expansion Cypher, so
    a filtered-out claim arrives as a row with no anatomy node in it."""
    assert _anatomy_specs(_expansion_row(anatomy=[[None, []]])) == []


def test_evidence_guard_is_present_on_both_new_claim_hops():
    """Pinned as text because the clause above is what the previous test relies
    on; the offline suite cannot execute the Cypher that enforces it."""
    for claim in ("pc", "ac"):
        assert f"EXISTS {{ MATCH (:Evidence)-[:SUPPORTS]->({claim}) }}" in _EXPANSION_QUERY


def test_trait_with_no_phenotypes_emits_no_anatomy_query():
    specs = queries_for_trait(
        _FakeSession(_expansion_row()), "trait:kagamirin", "kagamirin"
    )
    assert specs
    assert all(
        s.tier not in (DiscoveryTier.ANATOMY, DiscoveryTier.ANATOMY_WIDE) for s in specs
    )


def test_short_anatomy_terms_survive_the_query_filter():
    """`fin` and `eye` are three characters and `scale` and `iris` are in
    AMBIGUOUS_SURFACE_FORMS, so all four fail the general `_is_searchable`.
    Running anatomy through that filter deletes the rung rather than the noise;
    the rung gets its own test instead of the general one being loosened."""
    for term in ("fin", "eye", "scale", "iris"):
        assert not _is_searchable(term), term
        assert _is_anatomy_searchable(term), term


def test_the_anatomy_filter_is_still_a_filter():
    """The relaxation is scoped, not an opening. One- and two-character terms
    are a data error whatever the rung."""
    assert not _is_anatomy_searchable("Da")
    assert not _is_anatomy_searchable("  ")
    assert not _is_anatomy_searchable("12")


def test_search_results_are_unescaped():
    """Europe PMC returns entity-escaped inline markup; left alone it reaches the
    review queue verbatim and breaks matching on italicised gene names."""
    spec = QuerySpec("q", "trait", "trait:x", "x")
    paper = parse_result(
        {"title": "Effects on medaka (&lt;i&gt;Oryzias latipes&lt;/i&gt;).", "doi": "10.1/x"},
        spec,
    )
    assert "&lt;" not in paper.title
    assert "<i>" not in paper.title
    assert "Oryzias latipes" in paper.title


# --- acquisition: section selection ----------------------------------------


def test_reference_lists_are_never_mined():
    """A bibliography co-mentions every gene with every trait."""
    assert not _is_evidence_section("References")
    assert not _is_evidence_section("Acknowledgements")
    assert not _is_evidence_section("Data availability")


def test_unfamiliar_section_titles_are_kept():
    """Papers do not title their sections `Results`. Matching against a list of
    expected names discarded two thirds of every article."""
    assert _is_evidence_section("Genome-wide association studies of ornamental phenotypes")
    assert _is_evidence_section("Population genomic analyses")


def test_jats_parsing_keeps_inline_markup_text():
    xml = """<article><abstract><p>We studied <italic>adcy5</italic> in medaka.</p></abstract>
    <body><sec><title>Results</title><p>The <italic>orochi</italic> strain was darker.</p></sec>
    </body></article>"""
    sections = parse_jats(xml)
    assert "adcy5" in sections["Abstract"]
    # Italics on a gene symbol must not split the sentence around it.
    assert "orochi" in sections["Results"]


# --- extraction ------------------------------------------------------------


def test_relations_co_mention_cannot_support_are_not_proposed():
    """Two traits in one sentence is a sentence about a table, not resemblance;
    two genes in one sentence is an enumeration, not epistasis."""
    for predicate in (
        Predicate.RESEMBLES,
        Predicate.CO_OCCURS_WITH,
        Predicate.EPISTATIC_WITH,
        Predicate.PLEIOTROPIC_WITH,
        Predicate.PUTATIVELY_SAME_AS,
    ):
        assert predicate not in PREDICATE_PREFERENCE, predicate


def test_same_species_gene_pairs_are_not_called_orthologues():
    assert predicate_for(NodeLabel.GENE, NodeLabel.GENE) is None


def test_cross_species_orthology_is_still_proposable():
    assert predicate_for(NodeLabel.GENE, NodeLabel.HUMAN_GENE) is Predicate.ORTHOLOG_OF


def test_weakest_fitting_predicate_wins():
    """Both associated_with_gene and modified_by accept (trait, gene). When
    uncertain, assert less."""
    assert (
        predicate_for(NodeLabel.ORNAMENTAL_TRAIT, NodeLabel.GENE)
        is Predicate.ASSOCIATED_WITH_GENE
    )


def test_level_cue_is_returned_with_the_level():
    """A reviewer can check a phrase and cannot check a bare label."""
    level, cue = detect_level("we generated gene knockout medaka using CRISPR")
    assert level is EvidenceLevel.FUNCTIONAL_VALIDATION
    assert cue


def test_strongest_cue_wins():
    level, _ = detect_level("GWAS followed by genome editing confirmed the variant")
    assert level is EvidenceLevel.FUNCTIONAL_VALIDATION


def test_no_cue_means_unknown_not_a_guess():
    assert detect_level("The fish were maintained at 26 degrees.")[0] is EvidenceLevel.UNKNOWN


def test_negation_is_flagged_not_interpreted(lexicon):
    """The extractor does not resolve negation; it marks the sentence so the
    reviewer reads it."""
    candidates = extract_from_text(
        "paper:x",
        "No association was found between orochi and adcy5 in this cohort.",
        lexicon,
    )
    assert candidates
    assert all(c.negated for c in candidates)


def test_paper_species_defaults_every_sentence_in_it():
    """A corn-snake paper contains sentences naming no species at all. Judged
    alone they are medaka findings, and would enter the graph at full strength."""
    species = detect_paper_species(
        "Conserved mechanisms drive chromatophore differentiation in the corn snake", None
    )
    assert species == "Pantherophis guttatus"
    assert detect_species("melanophores expressed OCA2 and TYR", default=species) == species


def test_a_paper_naming_medaka_stays_medaka():
    assert detect_paper_species("The medaka zic1/zic4 mutant", None) == MEDAKA
    assert detect_paper_species("Gene editing in fish", "including medaka") == MEDAKA


def test_extraction_records_the_quote_verbatim(lexicon):
    sentence = "Loss of exon 8 of adcy5 caused hyper-melanism in orochi."
    candidates = extract_from_text("paper:x", sentence, lexicon)
    assert candidates
    assert all(c.quote == sentence for c in candidates)


def test_list_like_sentences_are_skipped(lexicon):
    """A sentence naming everything says nothing about any pair."""
    crowded = (
        "Candidate genes included adcy5, zic1 in orochi, hikari, black and deme "
        "with hyper-melanism."
    )
    assert extract_from_text("paper:x", crowded, lexicon) == []


# --- resolution ------------------------------------------------------------


def test_gene_symbols_are_proposed_only_beside_known_entities(lexicon):
    beside = propose_new_genes(
        "paper:x", "In medaka, adcy5 and kcnq5a were both downregulated.", lexicon
    )
    assert {p.symbol for p in beside} == {"kcnq5a"}

    isolated = propose_new_genes("paper:x", "The protein abcd1 was purified.", lexicon)
    assert isolated == []


def test_digitless_symbols_are_out_of_reach_and_stay_that_way(lexicon):
    """`pmela`, `tyr` and `kita` are gene symbols with no digit, so nothing
    about their spelling separates them from ordinary words. The rule does not
    find them, and must not be loosened until it can do so without proposing
    every noun in the paper. Asserted so the limitation is visible rather than
    discovered later as a coverage gap."""
    proposals = propose_new_genes(
        "paper:x", "In medaka, adcy5 and pmela were both downregulated.", lexicon
    )
    assert "pmela" not in {p.symbol for p in proposals}


def test_figure_and_chromosome_labels_are_not_genes(lexicon):
    """Medaka has 24 chromosomes; a hand-written list that stopped at chr9 duly
    proposed `chr21` as a gene."""
    proposals = propose_new_genes(
        "paper:x",
        "In medaka, adcy5 expression is shown in fig3 and table2 on chr21, lane4.",
        lexicon,
    )
    assert {p.symbol for p in proposals} == set()


# --- registry --------------------------------------------------------------


def test_paper_identity_prefers_doi():
    """A discovered paper and a curated one must collapse onto one node."""
    assert paper_id_for("10.1/X", "123", "PMC1") == paper_id_for("10.1/x", None, None)


def test_paper_without_identifier_is_refused():
    with pytest.raises(ValueError):
        paper_id_for(None, None, None)


def test_accepted_outranks_every_intermediate_state():
    """Rediscovery must never drag a curated paper back to DISCOVERED."""
    assert _STATE_RANK[PaperState.ACCEPTED] > max(
        _STATE_RANK[s] for s in ACTIONABLE_PAPER_STATES
    )


def test_every_state_has_a_rank():
    assert set(PaperState) == set(_STATE_RANK)
