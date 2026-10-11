# Albino alleles: is "albino" one allele (`i`)?

**Status: research note. Section 8 records what was applied to the seed on
2026-10-11 and what was held back; sections 1 to 7 are the findings and the
original proposal.** Date: 2026-10-11. Method: `trait-literature-search` (Europe PMC
REST, full text where open). Breeder material is `BREEDER_OBSERVATION` only
(ADR 0003).

## Question

The cross query (`genetics.py`, ADR 0006/0007, R-70) models medaka albino as one
allele, `i`, an allele of *tyr*. ADR 0007 lists "Albino allele heterogeneity
(`tyr` vs `oca2`): two albino parents are assumed to carry the same allele" as an
open decision. If medaka "albino" spans several loci, an albino x albino cross can
give pigmented offspring by complementation, and the model predicts 100% albino
for a cross that is not.

**Is the single-allele assumption supported, refuted, or unresolvable?**

## Verdict

**Refuted as a premise about medaka. Unresolvable for any given ornamental
line.**

1. **The premise is false.** At least two non-allelic loci give a whole-body,
   melanophore-lacking albino in the laboratory stocks: the `i` series, which is
   *tyr* (alleles i1, i4, i5/ib, i6), and `i-3`, which is *oca2*
   (fukamachi2004, abstract and full text read). The two are told apart in the
   same paper by tyrosinase staining. Two further genes, *slc45a2* (`b`, skin-only
   albinism) and *hps1* (a wild-derived albino), also produce albino-like fish,
   though neither is a plausible "ornamental albino" candidate on present
   evidence.
2. **No published complementation cross** between medaka albino lines was found
   (see §3). The non-allelism of `i` and `i-3` rests on two different genes being
   cloned from them, on different tyrosinase-staining phenotypes, and on `i-3`
   being carried in a strain alongside other independent loci. It does not rest on
   an `i` x `i-3` F1.
3. **Which locus a trade アルビノ line carries has never been published.** Kon et
   al. 2026 Table 1 names *oca2* for albino without testing it (the albino
   phenotype was not GWAS-analysed). Koga and Hori 1997 say two *tyr* alleles
   (i1, i4) came from "a commercial breeding population". Those point in
   different directions and neither is a genotype of a line sold today.

So the assumption "two albino parents carry the same allele" has no support in
the literature, and ADR 0007's open decision should state the evidence rather
than a bare assumption (proposal in §6).

## 1. Sources searched

Control first: `DOI:"10.1093/molbev/msag021"` returned 1 (Kon et al. 2026), as
required by the skill. All counts are Europe PMC `hitCount` on 2026-10-11.
Syntax caveat: the last row returned 0 and I did not re-run it in a simpler form;
treat it as uninformative.

| query | hits |
|---|---|
| `TITLE:(medaka) AND TITLE:(albino)` | 6 |
| `TITLE_ABS:"medaka" AND TITLE_ABS:"albino"` | 23 |
| `TITLE_ABS:"Oryzias latipes" AND TITLE_ABS:"albino"` | 16 |
| `TITLE:(medaka) AND TITLE:(tyrosinase)` | 8 |
| `TITLE:(medaka) AND TITLE:(oculocutaneous)` | 3 |
| `TITLE:(medaka) AND TITLE:("pink-eyed dilution")` | 1 |
| `TITLE_ABS:(medaka) AND TITLE_ABS:("pink-eyed dilution" OR "p gene" OR oca2)` | 6 |
| `medaka AND (oca2 OR "oculocutaneous albinism")` | 128 (titles screened) |
| `medaka AND "i-3"` | 124 (titles screened; mostly noise) |
| `medaka AND (albino OR albinism) AND ("i-3" OR "i(3)" OR "pink-eyed")` | 34 |
| `TITLE_ABS:medaka AND TITLE_ABS:(albino OR albinism) AND TITLE_ABS:(locus OR loci)` | 9 |
| `medaka AND albino AND (complementation OR allelic)` | 55 (titles screened) |
| `medaka AND albino AND (allelism OR "allelic test" OR "complementation test" OR "compound heterozygote")` | 5 |
| `TITLE:(medaka) AND TITLE:(slc45a2 OR matp OR "oculocutaneous albinism type 4")` | 2 |
| `TITLE:(medaka) AND TITLE:(hermansky OR hps1 OR hps4 OR "lysosome-related")` | 1 |
| `TITLE_ABS:medaka AND TITLE_ABS:("positional cloning") AND TITLE_ABS:(melanophore OR melanin OR pigmentation)` | 6 |
| `(medaka OR "Oryzias latipes") AND ("ruby eye" OR "ruby-eye" OR "grape eye" OR "quasi-albino" OR "pseudo-albino")` | 9 |
| `TITLE_ABS:"Oryzias latipes" AND TITLE_ABS:(albino OR albinism OR "melanin-deficient") AND TITLE_ABS:(strain OR strains OR "ornamental" OR "orange-red")` | 11 |
| `TITLE_ABS:(medaka OR "Oryzias latipes") AND TITLE_ABS:(albino OR albinism) AND PUB_YEAR:[2019 TO 2026]` | 4 |
| `TITLE:(medaka) AND TITLE:(albinism OR albino) AND PUB_YEAR:[1950 TO 1995]` | 2 |
| `TITLE:"Tomita collection"` | 1 |
| `TITLE:medaka AND TITLE:"linkage map"` | 8 |
| `TITLE:(medaka OR "Oryzias latipes") AND TITLE:(tyr OR tyrosinase) AND (CRISPR OR knockout OR "genome editing")` | 0 (uninformative) |

Citation chasing (Europe PMC `MED/{pmid}/citations`, `/references`): forward
citations of fukamachi2004 (37), kelsh2004 (62), hyodotaguchi1997 (22),
kogahori1997 (17), koga1999 (13), iida2004 (13), koga1995 (76) and
yamamoto1969 (6), screened by title.

Full text read: fukamachi2004 (PMC HTML page; Europe PMC refuses the XML for this
publisher), iwanami2022, ohshima2013, kon2026 (Europe PMC XML), plus the
Utsunomiya University press release for iwanami2022 (PDF). **Abstract only:**
koga1995, kogahori1997, koga1999, iida2004, iida2005, inagaki1998, fu2000,
hyodotaguchi1997, tsutsumi2006, watanabe2014, fukamachi2008, fang2018. **Not
read at all:** yamamoto1969 (see §3), kelsh2004, Tomita 1992, Yamamoto's 1975
strain book.

## 2. Loci, genes and experiments

Experiment names are the closed list in `ceilings.EXPERIMENT_CEILINGS`. "Level"
is what ADR 0003 allows for an `associated_with_gene`/`allele_of` claim on the
data the paper shows, not what its prose concludes. All findings are
*Oryzias latipes*.

| locus / allele | gene | paper (PMID) | experiment | level (ADR 0003) | read |
|---|---|---|---|---|---|
| `i` (i1), Tol1 1.9 kb in exon 1 | *tyr* | koga1995 (8552044) | Southern blot and sequencing of the mutant, per the abstract. **Not** mapping or rescue | at most QTL_GWAS_ASSOCIATION on its own (`variant genotyping`); the seed says `positional cloning` / CAUSAL_VARIANT, which the abstract does not support (known, TODO.md) | abstract |
| `i` (i1) | *tyr* | inagaki1998 (9877099) | `transgenic rescue`: *tyr* genomic and cDNA clones into albino i(l) eggs | FUNCTIONAL_VALIDATION | abstract |
| `i` (i1) | *tyr* | tsutsumi2006 (16704459) | `somatic reversion analysis`: Tol-1 precisely excised in black revertants | CAUSAL_VARIANT | abstract (already in seed) |
| `i` (i1) | *tyr* | watanabe2014 (24905071) | germline reversion of the Tol1 insertion in an albino laboratory strain, 0.4% per gamete | CAUSAL_VARIANT (no exact row in the ceiling table) | abstract |
| i4, Tol1 4.7 kb in exon 5 ("quasi-albino", red-wine eyes) | *tyr* | kogahori1997 (9428004) | sequencing of cloned alleles (review) | OBSERVATIONAL | abstract |
| i5 = i(b), Tol2 4.7 kb in the promoter, weak albino | *tyr* | iida2004 (15016305) | cloning and sequencing, expression decreased | QTL_GWAS_ASSOCIATION on its own | abstract |
| i(b) | *tyr* | iida2005 (16162178) | reversion with Tol2 excision | CAUSAL_VARIANT | abstract |
| i6, 245 bp deletion across the intron 2 acceptor | *tyr* | koga1999 (10454293) | sequence comparison; "likely" | QTL_GWAS_ASSOCIATION | abstract |
| **`i-3`**, 4 bp deletion in exon 13 | ***oca2*** | fukamachi2004 (15579703) | `positional cloning`: LG4, 17 recombinants in 1686 meioses, one BAC of ~220 kb, frameshift in the candidate | see below | **full text** |
| `b` (bg8), promoter change; albinism **in the skin only** | *slc45a2* | fukamachi2008 (18245373) | `transgenic rescue` of eye and skin | FUNCTIONAL_VALIDATION | abstract |
| unnamed wild-derived albino, frameshift, LG15 | *hps1* | iwanami2022 (35944207) | `positional cloning` and `genome editing` (13 bp deletion line) | FUNCTIONAL_VALIDATION | **full text** |
| `i-3` fish edited | *oca2* | lischik2019 (30845151) | genome editing in **wild-type** Cab fish | FUNCTIONAL_VALIDATION for *oca2* → melanogenesis only; own-subject rule keeps it off albino | in seed, full text read earlier |
| tyr knockout in orange-red medaka | *tyr* | fang2018 (29873175) | `genome editing` | wild-type background; own-subject rule | abstract |

**fukamachi2004's level.** Under ADR 0003 the interval is one BAC with six
human-homolog genes named in the paper (*CYFIP1*, *NIPA2*, *GABRG3*, *OCA2*,
*HERC2*, *PEG10*), which is more than five, so `FINE_MAPPING` is out. The
frameshift was found in *oca2* because the phenotype suggested it ("a very likely
candidate gene"), and the paper does not report genotyping F2 fish for the
deletion or any rescue. ADR 0003's rule that "a candidate variant found inside
that interval ... stays" at QTL_GWAS_ASSOCIATION points there. `positional
cloning` would allow CAUSAL_VARIANT, so this is a call for the data owner. In
either reading **it is a different gene from *tyr***, which is all this note
needs.

Verbatim findings:

- fukamachi2004: "The i-3 mutation is a four-base deletion in exon 13, which
  causes a frameshift and truncation of the protein."
- fukamachi2004: "The i-3 locus was mapped to medaka linkage group 4 (LG4)".
- fukamachi2004: "Amelanotic melanophores in the i-1 fry were not stained after
  incubation, indicating a complete lack of tyrosinase."
- fukamachi2004, of i-3 fry: "indicating the presence of active tyrosinase in
  these cells".
- fukamachi2004 on phenotype: "almost indistinguishable from the i -locus
  mutants". Two genes, one look.
- inagaki1998: "the i locus of the medaka genome can be concluded to encode the
  tyrosinase gene."
- kogahori1997: "Both i1 and i4 are alleles that were found in a commercial
  breeding population."
- koga1999: "Three mutant alleles (i1, i4, and i5) of the tyrosinase gene in the i
  locus".
- iwanami2022: "confirming that hps1 mutation was responsible for the observed
  albino medaka."
- ohshima2013: "the b , i-3 , lf , and gu loci are independent on chromosomes".
- ohshima2013: "The i-3 locus encodes the oculocutaneous albinism type 2 (Oca2)
  protein".
- fukamachi2008: "There is a unique OCA4 mutant in medaka (b) that exhibits
  albinism only in the skin".

**Interpretation.** In the medaka literature "i-N" is not one locus. `i`, i1 to
i6 and `ib` are alleles of *tyr*. `i-3` is a separate locus on LG4 with a different
gene. The names look alike and the seed already trips on it ("Fukamachi et al.
2004" in Kon's Table 1 is the *i-3* paper, not an `i` paper). Nobody has
published where *tyr* sits relative to `i-3`; I did not retrieve its linkage
group, so the "different locus" claim rests on the two cloned genes being
different, not on a map.

hyodotaguchi1997 (9431801), abstract only, rescued two albino strains with a mouse
*tyr* transgene and concludes "the i3-locus [lies] upstream and the b-locus
downstream of the tyrosinase locus i1". It treats `i1` and `i3` as separate loci.
It says nothing about a cross between them in the abstract.

## 3. Complementation evidence

**None found** for medaka albino lines. Specifically:

- No retrieved abstract or full text reports an `i` x `i-3` (or any
  albino x albino) cross.
- The one paper that looks as though it should is **yamamoto1969**, Genetics
  62:797, "Inheritance of Albinism in the Medaka, *Oryzias latipes*, with Special
  Reference to Gene Interaction" (PMID 17248459, PMC1212316). **I could not read
  it.** The PMC article page carries no text, and its PDF sits behind a browser
  check that I did not bypass. Europe PMC has no abstract. Its title says more
  than one gene is involved and that they interact. It is the first paper to
  read, and it may decide this question.
- kelsh2004 (Tomita collection, 15210190) describes the embryonic phenotypes of
  40+ mutants and may list allelism groups. Not open; unread.

What the retrieved papers do support is the *consequence* of non-allelism, by
Mendelian reasoning rather than by an observed cross: if `i` (*tyr*) and `i-3`
(*oca2*) are recessive loss-of-function mutations in different genes, an
i/i; I3/I3 x I/I; i-3/i-3 cross gives I/i; I3/i-3 fish with normal pigment.
**That prediction was not found tested.**

## 4. Breeder and trade evidence (BREEDER_OBSERVATION)

- JMA manual 5, §3.3.1 (local `scripts/vocab/raw/jma5.txt`, lines 1034-1070):
  albino is defined by missing melanin synthesis and a red (blood-colour) eye;
  body colour is limited to white, pink, yellow, orange. The manual groups three
  types quoted from Iwamatsu (全訂増補版メダカ学全書): a "完全なアルビノ表現型",
  a "疑似アルビノ表現型" (red-wine-coloured eye, also called ブドウ眼 /
  ルビーアイ), and the see-through type. §3.9.1 adds "黒色素の生成が制限された，
  アルビノの仲間です" for the change-colour eye.
- It states **nothing** about the genetics of trade albino lines, about albino x
  albino crosses, or about reversion to pigmented fry. Nothing in
  `data/seed/01-sources-breeder.yaml` or the other local breeder text
  (`hz_notes.txt`, `aqualab_yougo.txt`, `dc.html`) does either. The strain list
  only names albino as a parent of other lines (王妃, 龍の瞳).
- I ran two Japanese web searches for reports of albino x albino giving
  pigmented fry. Both returned nothing relevant. This is an absence in a small
  search, not evidence of absence.
- One caution on method. A `WebFetch` summary of the Utsunomiya press release
  claimed it reported an *oca2* mutation. Reading the PDF myself, it reports
  *hps1* in a wild-derived stock (a 14-base deletion, per the release) and makes
  no *oca2* claim. The summary was wrong and is not used.

**Interpretation, not asserted.** The JMA's three eye types suggest the trade
already sees more than one kind of albino (full vs trace melanin). kogahori1997's i4
is a *tyr* allele with "red-wine-coloured eyes" and "quasi-albino" skin, and the
trade's ルビーアイ / ブドウ眼 is described in the same words. That is a
resemblance of descriptions. It is not a recorded identity, and I would not write
it as a claim. It does show that the trade's one-word アルビノ can already hide
alleles of one gene that look different.

## 5. What the ontology asserts now

Read from `data/seed/`, `TODO.md`, `data/dossier/albino.md`:

- albino → *tyr* (CAUSAL_VARIANT, koga1995 `positional cloning`; tsutsumi2006
  reversion at FUNCTIONAL_VALIDATION). koga1995's full text is unread and its
  abstract reads as Southern blot, not cloning. The albino claim rests on
  tsutsumi2006 and not on koga1995.
- albino → *oca2*: UNKNOWN, one UNKNOWN-level item from kon2026 Table 1
  with `BROKEN_CITATION`. The citation resolves to fukamachi2004 (cited by
  lischik2019, reference 27). It is not in the seed as a paper.
- `i locus: i (albino)` `allele_of` *tyr*, and `albino requires_allele i locus: i
  (albino)` INFERRED, with the interpretation "Whether an ornamental albino
  carries i or another albino locus (oca2) is not known".
- The i allele's own description already says "two albino strains crossed
  together may complement each other".
- genetics.py `albino_allele` open decision: "two albino parents are assumed to
  carry the same allele".
- Nothing records `i-3`, *hps1*, or *slc45a2*'s albino alleles, and nothing
  records that `i-3` is a locus distinct from `i`.

The seed has therefore already named the risk. It has not recorded the evidence
that the risk is real.

## 6. Proposal (not applied)

Seed changes, in the order I would make them. Quotes are the abstract sentences
above.

1. **Add paper `fukamachi2004`**: PMID 15579703, doi 10.1534/genetics.104.030494,
   PMCID PMC1448775, "Conserved function of medaka pink-eyed dilution in melanin
   synthesis and its divergent transcriptional regulation in gonads among
   vertebrates", Genetics 2004. It resolves the `BROKEN_CITATION` on albino →
   *oca2*. Say in its note that it is the *i-3* paper and not an `i` paper.
2. **Add loci/alleles**: Locus "i-3 locus" (LG4, per fukamachi2004; the assembly
   chromosome number has not been checked); GeneticVariant "i-3 locus: i3 (albino)"
   (loss of function, symbol `i3`) and "i-3 locus: I3 (wild type)".
   - `allele_of` i3 → *oca2*: `positional cloning`, **QTL_GWAS_ASSOCIATION** (see §2;
     owner may choose CAUSAL_VARIANT), species *Oryzias latipes*, finding "The i-3
     mutation is a four-base deletion in exon 13, which causes a frameshift and
     truncation of the protein."
   - `allele_of` I3 → *oca2*: INFERRED, as the other wild-type alleles.
3. **Add papers and evidence for `i` → *tyr* that are stronger than koga1995**:
   inagaki1998 (9877099, doi 10.1111/j.1600-0749.1998.tb00737.x), `transgenic
   rescue`, FUNCTIONAL_VALIDATION, finding "the i locus of the medaka genome can be
   concluded to encode the tyrosinase gene." On the same claims add koga1999 (i6) and
   iida2004 (ib) at QTL_GWAS_ASSOCIATION, and iida2005 (ib reversion) at
   CAUSAL_VARIANT if the owner wants the alleles listed. Lower koga1995's
   `experiment_type` to `variant genotyping` (QTL_GWAS_ASSOCIATION) until the full
   text is read. That settles its ceiling question without
   deciding it.
4. **Replace the `albino requires_allele i` interpretation** with one that states
   the finding: "Two non-allelic albino loci are documented in medaka (`i`, *tyr*;
   `i-3`, *oca2*; fukamachi2004). Which one an ornamental albino carries has not
   been published." Keep the claim INFERRED.
5. **Optionally** add *hps1* and *slc45a2* albino alleles as laboratory-mutant
   entities, with no ornamental trait attached, so the dossier lists the loci
   instead of hiding them. *hps1*: iwanami2022, genome editing, FUNCTIONAL_VALIDATION.
   Not needed for the cross query.
6. **Do not** link trade ルビーアイ to i4 or to any locus (see §4).
7. Update `data/dossier/albino.md` open questions and `TODO.md` ("Fukamachi et
   al. 2004 resolves to an i-3 cloning" is now a seed entry). Add **yamamoto1969**
   as the first paper to read, and say why.

`genetics.py` behaviour, from least to most work. Only 3 or 4 is needed to make
the current prediction honest.

1. **Reword `albino_allele`** (open decision text only): "Two non-allelic albino
   loci are documented (`i`/*tyr*, `i-3`/*oca2*). Which one a line carries is
   unpublished; two albino parents are assumed to carry the same allele, and if
   they do not, their offspring are pigmented." Costs nothing, changes no output
   number, and states the evidence.
2. **Refuse the cases the assumption decides**: add a refusal code
   `albino_locus_ambiguous` to `REFUSALS`, raised for the trait `albino` when
   both parents are albino *by phenotype* or when one is albino and the other is
   stated to carry `i`. Other traits in the cross are still predicted, as with
   `multilocus`. The result says "albino x albino: 100% albino if both carry the
   same locus, 0% if they carry different loci; not recorded which".
3. **Model two loci** (2. above) with an OR rule: albino expressed iff `i/i` **or**
   `i3/i3`. `requires_allele` is AND today, so this needs either a group marker on
   `requires_allele` claims or two traits, "albino (tyr)" and "albino (oca2)",
   both absorbed by an `albino` display parent.
4. **Use the existing hypothesis machinery**: `hypotheses()` and
   `cross_from_phenotypes()` already return a range over unresolved genotypes. An
   albino parent known only by phenotype becomes the hypotheses {i/i, i3/i3},
   each at no stated prior, so albino x albino returns albino at 0% to 100% instead
   of a single number. That reuses `RangeResult` and invents no prior.

I recommend 1 now and 4 when the data owner agrees to add the second locus. The
`masks` claims (albino hides blue and panda) hold for either locus, as both lose
melanophore pigment, so they do not change.

## 7. What would change this verdict

- **yamamoto1969**, if it reports albino x albino crosses (it may settle the
  *i*/*i-3* question directly, in 1969 stocks).
- A genotyped ornamental albino line (a *tyr* and *oca2* sequence of strains such
  as those Kon et al. hold). A single such result would turn "unresolvable for a
  given line" into a fact for that line.
- A reported albino x albino cross from the hobby with a stated parentage.
- The koga1995 and fukamachi2004 supplementary material, which I did not read.

## 8. Applied to the seed, and held back (2026-10-11)

**Applied** (proposal items 1, 3, 4; rulings R-82 to R-89 in `.harness/rulings.md`):

- Papers `fukamachi2004` (PMID 15579703, the i-3 paper, full text read) and
  `inagaki1998` (PMID 9877099, abstract only) added to `00-papers.yaml`. Both
  identifiers were checked against Europe PMC on 2026-10-11.
- inagaki1998 added as `transgenic rescue`, FUNCTIONAL_VALIDATION, on `albino ->
  tyr`, on `i locus: i (albino) allele_of tyr`, and on `tyr participates_in
  melanogenesis`.
- koga1995 is now `variant genotyping`, QTL_GWAS_ASSOCIATION, on all four claims
  it supports (the abstract reads as Southern blot and sequencing). The
  `KNOWN_CEILING_VIOLATIONS` entry for `tyr participates_in melanogenesis` is
  gone and `tests/test_ceilings.py` now pins the list empty.
- The `albino requires_allele i` interpretation now names the two documented loci
  and says which one an ornamental albino carries is unpublished.
- `albino -> oca2` keeps its UNKNOWN level and `BROKEN_CITATION`. fukamachi2004 is
  *not* attached to it: the fish are the i-3 mutant, and ADR 0003's own-subject
  rule defines albino here as the i mutant. The claim's interpretation and the
  oca2 entity now say what the citation probably is.

**Held back: the i-3 alleles (proposal item 2).** Adding `i-3 locus: i3 (albino)`
and `I3 (wild type)` as `allele_of oca2` claims makes `genetics.py` read oca2 as
a locus whose symbols `i3` and `I3` a genotype can use. Nothing requires them,
so the query then answers a same-locus cross wrongly and silently. Measured on a
copy of the seed with the block below added:

    cross --mother "i3/i3" --father "i3/i3"   ->   "none of the modelled traits"

Both parents are albino (i-3 is a whole-body albino) and every offspring is
albino, so the query would say the opposite of the truth, with no assumption
raised for it. `cross --symbols` would also grow `oca2: i3, I3`. Before the alleles
go in, `genetics.py` has to treat albino as `i/i` **or** `i3/i3` (section 6,
options 3 or 4), which is the owner's work in progress. With that in place the
block below is ready; it passes `validate` (38 papers, 197 entities, 253 claims)
and needs `tests/test_graph_integration.py` bumped to 197 and 253.

**The level, as decided (R-82).** `allele_of i3 -> oca2` is `positional cloning` at
**QTL_GWAS_ASSOCIATION**. The paper's own text, read in full: 17 recombinations in
1686 meioses (843 F2) between i-3 and the nearest EST; chromosome walking to BAC
129C11 (about 220 kb), which holds the entire candidate region because both
ends recombined with the locus; six human-homolog genes in it (CYFIP1, NIPA2,
GABRG3, OCA2, HERC2, PEG10), over the five FINE_MAPPING allows; oca2 chosen as
"a very likely candidate gene" from the phenotype; the deletion found by
sequencing the candidate's cDNA from i-3, Hd-rR and HNI. No F2 fish are
genotyped for the deletion and nothing is rescued. A candidate variant found in
an interval that was never narrowed stays at QTL_GWAS_ASSOCIATION (ADR 0003), and
the authors' "concluded" is wording, not data (rule 2). CAUSAL_VARIANT would
need the deletion mapped in the crosses or reverted; FUNCTIONAL_VALIDATION would
need an i-3 rescue. Lowering to OBSERVATIONAL was considered and rejected: the
paper did map the locus by recombination to the interval.

Ready-to-apply block, appended to `13-entities-genetics.yaml`:

```yaml
  - label: GeneticVariant
    name: "i-3 locus: I3 (wild type)"
    symbol: I3
    variant_type: wild type
    description: >-
      Wild-type allele at i-3 (oca2). The symbol I3 is ours, a handle for the
      wild type of the literature's i-3; no source writes it.

  - label: GeneticVariant
    name: "i-3 locus: i3 (albino)"
    symbol: i3
    variant_type: loss of function
    description: >-
      The albino allele of the i-3 mutant, a four-base deletion in exon 13 of
      oca2 that frameshifts and truncates the protein (fukamachi2004). i-3 is on
      linkage group 4 and is a different locus from i (tyrosinase). The symbol
      i3 is ours for the literature's i-3.
```

and to `24-claims-inheritance.yaml`:

```yaml
  - predicate: allele_of
    subject: {label: GeneticVariant, name: "i-3 locus: i3 (albino)"}
    object: {label: Gene, name: oca2}
    interpretation: >-
      QTL_GWAS_ASSOCIATION, not CAUSAL_VARIANT, under ADR 0003 (R-82). The paper
      mapped i-3 by 17 recombinations in 1686 meioses to one BAC of about 220 kb
      that holds six human-homolog genes, more than the five FINE_MAPPING
      allows. It chose oca2 from those six because the phenotype suggested it
      and found the four-base deletion by sequencing it. It reports no
      genotyping of the F2 for the deletion and no rescue, so the deletion is a
      candidate variant inside an interval that was never narrowed, which ADR
      0003 keeps at QTL_GWAS_ASSOCIATION. The authors' word is "concluded"; the
      level follows the data, not the wording (ADR 0003 rule 2).
    evidence:
      - paper: fukamachi2004
        experiment_type: positional cloning
        level: QTL_GWAS_ASSOCIATION
        species: Oryzias latipes
        section: Abstract
        finding: >-
          The i-3 mutation is a four-base deletion in exon 13, which causes a
          frameshift and truncation of the protein.

  - predicate: allele_of
    subject: {label: GeneticVariant, name: "i-3 locus: I3 (wild type)"}
    object: {label: Gene, name: oca2}
    interpretation: >-
      A wild-type allele belongs to its locus by definition; no source writes
      the sentence, so it is ours. fukamachi2004 shows i3 is a mutant allele of
      oca2, so the wild-type allele it is a mutant of, I3, is an allele of the
      same gene.
    evidence:
      - paper: fukamachi2004
        experiment_type: inference
        level: INFERRED
        species: Oryzias latipes
        section: Abstract
        finding: >-
          The i-3 mutation is a four-base deletion in exon 13, which causes a
          frameshift and truncation of the protein.
```

**Not done: dossiers.** `data/dossier/albino.md` is rendered from the graph
(`cli dossier`, `dossier-all`), which needs Neo4j; the repo has no database-free
path for it. The seed edits change the albino dossier's tyr evidence (koga1995
lowered, inagaki1998 added) and its `requires_allele` text. Regenerate after
the next `cli load`.
