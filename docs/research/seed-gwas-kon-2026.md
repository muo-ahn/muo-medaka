# Seed GWAS candidate

**Confidence: VERY HIGH (~97%).** This is almost certainly the intended paper. It is the only
2025–2026 genome-wide association study on ornamental medaka trait genetics that exists, it defines
an explicit closed set of ornamental traits (34 phenotypes), and it runs GWAS across them. Every
gene named in the task brief as a hint (`adcy5`, `kcnq5a`, `zic1/zic4`, `slc45a2`, `slc24a5`,
Hikari / Daruma / Swallow / Panda) appears in it. The brief's hint list reads as if drawn from this
paper's abstract and Table 3.

| Field | Value |
|---|---|
| Title | Genomic consequences of domestication and the diversification of body coloration and morphology in ornamental medaka strains |
| Authors | Tetsuo Kon, Rui Tang, Koto Kon-Nanjo, Soma Tomihara, Soichiro Fushiki, Wakana Fujii, Mifuyu Sera, Yusuke Takehana, Hideki Noguchi, Atsushi Toyoda, Kiyoshi Naruse, Yoshihiro Omori |
| Year | 2026 |
| Journal | Molecular Biology and Evolution |
| Volume / article | 43(2): msag021 |
| DOI | `10.1093/molbev/msag021` |
| PMID | `41612673` |
| PMCID | `PMC12915790` |
| Open access | Yes — CC BY-NC 4.0 |
| URL (publisher) | https://academic.oup.com/mbe/article/43/2/msag021/8444924 |
| URL (free full text) | https://pmc.ncbi.nlm.nih.gov/articles/PMC12915790/ |
| Code / data | https://github.com/ironman-tetsuo/ornamental_medaka_wgs (analysis pipeline only; no phenotype table in README) |

### Abstract (verbatim, from JATS full text)

> Ornamental medaka strains derived from wild Japanese medaka (*Oryzias latipes* species complex)
> are bred worldwide. Over 200 years of selective breeding have produced over 700 strains with a
> wide variety of phenotypes, including diverse body coloration, scales, eyeball morphology, and
> fin and body shapes. In this study, we first identified and described 34 phenotypes in ornamental
> medaka strains. To understand the genomic basis of this phenotypic diversity and the
> domestication process, we performed whole-genome sequencing on 181 individuals of 86 ornamental
> Japanese medaka strains. Population genomic analyses revealed that modern ornamental medaka
> strains are genetically closer to the wild Southern Japan population of the Kansai–Setouchi
> regions, suggesting the origin of ornamental strains. In addition, the gene loci poc1a, tyr,
> nme2a, and gabrr2b have undergone selection during domestication. We performed genome-wide
> association studies analysis for 29 phenotypes observed in ornamental medaka strains and
> identified strong candidate genes for some phenotypes, including kcnq5a for hirenaga and swallow,
> bmp5 for deme, adcy5 for orochi, and kitlga for aurora, respectively. We found that loss of exon 8
> of adcy5 caused melanism, a dark body color phenotype, in medaka, providing a molecular insight
> into this phenomenon in vertebrates and human familial dyskinesia. In addition, we uncovered the
> predominant candidate peaks of genome-wide association studies, including a total of 3,328 genes
> associated with 26 phenotypes. Our findings highlight the potential of population genomics to
> explore genotype-phenotype correlations and the genomic basis of body coloration and
> morphogenesis in medaka.

### Key design numbers (from the paper, not inferred)

- 34 phenotypes **described** (Table 1); GWAS run on **29**; candidate regions reported for **26** (Table 2 lists 26 rows).
- 181 individuals, 86 ornamental strains, ~17 M variant sites.
- 3,328 genes total across the 26 candidate intervals.
- Skin RNA-seq on 8 strains: orochi, miyuki, white, gold, aurora rame, yokihi, himedaka (yellow), kiyosu (wild type).

### Why this and not something else

The provenance chain is clean and mutually corroborating: PubMed record, OUP landing page, PMC full
text, and the Europe PMC JATS XML all return the same authors, DOI and tables. The trait→gene table
below was extracted from the **publisher's own XML markup of Table 1, Table 2 and Table 3**, not
from prose summarization, so the chromosome and interval values are the authors' own.

---

# Runner-up candidates

I searched PubMed/Europe PMC/bioRxiv/Google-Scholar-style venues with the query variations in the
brief. No competing ornamental-medaka GWAS exists. These are the nearest neighbours, listed so the
ontology project can rule them out deliberately rather than by omission.

| Paper | Why it is NOT the seed | DOI |
|---|---|---|
| Zhang W. et al. 2022, "The genetic architecture of phenotypic diversity in the Betta fish (*Betta splendens*)", *Sci Adv* 8:eabm4955 | Correct study design (ornamental-fish domestication GWAS) but wrong species. Cited by the seed paper as methodological precedent. | `10.1126/sciadv.abm4955` |
| "Empowering medaka fish biology with versatile genomic resources in MedakaBase", bioRxiv 2025 | Database/resource paper, not a GWAS; no ornamental trait definitions. | preprint — `10.1101/2025.05.13.653297` |
| "Complete sequencing of medaka genomes reveals the architecture of centromeric satellites, giant mobile elements, and sex chromosomes", *Genome Research* 36(8):1696, 2026 | Reference-genome assembly of 3 **inbred lab** strains (Hd-rR, HNI, HSOK). No ornamental traits, no GWAS. | UNVERIFIED (not resolved via CrossRef) |
| "Medaka: a novel model for analyzing genome–environment interactions", *Trends in Genetics* 2026 (PMID 41735098) | Review, not primary GWAS. | `10.1016/j.tig.2025.10.011` — **UNVERIFIED**, inferred from ScienceDirect PII only; do not cite without checking |
| Goldfish (*Carassius auratus*) ornamental GWAS work | Wrong species; referenced only as background in the seed paper's intro. | not retrieved |

---

# Trait → locus table from the seed paper

Source: **Table 2** (GWAS candidate regions) joined with **Table 1** (phenotype definitions) and
**Table 3** (focused candidate genes), all extracted from the JATS XML.

### Evidence-level key (my labelling of the authors' own claims)

| Level | Meaning |
|---|---|
| **L4 functionally validated** | Variant recreated by genome editing and phenocopied |
| **L3 candidate variant** | GWAS peak + a specific co-segregating sequence variant identified in the candidate gene |
| **L2 named candidate** | GWAS peak + a named gene in the interval, argued from GO term / homology only |
| **L1 interval only** | Significant GWAS peak, no gene nominated (Table 2 shows "…") |
| **L0 no peak** | GWAS run, no significant association |
| **L–** | Not GWAS-analysed in this study |

### Body color

| Trait | Japanese name | Phenotype described (Table 1, condensed) | Chr | Interval (bp) | n mutants | Best P | # genes | Candidate gene(s) | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| orochi | オロチ† | Blackness greater than *black*; increased melanophores. Table 1 hereditary mode: "Multilocus" | 21 | 4,494,031–7,110,016 | 16 | 6.28E−25 | 70 | **adcy5** | **L4** | Homozygous 56-bp deletion spanning the intron7/exon8 boundary in 16/18 (89%) orochi. RT-PCR: transcript lacks exon 8, no frameshift after exon 9. Genome-edited `adcy5^delex8` founders showed significantly increased black body color → "deletion of adcy5 exon8 caused hyper-melanism, similar to orochi phenotype." Deletion maps to the C1b-α2 domain (human ADCY5 690–696 aa) |
| aurora | オーロラ† | Mild iridophore depletion; opercular iridophore loss makes red gills visible; scales shift green/red/blue/yellow | 6 | 35,026–6,793,288 | 23 | 7.32E−17 | 175 | **kitlga** | **L3** | Frameshift at Chr6:2,485,888 → premature stop, 164-aa truncated protein vs 233-aa wild type. Authors: "kitlga is a strong candidate gene." Caveat they state: "we cannot rule out the possibility that the aurora phenotype results from mutations in another gene located near kitlga" |
| sanshoku | 三色† | Body partly white with orange **and** black spots | 14 | 22,279,553–30,567,935 | 4 | 6.48E−61 | 248 | **uvrag** | **L2** | Argued from mammalian UVRAG role in melanogenesis/autophagy and zebrafish uvrag-depletion phenotype. Only 4 mutants — very small n despite extreme P |
| kurobuchi | 黒斑† | Body color pattern with black spots; superset including sanshoku and kuroaka | 14 | 22,305,698–30,081,129 | 11 | 8.50E−09 | 230 | **uvrag** | **L2** | Same locus as sanshoku |
| blackrim | — | Dense melanophores around scales, appearing as a black mesh | 12 | 9,763,282–15,596,885 | 14 | 3.33E−26 | 230 | **slc45a2** | **L2** | Same chr12 region as yellow/YWKo |
| yellow (himedaka) | ヒメダカ / 黄† | Loss of normal melanophores from body surface. "The body color of the traditional ornamental medaka, himedaka" | 12 | 8,533,986–11,509,087 | 77 | 3.19E−06 | 100 | **slc45a2** | **L2** (recovers known gene) | Table 1 prior locus: slc45a2 (Fukamachi et al. 2001), recessive. Weakest P among body-color hits |
| YWKo | — | Body color without melanophores; umbrella class covering yellow, white, or kouhaku | 12 | 9,523,726–11,920,633 | 100 | 2.00E−11 | 61 | **slc45a2** | **L2** | Composite/aggregated class, not a strain name — important for ontology modelling |
| black | 黒† | Increased blackness vs wild type; increased melanophores | 21 | 7,325,809–8,858,152 | 40 | 1.53E−12 | 35 | **atp6ap2** | **L2** | Nominated via melanocyte-differentiation requirement (Tatarakis et al. 2021). Adjacent to but distinct from the orochi interval on chr21 |
| akabuchi | 赤斑† | Body color pattern with red spots; superset including sanshoku and kouhaku | 4 | 15,616,568–19,691,410 | 19 | 1.23E−10 | 106 | **foxd3** | **L2** | |
| panda | パンダ† | Decreased iridophore throughout body **including** iris and peritoneum | 3 | 12,944,237–16,837,085 | 16 | 1.12E−16 | 113 | **slc24a5** | **L2, explicitly hedged** | Authors call the chr3 peak "unexpected". They state slc24a5 "may not fully explain the panda phenotype" and conclude "a mutation in a functionally unknown gene within the GWAS interval on chromosome 3 … causes the panda phenotype". They **explicitly reject** the prior pnp4a attribution: no coding mutations in pnp4a in panda individuals. See Gaps |
| white | 白† | White body; loss of both normal xanthophores and melanophores | 12 | 3,865,760–7,668,732 | 30 | 1.76E−12 | 72 | — | **L1** | Table 1 prior loci: slc45a2 (Fukamachi 2001), r locus (Aida 1921); recessive |
| blue | 青† | Loss of normal xanthophores from body surface | 4 | 23,872,478–27,071,814 | 33 | 2.43E−11 | 108 | — | **L1** | Table 1 prior locus: r locus (Aida 1921); recessive |
| miyuki | 幹之† | Ectopic iridophore on dorsal side; reduction of melanophores and xanthophores. Table 1 mode: "Multilocus" | 19 | 9,832,109–10,803,405 | 34 | 3.67E−10 | 30 | — | **L1** | Discussion also groups miyuki with the "no obvious candidate peak" set — treat the chr19 hit as weak |
| rame | ラメ† | Increased number of iridophore-expressing silver-colored scales | 20 | 12,073,015–13,138,676 | 47 | 1.33E−09 | 38 | — | **L1** | Distinct interval from hikari despite sharing chr20 |
| kouhaku | 紅白† | Body surface partly white with orange spots | 3 | 13,960,030–15,862,381 | 19 | 3.61E−11 | 44 | — | **L1** | Interval overlaps the panda chr3 interval |
| kuroaka | 黒赤† | Body surface partly orange with some black spots formed by melanophores | 8 | 5,006,576–6,657,821 | 7 | 8.96E−16 | 113 | — | **L1** | |
| fukumaku | 腹膜† | Blue silver-colored peritoneum | 13 | 25,328,892–33,584,184 | 4 | 5.71E−59 | 198 | — | **L1** | n = 4 only |
| yokihi | 楊貴妃† | Increased redness (orange) vs yellow medaka; enhanced xanthophores, loss of normal melanophores | — | — | — | — | — | — | **L0** | "we did not observe any obvious peaks in the Manhattan plot for the yokihi, gold, and toumeirin phenotypes"; authors attribute this to polygenicity. RNA-seq: *csf1ra* upregulated in yokihi skin |
| gold | — | Brown or wild-type-like; brighter than wild type, decreased blackness | — | — | — | — | — | — | **L0** | RNA-seq: *csf1ra* higher in gold and white |
| toumeirin | 透明鱗† | Decreased iridophore throughout body **excluding** iris and peritoneum; near-complete loss in scales | — | — | — | — | — | — | **L0** | Contrast with panda (which *includes* iris/peritoneum) — a clean ontological discriminator |
| albino | アルビノ† | Lack of melanophores throughout body; yellow body, pink pupil | — | — | — | — | — | *oca2* | **L–** | Prior locus per Table 1: "oca2 (Fukamachi et al. 2004)", recessive. Not GWAS-analysed here. **Citation problem — see Gaps** |
| nijikin | 虹金† | Ectopic iridophore expression throughout the muscle | — | — | — | — | — | — | **L–** | Not GWAS-analysed |

### Body shape

| Trait | Japanese name | Phenotype described | Chr | Interval (bp) | n | Best P | # genes | Candidate gene(s) | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| hikari | 光† | Dorsal side becomes ventral; dorsal fin shaped like a pelvic fin; caudal fin diamond-shaped; ectopic iridophore on back, dorsal side shines silver | 20 | 18,018,142–19,345,542 | 35 | 1.84E−21 | 40 | **zic1/4** | **L3 (replication of an established causal locus)** | Table 1 prior locus: zic1/4 (Moriyama et al. 2012), recessive. The seed paper's own contribution: GWAS peak on chr20 **plus** confirmation of the insertion in the zic1/4 locus in **all 35** hikari individuals. Causality itself was established by the earlier Da literature, not here |
| daruma | ダルマ† | Short body axis | 4 | 775,070–6,879,644 | 6 | 9.61E−38 | 211 | — (none nominated) | **L1** | Table 1 prior locus: "wnt4b (Inohaya et al. 2010)", mode "Recessive, Incomplete dominant (dorsalfin)". **The paper's own data argue against wnt4b**: wnt4b is on chr16, the peak is on chr4, and the authors write that ≥2 daruma individuals carried the reported wnt4b mutation "however, this does not appear to be a major mutation causing the daruma phenotype." They conclude "unknown molecular mechanisms may be responsible". The wnt4b precedent is the medaka *fused centrum* (*fsc*) mutant, a *similar* phenotype — not daruma itself |
| handaruma | 半ダルマ† | Mildly short body axis; longer than daruma, shorter than wild type | — | — | — | — | — | — | **L–** | Not GWAS-analysed (only 5 of 7 shape/eye phenotypes were) |

### Fin morphology

| Trait | Japanese name | Phenotype described | Chr | Interval (bp) | n | Best P | # genes | Candidate gene(s) | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| hirenaga | ヒレ長† | **All five** types of fin rays longer than wild type; fin membranes elongate partially | 15 | 7,548,155–12,116,545 | 19 | 1.19E−31 | 92 | **kcnq5a** | **L3** | Top SNV Chr15:11,377,038. No hirenaga-specific nonsense/frameshift/missense variant found in the kcnq5a coding region; instead a hirenaga-specific large deletion in **intron 1** (Chr15:11,147,312–11,148,989). Authors: "These genetic variants may affect kcnq5a expression" — regulatory hypothesis, not demonstrated |
| swallow | スワロー† | **Some** fin rays longer than wild type; fin membranes do **not** elongate | 15 | 7,321,021–11,762,845 | 12 | 6.95E−33 | 93 | **kcnq5a** | **L2/L3** | Same locus as hirenaga, overlapping interval; the paper treats these as allelic variants at kcnq5a. Membrane involvement is the discriminator from hirenaga |
| longfin | — | **Six** fins (all except the caudal fin) longer than wild type | 7 | 9,865,513–17,095,925 | 10 | 5.19E−26 | 318 | **kcna10, kcna3, kcnd3** | **L2** | Another potassium-channel cluster — independent of the chr15 kcnq5a locus. Largest gene count of any interval |
| reallongfin | — | **All** fins longer; not only fin rays but also fin **membranes** elongated | 17 | 26,828,411–31,743,217 | 8 | 1.10E−33 | 197 | **and2** | **L2** | *and2* = actinodin 2, an actinotrichia protein (Zhang J. et al. 2010, *Nature*) |
| nodorsalfin | — | Dorsal fin loss | — | — | — | — | — | *lmbr1* | **L–** | Prior locus per Table 1: lmbr1 (Letelier et al. 2018), recessive. Not GWAS-analysed |

### Eye morphology

| Trait | Japanese name | Phenotype described | Chr | Interval (bp) | n | Best P | # genes | Candidate gene(s) | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| deme | 出目† | Protrusion of eyeballs from the skull due to **skeletal dysplasia of the head**; no enlargement of the eyeballs | 15 | 23,036,284–25,194,225 | 15 | 1.76E−22 | 109 | **bmp5** | **L3** | Nominated via GO "skeletal system development" (GO:0001501). No deme-specific coding mutation; instead an SNV 1.6 kb **upstream** of bmp5 (Chr15:24,280,607; case 12/15, control 1/166). Note: chr15 like hirenaga/swallow but a **different, non-overlapping interval** (~23.0–25.2 Mb vs ~7.3–12.1 Mb) |
| bigeye | — | Enlarged eyeballs that do **not** protrude from the skull | 2 | 20,843,163–23,907,604 | 7 | 6.48E−34 | 74 | **abcb6a, chn1** | **L2** | Clean ontological contrast with deme (protrusion vs enlargement) |
| tenme | 天眼† | Small pupil; small eyeballs in some cases | 22 | 47,214–3,731,349 | 14 | 1.45E−19 | 223 | — | **L1** | |
| suihougan | 水泡眼† | Enlargement of the anterior segment of the eyeball; corneal cyst | — | — | — | — | — | — | **L–** | Not GWAS-analysed |

### Domestication selection signal (not trait-associated — FST outliers)

`poc1a`, `tyr`, `nme2a`, `gabrr2b`. The authors interpret *tyr* (tyrosinase, rate-limiting for melanin)
as evidence that light body color selection was an essential early domestication step, and `gabrr2b`
(a GABA receptor) as a possible tameness/stress-tolerance signature. **Evidence level: population-genetic
outlier only — no phenotype association, no variant, no functional test.**

† **Japanese-script column is my reconstruction, NOT from the paper.** The paper gives only romanized
names. Entries marked † are standard Japanese ornamental-medaka hobby terms that I am confident map
to the romanization, but they were not verified against the source. Treat the romanized string as
the authoritative identifier for the ontology; treat the kanji/kana as a display-label suggestion
requiring native review. Entries with "—" are ones where I could not responsibly guess.

---

# Background literature by trait

All DOIs and PMIDs below were extracted from the seed paper's own JATS reference list (publisher
metadata) or resolved against the CrossRef API. None are reconstructed from memory.

## Hikari / Double anal fin (Da) → zic1/zic4

| Paper | Year | DOI | PMID | What was shown |
|---|---|---|---|---|
| Ohtsuka M. et al. "Possible roles of zic1 and zic4, identified within the medaka Double anal fin (Da) locus, in dorsoventral patterning of the trunk-tail region (related to phenotypes of the Da mutant)." *Mech Dev* 121:873–882 | 2004 | `10.1016/j.mod.2004.04.006` | 15210192 | Identified *zic1* and *zic4* as the genes within the Da locus and implicated them in dorsoventral patterning of the trunk-tail region. **The founding gene-identification paper.** |
| Ohtsuka M. et al. "Comparative analysis of a 229-kb medaka genomic region, containing the zic1 and zic4 genes, with Fugu, human, and mouse." *Genomics* | 2004 | `10.1016/j.ygeno.2003.09.027` | UNVERIFIED | Comparative genomic characterization of the zic1/zic4 region, establishing the locus structure. Supporting, not central. |
| Moriyama Y. et al. "The medaka zic1/zic4 mutant provides molecular insights into teleost caudal fin evolution." *Curr Biol* 22:601–607 | 2012 | `10.1016/j.cub.2012.01.063` | 22386310 | A large **transposon inserted into the enhancer region** of zic1/zic4 causes mesoderm-specific loss of their transcription; zic1/zic4 expression in dorsal ural mesenchyme drives asymmetric caudal fin development, and its loss yields the symmetrical (diphycercal-like) caudal skeleton. **This is the citation the seed paper uses for hikari.** |
| Kawanishi T. et al. "Modular development of the teleost trunk along the dorsoventral axis and *zic1/zic4* as selector genes in the dorsal module." *Development* 140:1486 | 2013 | `10.1242/dev.088567` | UNVERIFIED (CrossRef-resolved title/DOI; PMID not confirmed) | Da is an **enhancer mutant**: zic1/zic4 expression is lost specifically in the dorsal half of the somites, producing mirror-image duplication of the ventral half across the lateral midline from larva to adult. Establishes zic1/zic4 as dorsal-module selector genes. |
| Ohtsuka M. et al. "Double Anal Fin (Da): A Medaka Mutant Exhibiting a Mirror-Image Pattern Duplication of the Dorsal–Ventral Axis." In *Medaka* (Springer) | 2011 | `10.1007/978-4-431-92691-7_13` | — | Book-chapter review of the Da mutant. Useful ontology-facing summary. |
| Kawanishi T. et al. "Dorsoventral patterning beyond the gastrulation stage: Interpretation of early dorsoventral cues and modular development mediated by zic1/zic4." *Cells & Development* | 2025 | `10.1016/j.cdev.2025.204012` | UNVERIFIED | Recent review of the zic1/zic4 modular-development model. Not cited by the seed paper; found independently. |

## Daruma (shortened body axis)

**This is the weakest area of the whole ontology.** There is no paper that identifies a daruma causal gene.

| Paper | Year | DOI | PMID | What was shown |
|---|---|---|---|---|
| Inohaya K., Takano Y., Kudo A. "Production of Wnt4b by floor plate cells is essential for the segmental patterning of the vertebral column in medaka." *Development* 137:1807–1813 | 2010 | `10.1242/dev.051540` | 20460365 | Loss of *wnt4b* causes the medaka ***fused centrum* (*fsc*)** mutant — disrupted segmental patterning of the vertebral column. **Caution: this is *fsc*, not daruma.** Table 1 of the seed paper lists wnt4b as daruma's "reported locus", but the seed paper's own text says the wnt4b mutation "does not appear to be a major mutation causing the daruma phenotype" (wnt4b is chr16; the daruma GWAS peak is chr4). |
| Kimura T. et al. "Genetic Analysis of Vertebral Regionalization and Number in Medaka (*Oryzias latipes*) Inbred Lines." *G3* | 2012 | `10.1534/g3.112.003236` | UNVERIFIED | QTL-level genetic analysis of vertebral number/regionalization in medaka inbred lines. Background for axial-skeleton trait modelling; does not address daruma. |

## Pigmentation genes → medaka color varieties

| Gene | Variety / mutant mapping | Paper | Year | DOI | PMID | What was shown |
|---|---|---|---|---|---|---|
| **slc45a2** (the *b* locus) | **yellow / himedaka**, and in the seed paper also **blackrim**, **YWKo**, **white** (partly) | Fukamachi S., Shimada A., Shima A. "Mutations in the gene encoding B, a novel transporter protein, reduce melanin content in medaka." *Nat Genet* 28:381–385 | 2001 | `10.1038/ng584` | 11479596 | Identified the medaka *b* locus as a novel transporter gene (now slc45a2); mutations reduce melanin content. **This is the himedaka gene.** |
| **slc45a2** (functional proof) | — | Fukamachi S. et al. "Rescue From Oculocutaneous Albinism Type 4 Using Medaka slc45a2 cDNA Driven by Its Own Promoter." *Genetics* | 2008 | `10.1534/genetics.107.073387` | UNVERIFIED | Medaka slc45a2 cDNA under its own promoter rescues the pigmentation defect — functional validation, and establishes the OCA4 orthology. |
| **tyr** (tyrosinase, the *i* locus) | **albino** (classic medaka albino) | Koga A. et al. "Insertion of a novel transposable element in the tyrosinase gene is responsible for an albino mutation in the medaka fish, *Oryzias latipes*." *Mol Gen Genet* | 1995 | `10.1007/BF00287101` | UNVERIFIED | A transposable-element (Tol-1) insertion in *tyr* causes the medaka albino mutation. **Causal variant identified.** |
| **tyr** (reversion evidence) | albino | Tsutsumi M. et al. "Color reversion of the albino medaka fish associated with spontaneous somatic excision of the Tol-1 transposable element from the tyrosinase gene." *Pigment Cell Res* | 2006 | `10.1111/j.1600-0749.2006.00300.x` | UNVERIFIED | Somatic excision of Tol-1 from *tyr* restores color — strong causal confirmation. |
| **tyr** (rescue) | albino | Fu Y. et al. "Stable and full rescue of the pigmentation in a medaka albino mutant by transfer of a 17 kb genomic clone containing the medaka tyrosinase gene." *Gene* | 2000 | `10.1016/S0378-1119(99)00473-4` | UNVERIFIED | Transgenic rescue of the albino mutant with a genomic *tyr* clone. |
| **slc24a5** | seed paper nominates it for **panda** (hedged) | Lamason R.L. et al. "SLC24A5, a putative cation exchanger, affects pigmentation in zebrafish and humans." *Science* 310:1782–1786 | 2005 | `10.1126/science.1116238` | 16357253 | The zebrafish *golden* gene; a cation exchanger affecting melanosome pigmentation in zebrafish and humans. **Comparative reference — not a medaka paper.** |
| **slc24a5** (context) | — | Schnetkamp P.P.M. "The SLC24 gene family of Na+/Ca2+-K+ exchangers: from sight and smell to memory consolidation and skin pigmentation." *Mol Aspects Med* 34:455–464 | 2013 | `10.1016/j.mam.2012.07.008` | 23506883 | Review of SLC24 family function; used by the seed paper to argue slc24a5 "may not fully explain" panda. |
| **pnp4a** | ***guanineless*** iridophore mutant; **explicitly rejected for panda** by the seed paper | Kimura T., Takehana Y., Naruse K. "Pnp4a is the causal gene of the medaka iridophore mutant *guanineless*." *G3* 7:1357–1363 | 2017 | `10.1534/g3.117.040675` | 28258112 | *pnp4a* is the causal gene for the medaka *guanineless* iridophore mutant. **Causal.** The seed paper's Table 1 lists pnp4a as panda's prior locus but its own text rules this out. |
| **pax7a** | leucophore / xanthophore specification (relevant to **shirome**-type and leucophore traits) | Kimura T. et al. "Leucophores are similar to xanthophores in their specification and differentiation processes in medaka." *PNAS* 111:7343–7348 | 2014 | `10.1073/pnas.1311254111` | 24803434 | Medaka leucophores share specification/differentiation programs with xanthophores; *pax7a* is central to this shared lineage. **Note: pax7a does not appear anywhere in the seed paper.** |
| **sox5** | ***leucophore free (lf)*** — pigment-cell fate switch | Nagao Y. et al. "Sox5 Functions as a Fate Switch in Medaka Pigment Cell Development." *PLoS Genet* 10:e1004246 | 2014 | `10.1371/journal.pgen.1004246` | UNVERIFIED | Sox5 acts as a fate switch between xanthophore and leucophore lineages in medaka. **Causal / functional.** Not cited by the seed paper. |
| **kitlga** (kit ligand a) | ***few melanophore (fm)***; seed paper newly links it to **aurora** | Otsuki Y., Okuda Y., Naruse K., Saya H. "Identification of kit-ligand a as the gene responsible for the medaka pigment cell mutant *few melanophore*." *G3* 10:311–319 | 2020 | `10.1534/g3.119.400561` | 31757930 | *kitlga* is the causal gene for medaka *few melanophore*. **Causal.** The seed paper notes a tension: kitlga mutants show reduced melanophores but "no detectable alteration in iris iridophores", whereas aurora shows adult iridophore loss. |
| **somatolactin** (*color interfere*, *ci*) | pigment-cell proliferation/morphogenesis | Fukamachi S., Sugimoto M., Mitani H., Shima A. "Somatolactin selectively regulates proliferation and morphogenesis of neural-crest derived pigment cells in medaka." *PNAS* 101:10661–10666 | 2004 | `10.1073/pnas.0401278101` | 15249680 | Somatolactin selectively regulates neural-crest-derived pigment cell proliferation and morphogenesis. |
| **lf × ci interaction** | leucophore free / color interfere double mutants | Fukamachi S. et al. "Medaka double mutants for color interfere and leucophore free: characterization of the xanthophore–somatolactin relationship using the leucophore free gene." *Dev Genes Evol* | 2005 | `10.1007/s00427-005-0040-9` | UNVERIFIED | Dissects the xanthophore–somatolactin relationship via lf/ci double mutants. |
| **mpv17** | a lab **"panda (pa)"** iridophore mutant — **name collision, see Gaps** | Koda et al. "Discovery of the Novel Iridophore Mutant Medaka 'panda (pa)' and Identification of the Causal Gene, mpv17" | 2024 | `10.22541/au.173204448.88130877/v1` | — | **PREPRINT ONLY** (Authorea posted-content). Claims mpv17 as causal for a medaka iridophore mutant also called "panda". Not cited by the seed paper; no published version found. |
| **mpv17** (comparative) | zebrafish *transparent* | Krauss J. et al. "*transparent*, a gene affecting stripe formation in Zebrafish, encodes the mitochondrial protein Mpv17 that is required for iridophore survival." *Biol Open* | 2013 | `10.1242/bio.20136239` | UNVERIFIED | Mpv17 is required for iridophore survival in zebrafish. Comparative support for the mpv17 preprint. |
| **oca2** | listed for **albino** by the seed paper | — | — | **UNRESOLVED — see Gaps** | — | The seed paper's Table 1 attributes albino→oca2 to "Fukamachi et al. 2004", but the only Fukamachi 2004 entry in its own reference list is the somatolactin PNAS paper. **Do not cite this pairing.** |
| **atp6ap2** | seed paper nominates for **black** | Tatarakis D. et al. "Single-cell transcriptomic analysis of zebrafish cranial neural crest reveals spatiotemporal regulation of lineage decisions during development." *Cell Rep* 37:110140 | 2021 | `10.1016/j.celrep.2021.110140` | 34936864 | Zebrafish scRNA-seq showing atp6ap2 requirement in melanocyte differentiation — the basis for the seed paper's nomination. |
| **uvrag** | seed paper nominates for **sanshoku / kurobuchi** | Yang Y. et al. "Central role of autophagic UVRAG in melanogenesis and the suntan response." *PNAS* 115:E7728–E7737 | 2018 | `10.1073/pnas.1803303115` | 30061422 | UVRAG is central to autophagy-dependent melanogenesis; reduced UVRAG causes defective melanocyte development in zebrafish. |
| **adcy5** (comparative) | seed paper's **orochi** gene | Zhang L., Wan M., Tohti R., Jin D., Zhong T.P. "Requirement of Zebrafish Adcy3a and Adcy5 in melanosome dispersion and melanocyte stripe formation." *Int J Mol Sci* 23:14182 | 2022 | `10.3390/ijms232214182` | 36430661 | Loss of adcy5 reduces pigmented melanocyte density in zebrafish stripe formation — the comparative precedent for orochi. |
| **ADCY5** (human disease) | melanism ↔ human dyskinesia link the seed paper draws | Carapito R. et al. "A de novo ADCY5 mutation causes early-onset autosomal dominant chorea and dystonia." *Mov Disord* 30:423–427 | 2015 | `10.1002/mds.26115` | 25545163 | Human ADCY5 mutations cause familial dyskinesia; disease mutations cluster in the coiled-coil and C1b domain — the same domain as the orochi deletion. |
| **r locus** (historical) | **white**, **blue** | Aida T. "On the inheritance of color in a freshwater fish, *Aplocheilus latipes* Temminck and Schlegel, with special reference to sex-linked inheritance." *Genetics* 6:554–573 | 1921 | `10.1093/genetics/6.6.554` | 17245975 | The founding classical-genetics paper on medaka color inheritance; source of the *r* locus. Historical anchor for the ontology. |
| **ltk** | iridophore development | Mo E.S. et al. "Alk and Ltk ligands are essential for iridophore development in zebrafish mediated by the receptor tyrosine kinase Ltk." *PNAS* | 2017 | `10.1073/pnas.1710254114` | UNVERIFIED | Ltk (with Alk) is essential for **zebrafish** iridophore development. **No medaka ltk paper was found** — see Gaps. |

## Hirenaga / long-fin / Swallow → fin ray elongation

| Paper | Year | DOI | PMID | What was shown |
|---|---|---|---|---|
| Perathoner S. et al. "Bioelectric signaling regulates size in zebrafish fins." *PLoS Genet* 10:e1004080 | 2014 | `10.1371/journal.pgen.1004080` | 24453984 | The zebrafish ***longfin*** mutant is caused by the potassium channel ***kcnk5b***; bioelectric signaling sets fin proportion. **The canonical comparative reference.** The seed paper cites it as the precedent motivating potassium-channel candidates. |
| Daane J.M. et al. "Bioelectric-calcineurin signaling module regulates allometric growth and size of the zebrafish fin." *Sci Rep* | 2018 | `10.1038/s41598-018-28450-6` | UNVERIFIED | Extends the bioelectric model with a calcineurin module controlling allometric fin growth. |
| Harris M.P., Daane J.M., Lanni J. "Through veiled mirrors: fish fins giving insight into size regulation." *WIREs Dev Biol* 10:e381 | 2021 | `10.1002/wdev.381` | 32323915 | Review of fin size regulation and the bioelectric/potassium-channel paradigm. Good ontology-facing overview. |
| Silic M.R., Zhang G. "Bioelectricity in developmental patterning and size control: evidence and genetically encoded tools in the zebrafish model." *Cells* 12:1148 | 2023 | `10.3390/cells12081148` | 37190057 | Review of bioelectric size control. |
| Zhang J. et al. "Loss of fish actinotrichia proteins and the fin-to-limb transition." *Nature* 466:234–237 | 2010 | `10.1038/nature09137` | 20574421 | Characterizes the **actinodin** (*and1/and2*) actinotrichia proteins and their loss in the fin-to-limb transition. **This is the basis for the seed paper's *and2* nomination for reallongfin.** |
| Letelier J. et al. "A conserved Shh cis-regulatory module highlights a common developmental origin of unpaired and paired fins." *Nat Genet* 50:504–509 | 2018 | `10.1038/s41588-018-0080-5` | 29556077 | Identifies the *lmbr1*-associated Shh cis-regulatory module; basis for the **nodorsalfin** → *lmbr1* attribution in Table 1. |

**Medaka equivalent of kcnk5b:** none published before this seed paper. The seed paper's `kcnq5a`
(hirenaga/swallow, chr15) and `kcna10/kcna3/kcnd3` (longfin, chr7) are the **first** medaka
potassium-channel fin-elongation candidates — and both remain at candidate level, not causal.

## adcy5 and kcnq5a status check (asked explicitly in the brief)

- **adcy5** — appears in the medaka ornamental literature for the **first time** in this seed paper, as the **orochi** (hyper-melanism) gene. It is the paper's single functionally validated result (genome-edited `adcy5^delex8` phenocopy). 31 mentions in the full text.
- **kcnq5a** — likewise first appears here, for **hirenaga/swallow**. 11 mentions. Evidence is a GWAS peak plus an intron-1 deletion; **no functional validation, no coding variant.** Do not record this as causal.

---

# Gaps and uncertainties

### Things I could not verify

1. **Japanese trait names are not in the source.** The paper uses romanized names only (hirenaga, daruma, yokihi, …). Every kanji/kana string in my table is my own reconstruction, marked †. This needs a native-speaker pass before it enters the ontology as display labels. The romanized strings are safe as identifiers.
2. **PMIDs marked UNVERIFIED.** Where the seed paper's reference list carried a DOI but no PMID (or where I resolved a paper only via CrossRef), I left PMID blank rather than guess. The DOIs themselves are all either publisher-supplied or CrossRef-resolved.
3. **Kawanishi 2013 *Development* PMID** not confirmed; DOI `10.1242/dev.088567` is CrossRef-resolved and the title matches.
4. **"Medaka: a novel model for analyzing genome–environment interactions" DOI is inferred**, not resolved. Flagged in the runner-up table. Do not cite as-is.
5. **Genome Research 2026 complete-medaka-genomes paper** — I did not resolve its DOI. Listed as a runner-up to be ruled out, not to be cited.
6. **No medaka *ltk* paper exists** that I could find. The brief asked for it; only the zebrafish Ltk/Alk iridophore work is available. Similarly, **no medaka *kita* paper** — medaka's *few melanophore* maps to the **ligand** (*kitlga*), not the receptor.
7. **No functional daruma gene.** The literature is genuinely empty here, and the seed paper's own GWAS found a strong chr4 peak (P = 9.6E−38) with 211 genes and no nominated candidate.

### Conflicting reports the ontology must handle

1. **"panda" is an overloaded name — the most dangerous collision in this dataset.**
   - The seed paper's ornamental **panda** strain → GWAS peak chr3, nominates *slc24a5*, but the authors hedge heavily and say the real gene is probably an uncharacterized gene in the interval.
   - The seed paper's own **Table 1 says panda's prior locus is *pnp4a* (Kimura 2017)** — and the paper's own Results **reject** that: no coding mutations in pnp4a in panda individuals.
   - Separately, a **2024 preprint (Koda et al.)** describes a *different*, newly discovered lab medaka iridophore mutant **also named "panda (pa)"** and attributes it to ***mpv17***.
   - Three genes, one trait name, no agreement. Recommend the ontology store `panda` with an explicit source-scoped disambiguation and no committed causal gene.

2. **daruma → wnt4b is a mis-attribution carried inside the seed paper itself.** Table 1 lists wnt4b as daruma's reported locus; the Results section contradicts it (wnt4b is chr16 / *fused centrum*; the daruma peak is chr4). The table and the text of the same paper disagree. Trust the text.

3. **albino → oca2 citation is broken in the seed paper.** Table 1 cites "oca2 (Fukamachi et al. 2004)" but the only Fukamachi 2004 in its reference list is the somatolactin PNAS paper, which is not about oca2. Meanwhile the well-established medaka albino (*i* locus) gene is ***tyr*** (Koga 1995, transposon insertion). Recommend recording albino → *tyr* with the Koga lineage, and treating the oca2 claim as unsourced pending a check of the printed reference list.

4. **aurora → kitlga has an internal tension the authors acknowledge.** Otsuki 2020 reports that kitlga mutants (*fm*) show reduced melanophores but **no** iris iridophore change; aurora is an iridophore phenotype. The authors offer a shared-neural-crest-progenitor explanation and explicitly concede they "cannot rule out … another gene located near kitlga" (the interval is 175 genes and 6.8 Mb — one of the widest).

### Statistical caveats worth carrying into the ontology

- Several headline-significant intervals rest on **very few mutants**: sanshoku n=4 (P=6.5E−61), fukumaku n=4 (P=5.7E−59), daruma n=6, kuroaka n=7, bigeye n=7, reallongfin n=8. Extreme P-values with n<10 in a structured, heavily inbred, strongly stratified population are fragile. Strain structure and phenotype are confounded here almost by construction.
- **Candidate intervals are large** — median roughly 100–200 genes, up to 318 (longfin). "Candidate gene" in this paper generally means "a gene with a plausible GO term inside a multi-megabase window", not a mapped locus.
- **Composite / umbrella classes are mixed in with strain phenotypes**: `YWKo` (yellow-or-white-or-kouhaku), `kurobuchi` (declared to *include* sanshoku and kuroaka), `akabuchi` (declared to include sanshoku and kouhaku). These are not disjoint traits, and GWAS on overlapping label sets will share signal by construction. The ontology needs explicit subsumption relations here, or the trait→locus edges will look falsely replicated.
- Only **1 of 26** trait→gene assignments is functionally validated (**adcy5/orochi**). One more (**zic1/4**/hikari) is causal from prior literature. Everything else is candidate-level or interval-only.

### Recommended evidence gating for the ontology

| Tier | Traits |
|---|---|
| Causal, functionally validated | orochi → *adcy5* |
| Causal, established in prior literature | hikari → *zic1/zic4*; albino → *tyr*; yellow/himedaka → *slc45a2*; *guanineless* → *pnp4a*; *few melanophore* → *kitlga*; *leucophore free* → *sox5* |
| Strong candidate with a co-segregating variant | aurora → *kitlga*; hirenaga/swallow → *kcnq5a*; deme → *bmp5* |
| Positional candidate only | blackrim/YWKo → *slc45a2*; black → *atp6ap2*; sanshoku/kurobuchi → *uvrag*; akabuchi → *foxd3*; panda → *slc24a5*; longfin → *kcna10/kcna3/kcnd3*; reallongfin → *and2*; bigeye → *abcb6a/chn1* |
| Interval only, no gene | white, blue, miyuki, rame, kouhaku, kuroaka, fukumaku, daruma, tenme |
| No association found | yokihi, gold, toumeirin |
| Not analysed | handaruma, suihougan, nijikin, nodorsalfin, albino |
