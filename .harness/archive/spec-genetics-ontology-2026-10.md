# Spec — 용어 2차 정제와 유전 관계 온톨로지 (2026-10)

## 목표
1차 용어 통일(PR #10)을 검증해 남은 동의어 흩어짐·잘못된 병합·표기 흔들림을 고치고, 정제된 다국어 라벨을
온톨로지에 결합한다. 그 위에 유전 양식·대립유전자·우열·성연관·상위성·연관·복합 형질을 표현하는 층을 더해,
두 부모의 유전자형으로 자손 형질 분포를 내는 최소 질의가 가능함을 검증한다.

## 범위
- 1차 결과 검증: `docs/research/breeder-vocabulary-*.csv`, `data/seed/1x-*.yaml`. 기계 감사 스크립트와 보고서.
- 2차 정제: seed 라벨 교정, CSV 관계표의 잘못된 간선 교정(빌드 스크립트 경유), 근거를 rulings 에 기록.
- 다국어 라벨 구조(`labels`): 언어 태그·읽기·출처·검증 상태를 라벨마다 둔다. 언어 제약 없음을 문서에 명시.
- 유전 층: 새 노드 라벨 `InheritanceMode`, 새 predicate(유전 양식·대립·우열·형질의 대립유전자 요구·연관·가림·구성),
  새 증거 수준 `INFERRED`, 각 predicate 의 증거 수준 정의(ADR), seed 데이터(출처 있는 것만).
- 교배 질의: 순수 Python 모듈 + CLI 명령. Neo4j 없이 seed 에서 돈다.

## 비범위
- 품종명 층 전체 편입(328개 품종). JMA 가 구성을 명시하고 구성 형질이 모두 seed 에 있는 소수만 넣는다.
- 교배 추천·최적 교배 전략·개체 관리(PRD §14 의 나머지 비목표는 유지).
- 출처 없는 유전 양식 기입. 모르는 것은 모른다고 둔다.
- `TraitCategory` 에 LUSTER 축 추가(miyuki 문제, 별도 ADR 후보로 남김).

## 수용 기준
- AC-1: 1차 결과 검증 보고서가 있다(`docs/research/vocabulary-audit-2026-10.md`). 검사 종류별 발견 수와 대표 사례,
  각 발견의 판정(고침/의도된 것/남김)이 있다. 감사는 스크립트로 재현된다.
- AC-2: 감사가 "고침"으로 판정한 것은 모두 고쳐졌고, 병합·분리·이름 변경마다 rulings 에 근거(출처·판단 이유) 한 줄이 있다.
  최소한 다음이 반영된다: ブラック≠オロチ(same_as 제거), akabuchi↛白朱赤(seed_match 교정), Daタイプ 는 hikari 의 라벨,
  yellow 의 ヒメダカ 는 출처 있는 라벨, tenme 의 スモールアイ 는 JMA 출처 라벨, 다툼 있는 same_as 2건 표시.
- AC-3: Entity 에 다국어 `labels` 가 있다. 라벨은 언어 태그(BCP 47)·종류·읽기·출처(paper key 또는 `bv:` id)·상태를 갖는다.
  기존 `japanese_name`/`aliases`/`unverified_labels` 를 읽는 경로(dossier·query·lexicon·resolution)가 계속 동작한다.
  출처 없는 라벨은 `UNVERIFIED_LABEL` 을 끌고 다닌다(테스트로 강제).
- AC-4: README 와 설계 문서(ADR)에 "온톨로지 언어에는 제약이 없다(영어·일본어·한국어 등 혼용 가능), 품종명은
  일본어 원어 표기를 기준으로 다른 언어 표기를 동의어로 둔다"가 명시되어 있다.
- AC-5: 새 predicate 와 `InheritanceMode`·`INFERRED` 가 vocabulary 에 닫힌 집합으로 있고, 각각 domain/range 가 선언되어
  있으며, 증거 수준 정의와 experiment_type 상한이 ADR 과 `ceilings.py` 에 있다.
- AC-6: seed 에 출처 있는 유전 데이터가 있다. 최소: Kon 2026 Table 1 의 유전 양식 11건(원문 대조), b·r·i 좌위의 대립유전자와
  우열(Sasano 2012), r 좌위의 성연관(Hayasaka 2019), 연관 1건 이상, 가림(상위성) 1건 이상, 복합 형질 1건 이상.
  추론은 `INFERRED` 로 표시한다.
- AC-7: 교배 질의가 두 부모 유전자형 → 자손 유전자형·형질 분포(성별 구분)를 낸다. 예측에 쓴 claim 중 가장 약한 증거 수준을
  함께 낸다. 모델에 없는 형질은 "예측 불가(사유)"로 명시한다.
- AC-8: 교배 질의 검증: (a) Hayasaka 2019 의 Hd-rRII1 계통 유지 교배(딸 전부 白, 아들 전부 주황) 재현,
  (b) Sasano 2012 Cross I 역교배 관찰 수와 예측 비율의 적합도 보고, (c) 성연관 때문에 9:3:3:1 이 깨지는 예시. 테스트로 고정.
- AC-9: `python -m medaka_ontology.cli validate` 와 `pytest` 가 통과한다. skip 은 이름과 사유를 적는다.
  seed 에서 생성되는 커밋 산출물(dossier)이 달라져야 하면 재생성하거나 사유를 보고한다.
- AC-10: 작업 브랜치 `genetics-ontology` 에 커밋한다. main 에 push·merge 하지 않는다.

## 열린 결정
- PRD §14 는 "Mendelian cross simulator", "offspring phenotype prediction" 을 비목표로 둔다. 이번 지시는 그 질의를
  검증용으로 요구한다. 검증용 최소 질의로 한정하고, 비목표 해제 여부는 사용자 결정으로 남긴다.
- 권위 순서(JMA > 도감 > 번식장 > 블로그)는 여전히 잠정.
- r 좌위와 성결정 좌위 사이 재조합률은 출처가 없어 0 으로 둔다(가정 명시).

## 변경 이력
- 2026-10-01 이전 spec(용어 조사 결과의 seed 반영, AC-1..AC-8)은 `.harness/archive/spec-breeder-labels-to-seed-2026-09.md` 로 옮겼다.
