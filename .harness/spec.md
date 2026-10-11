# Spec — 체외광·린광을 관상 형질로 (2026-10)

## 목표
JMA 매뉴얼 제5판 §3.4.2 가 정의하는 체외광(体外光)과 그 形質補足 린광(鱗光)을 `OrnamentalTrait` 로 seed 에 넣는다.
광택 축이 없던 `TraitCategory` 에 LUSTER 를 신설한다(2026-10-11 사용자 결정, ADR 0008).

## 범위
- 어휘: `TraitCategory.LUSTER` 추가. ADR 0008 신설.
- seed: `12-entities-breeder-traits.yaml` 에 형질 2개와 필요한 Phenotype, `23-claims-breeder.yaml` 에 claim.
- miyuki 라벨 note 의 포인터 갱신(体外光 을 miyuki 라벨로 붙이지 않는 R-36 은 유지).
- 테스트, README·문서에서 형질 수·범주 목록을 말하는 곳.

## 비범위
- Kon 형질(miyuki, rame 등)의 category 이동.
- 체외광의 다른 形質補足(光の色 5종, 頭光·横光, スポットラメ)과 체외광 등급어(点光~極光)를 엔티티로 올리는 것.
- 체외광·린광의 유전자 claim, 유전 양식 claim.
- miyuki 와 taigaikou 를 잇는 형질-형질 claim.
- hikari 의 `ectopic dorsal iridophore` claim 에 대한 JMA 반박(CONTRADICTS) 기록.

## 수용 기준
- AC-1: `TraitCategory` 에 `LUSTER = "LUSTER"` 가 있고, ADR 0008 이 "형질의 category 는 그 형질을 정의한 출처의 분류를 따른다; Kon 형질은 Kon Table 1 분류를 유지한다"를 결정으로 기록한다.
- AC-2: `OrnamentalTrait` `taigaikou` 가 category LUSTER 로 있다. 라벨은 体外光(ja, PREFERRED, reading たいがいこう, sources [jma5], vocab [bv:0074])과 체외광(ko, PREFERRED, vocab [bv:0074])이다. description 은 jma5 §3.4.2 에 근거한다.
- AC-3: `OrnamentalTrait` `rinkou` 가 category LUSTER 로 있다. 라벨 鱗光(ja, PREFERRED, reading りんこう, sources [jma5], vocab [bv:0087])에는 같은 문자열이 垂水政治 2019 품종명이기도 하다는 note 가 붙는다. 출처가 없는 한국어 표기는 UNVERIFIED 로만 둔다.
- AC-4: 두 형질의 모든 claim 은 근거가 jma5 §3.4.2 이고 수준은 BREEDER_OBSERVATION 이다. 최소한 다음 claim 이 있다: `taigaikou has_phenotype ectopic dorsal iridophore`, `taigaikou subsumes rinkou`, rinkou 를 체외광과 구분하는 has_phenotype 1개 이상.
- AC-5: seed 에 taigaikou·rinkou 의 유전자·좌위·유전 양식 claim 이 없고, miyuki 나 hikari 와 잇는 형질-형질 claim 도 없다. 그렇게 둔 이유가 파일 주석에 있다.
- AC-6: `pytest` 가 통과하고(Neo4j 없이 skip 되는 통합 테스트는 skip), 새 형질과 LUSTER 를 확인하는 seed 테스트가 1개 이상 추가된다.
- AC-7: `.claude/skills/trait-literature-search/scripts/validate_rule.py` 결과가 baseline 과 같다. 다르면 차이를 보고한다.

## 열린 결정
- hikari 의 `ectopic dorsal iridophore` (Kon) 와 JMA 의 "ヒカリ의 등 빛은 배 쪽 홍색소포의 전이, 체외광과 다르다" 사이의 긴장 기록 여부.
- 체외광 形質補足(색·위치·스폿라메)을 엔티티로 올릴지.

## 변경 이력
