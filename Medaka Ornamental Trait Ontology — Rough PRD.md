# Medaka Ornamental Trait Ontology

## 1. 목적

관상 메다카(*Oryzias latipes*)의 형질과 유전적 배경에 관한 연구 자료를 지속적으로 수집하고, 이를 구조화된 **Ornamental Trait Ontology**로 구축한다.

최종적으로 다음과 같은 질문에 근거 기반으로 답할 수 있는 knowledge base를 만드는 것이 목적이다.

- 특정 관상 형질과 연관된 gene / locus / variant는 무엇인가?
- 해당 연관관계는 어느 수준까지 검증되었는가?
- 하나의 유전적 변화가 어떤 복수의 phenotype을 발생시키는가?
- 서로 다른 관상 형질이 동일한 gene / pathway / developmental mechanism을 공유하는가?
- 브리더가 사용하는 형질명과 학술 문헌의 mutant / phenotype 명칭은 어떻게 연결되는가?
- 특정 형질과 함께 나타나는 pleiotropy, modifier, epistasis 등의 관계가 알려져 있는가?

본 프로젝트는 **브리딩 의사결정 시스템 자체를 구현하지 않는다.**

현재 목표는 향후 브리딩 의사결정에 사용할 수 있는 신뢰도 높은 knowledge layer를 구축하는 것이다.

---

# 2. 핵심 원칙

## 2.1 Trait-first

Ontology의 primary entity는 `Gene`이 아니라 `OrnamentalTrait`이다.

실제 사용자는 보통 다음과 같이 질문한다.

> "Hikari는 어떤 유전적 원인으로 발생하는가?"

따라서 탐색의 기본 방향은 다음과 같다.

`Ornamental Trait → Phenotype → Genetic Association → Mechanism → Evidence`

Gene-centric navigation은 지원하지만 ontology 구축의 출발점으로 사용하지 않는다.

---

## 2.2 Evidence-first

논문에서 발견된 association을 곧바로 사실로 확정하지 않는다.

모든 주요 claim은 반드시 source와 연결한다.

예:

`Hikari → caused_by → zic1/zic4 regulatory alteration`

라는 edge가 존재한다면 동시에 다음 정보를 추적할 수 있어야 한다.

- source paper
- experiment
- studied strain / population
- causal variant
- 연구자가 실제 주장한 범위
- evidence level

이를 통해 다음을 구별한다.

`Causal Variant ≠ Functional Evidence ≠ Fine Mapping ≠ GWAS/QTL Association ≠ Breeder Observation`

---

## 2.3 Raw evidence와 interpretation 분리

논문에서 직접 확인할 수 있는 내용과 시스템이 해석한 내용을 구별한다.

예:

### Evidence

> Da mutant에서 zic1/zic4의 dorsal expression loss가 관찰됨.

### Interpretation

> zic1/zic4가 dorsal developmental identity를 조절하며 Hikari phenotype의 주요 mechanism으로 작동한다.

두 정보는 연결되지만 동일한 record로 취급하지 않는다.

---

## 2.4 Provenance 보존

모든 정보는 가능한 경우 원문까지 역추적 가능해야 한다.

최소 provenance:

- DOI
- PMID / PMCID
- paper title
- publication year
- source URL
- relevant section / figure / table
- extracted text 또는 evidence summary

---

# 3. Ontology Scope

초기 ontology는 다음 entity를 중심으로 구성한다.

## OrnamentalTrait

브리더가 인식하고 선택하는 관상 형질.

예:

- Hikari
- Orochi
- Hirenaga
- Swallow
- Panda
- Aurora
- Daruma

가능한 필드:

- canonical name
- Japanese name
- aliases
- breeder terminology
- category
- description

---

## Phenotype

실제로 관찰 가능한 생물학적 phenotype.

예:

- elongated fin ray
- dorsal pigmentation
- melanism
- shortened body axis
- altered dorsal/ventral morphology

하나의 OrnamentalTrait은 여러 Phenotype을 포함할 수 있다.

---

## Gene

형질 또는 phenotype과 관련된 gene.

예:

- zic1
- zic4
- adcy5
- kcnq5a
- slc24a5
- slc45a2

가능하면 다음도 연결한다.

- medaka gene identifier
- chromosome
- ortholog
- known biological function

---

## GeneticVariant / Locus

형질과 연관된 실제 genomic alteration.

예:

- SNP
- deletion
- insertion
- regulatory mutation
- mapped genomic region

Gene association과 causal variant를 반드시 구별한다.

---

## BiologicalMechanism

형질이 발생하는 생물학적 과정.

예:

- dorsal/ventral patterning
- chromatophore development
- potassium-channel signaling
- neural crest development
- fin-ray growth

---

## Evidence

ontology의 relation을 지지하는 개별 연구 결과.

Evidence는 최소한 다음을 포함한다.

- paper
- experiment type
- population / strain
- finding
- evidence level
- relevant entity/relation

---

# 4. 주요 Relationship

초기에는 relation vocabulary를 과도하게 확장하지 않는다.

필수 relation 후보:

```text
OrnamentalTrait
    has_phenotype
    associated_with_gene
    associated_with_locus
    caused_by_variant

Phenotype
    affects_anatomy
    associated_with_gene

Gene
    participates_in
    ortholog_of

Trait / Phenotype
    resembles
    co_occurs_with
    modified_by
    epistatic_with
    pleiotropic_with

Evidence
    supports
    contradicts
```

새 relation이 필요한 경우 기존 relation으로 표현할 수 없는지 먼저 확인한 뒤 확장한다.

---

# 5. Evidence Level

최소 다음 수준을 구분한다.

```text
CAUSAL_VARIANT
FUNCTIONAL_VALIDATION
FINE_MAPPING
QTL_GWAS_ASSOCIATION
EXPRESSION_ASSOCIATION
OBSERVATIONAL
BREEDER_OBSERVATION
```

Evidence level은 자동 추출 결과만으로 확정하지 않아도 된다.

불명확한 경우 `UNKNOWN`으로 유지한다.

잘못된 확신보다 불확실성을 보존하는 것을 우선한다.

---

# 6. Literature Collection

## 6.1 Seed

초기 seed dataset으로 최근 ornamental medaka GWAS에서 정의된 관상 형질들을 사용한다.

각 trait를 독립적인 research target으로 생성한다.

---

## 6.2 Search Expansion

단순히 `"medaka ornamental genetics"`를 반복 검색하지 않는다.

각 trait에 대해 iterative search expansion을 수행한다.

기본 탐색 흐름:

```text
Ornamental Trait
        ↓
Aliases / Japanese terminology
        ↓
Known mutant name
        ↓
Associated gene / locus
        ↓
Older gene / mutant papers
        ↓
Developmental mechanism
        ↓
Related phenotype
        ↓
Additional papers
```

예:

```text
Hikari
  ↓
Double anal fin
  ↓
Da mutant
  ↓
zic1 / zic4
  ↓
dorsal identity
  ↓
dorsal-ventral patterning
```

이 방식으로 ornamental medaka를 직접 연구하지 않은 developmental biology / genetics 연구도 수집한다.

---

# 7. Paper Processing Pipeline

수집된 논문은 다음 pipeline을 거친다.

```text
Discovery
    ↓
Metadata extraction
    ↓
Full-text acquisition
    ↓
Relevant section identification
    ↓
Entity extraction
    ↓
Relationship extraction
    ↓
Evidence extraction
    ↓
Evidence classification
    ↓
Entity resolution
    ↓
Ontology update
```

---

# 8. Entity Resolution

동일 개념이 여러 이름으로 등장하는 문제를 반드시 처리한다.

예:

```text
Hikari
ヒカリ
Double anal fin
Da
double-anal-fin mutant
```

이들이 동일하거나 강하게 연관된 개념이라는 것을 표현할 수 있어야 한다.

단, **alias와 biological equivalence를 혼동하지 않는다.**

논문상 mutant와 브리더가 사용하는 strain/trait가 정확히 동일한 genetic background인지 확인되지 않았다면 별개의 entity로 유지하고 relation으로 연결한다.

---

# 9. Contradiction Handling

서로 다른 논문이 다른 결론을 제시할 수 있다.

기존 정보를 overwrite하지 않는다.

예:

```text
Paper A
Trait X → Gene A

Paper B
Trait X → Gene B
```

두 evidence를 모두 보존한다.

Ontology의 claim은 여러 Evidence가 support 또는 contradict할 수 있는 구조로 만든다.

---

# 10. Human Ortholog Layer

Medaka gene에 명확한 human ortholog가 존재하면 추가 정보로 연결한다.

예:

```text
zic1 → ZIC1
zic4 → ZIC4
adcy5 → ADCY5
```

단, human phenotype은 **medaka phenotype의 직접 대응 관계로 간주하지 않는다.**

다음처럼 별도의 comparative biology layer로 취급한다.

```text
Medaka Gene
     ↓ ortholog_of
Human Gene
     ↓ associated_with
Human Phenotype / Disease
```

이 정보는 관상형질의 biological mechanism을 이해하기 위한 supplementary knowledge다.

---

# 11. Automation

수집기는 로컬에서 주기적으로 실행할 수 있어야 한다.

한 번의 실행은 대략 다음 작업을 수행한다.

```text
Known traits / genes / papers load
             ↓
Literature search
             ↓
New candidate papers
             ↓
Deduplication
             ↓
Paper processing
             ↓
Candidate knowledge extraction
             ↓
Evidence validation
             ↓
Ontology update
             ↓
Run report
```

동일 논문을 반복 처리하지 않는다.

새로운 논문뿐 아니라 기존 ontology에서 evidence가 부족한 영역도 탐색 대상으로 삼는다.

---

# 12. Human Review

완전 자동화를 목표로 하지 않는다.

다음 상황은 review 대상으로 표시한다.

- 새로운 OrnamentalTrait 발견
- 새로운 causal variant 주장
- 서로 모순되는 evidence
- entity resolution confidence가 낮음
- breeder terminology와 academic terminology 연결
- 새로운 relationship type 필요
- 논문 원문 확보 실패
- evidence level 판단이 불명확

나머지 명확한 metadata 및 evidence extraction은 자동화한다.

---

# 13. Output

최소 두 종류의 output을 제공한다.

## Machine-readable ontology

향후 프로그램에서 query할 수 있는 구조화 데이터.

구체적인 storage technology는 초기 구현 전에 결정한다.

## Human-readable trait dossier

각 관상 형질을 사람이 바로 확인할 수 있는 형태로 표현한다.

예:

```text
Hikari

Aliases
- ヒカリ
- Double anal fin
- Da

Phenotypes
- altered dorsal fin morphology
- altered dorsal pigmentation
- dorsal → ventral identity transformation

Genetics
- zic1
- zic4
- Chr20 regulatory locus

Mechanism
- dorsal developmental identity

Evidence
- Paper A — CAUSAL_VARIANT
- Paper B — FUNCTIONAL_VALIDATION
- Paper C — GWAS

Related traits
- ...

Open questions
- ...
```

---

# 14. Non-goals

현재 단계에서는 다음을 구현하지 않는다.

- 자동 mating recommendation
- Mendelian cross simulator
- pedigree management
- 개인 보유 개체 관리
- offspring phenotype prediction
- 최적 교배 전략
- image-based phenotype classification

이 기능들은 ontology가 충분히 구축된 이후 별도 시스템으로 설계한다.

---

# 15. 초기 작업 순서

### Phase 1 — Ontology bootstrap

2026 ornamental medaka GWAS에서 정의된 관상 형질과 candidate loci를 seed dataset으로 구축한다.

목표:

`Trait → Phenotype → Gene/Locus → Evidence`

의 최소 graph 생성.

### Phase 2 — Literature backfill

각 trait의 alias, mutant, gene을 이용하여 과거 연구를 역추적한다.

특히 causal mechanism 또는 functional validation 연구를 우선한다.

### Phase 3 — Automated discovery

기존 ontology를 query expansion seed로 사용하여 새로운 논문을 주기적으로 탐색한다.

### Phase 4 — Knowledge refinement

중복 entity 통합, contradiction 탐지, evidence level 보정, relationship 확장 등을 수행한다.

---

# 16. 완료 기준

첫 번째 usable version은 다음 조건을 만족하면 된다.

1. 주요 ornamental medaka trait가 entity로 등록되어 있다.
2. 각 trait에서 관련 논문으로 역추적할 수 있다.
3. Trait–Phenotype–Gene/Locus 관계가 구조화되어 있다.
4. association과 causal evidence를 구별할 수 있다.
5. 동일 trait/gene의 alias가 resolution되어 있다.
6. 새로운 논문을 발견하고 기존 ontology에 증분 반영할 수 있다.
7. 모든 주요 claim의 provenance를 확인할 수 있다.
8. 불확실하거나 충돌하는 정보가 손실되지 않는다.

핵심 산출물은 **논문 목록이 아니라 evidence-backed Medaka Ornamental Trait Ontology**이다.