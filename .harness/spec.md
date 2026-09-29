# Spec — 업계 용어 조사 결과를 seed 에 반영 (a)

## 목표
`docs/research/breeder-vocabulary-2026-09.md` §seed에 대한 발견이 찾은 seed 의 일본어 표기·설명 오류를
`data/seed/` 에 반영하고, 이제 읽은 JMA 改良メダカ品種分類マニュアル 第5版을 출처로 등록한다.

## 범위
- `01-sources-breeder.yaml`: JMA 매뉴얼을 `:Paper` 로 추가하고, "NOT CITED, DELIBERATELY" 주석을 다시 쓴다.
- `10-entities-traits.yaml`: Kon 형질의 일본어 표기 교정. 출처가 그대로 싣는 표기는 `japanese_name` 으로 승격한다
  (사용자 결정 2026-09-29). 파일 머리 주석의 NAMING 원칙을 이에 맞게 다시 쓴다.
- hikari description 의 "pelvic fin" 을 Kon 원문과 대조한다.
- `12-entities-breeder-traits.yaml` / `23-claims-breeder.yaml`: JMA 매뉴얼이 カガミ鱗·フサヒレ 에 대해 말하는 것을 확인해 반영한다.
- Da mutant 의 업계 이름 Daタイプ 처리.

## 비범위
- `TraitCategory` 변경(miyuki → 광택 축), `vocabulary.py`·`models.py` 변경, 새 predicate, ADR.
- 품종명 층, 조사 CSV 의 미수집 용어(シルバー 등 55종) 추가.
- longfin 에 업계 라벨 부여.
- native speaker 검토 자체.

## 승격 기준 (japanese_name)
다음을 모두 만족할 때만 `japanese_name` 에 넣는다. 하나라도 빠지면 `unverified_labels` + `UNVERIFIED_LABEL` 로 둔다.
1. 조사 CSV 의 출처(JMA, hinsyu-zukan 등) 가운데 하나 이상이 그 문자열을 그대로 싣는다.
2. 그 출처의 정의가 Kon Table 1 의 해당 형질 정의와 맞는다(문자열만 같은 것은 불충분).
3. 같은 문자열이 다른 형질을 뜻하는 충돌이 조사에 기록되어 있지 않다. 있으면 읽기(かな)를 함께 적어 해소될 때만 승격.

승격한 형질은 `UNVERIFIED_LABEL` 을 떼고 `BREEDER_ACADEMIC_LINK` 를 단다 — 'Kon 의 X = 업계의 X' 동일성은
출처가 말한 것이 아니라 우리가 이은 것이기 때문이다. 각 승격 옆 주석에 근거 출처 key 를 적는다.

## 수용 기준
- AC-1: JMA 매뉴얼이 `01-sources-breeder.yaml` 에 `:Paper` 로 있다. URL, 접근일, 무엇을 말하고 무엇을 말하지 않는지가
  notes 에 있다. "NOT CITED, DELIBERATELY" 주석이 '읽었다'는 현재 상태로 다시 쓰여 있다.
- AC-2: Kon 형질 가운데 승격 기준을 만족하는 것은 `japanese_name` 을 갖고, 만족하지 않는 것은 그 이유가 주석에 있다.
  최소한 다음이 반영된다: hikari → ヒカリ, kuroaka → 赤黒, kurobuchi 黒斑 확인. 조사가 "일치"로 확인한 20개 표기
  (オロチ, オーロラ, 三色, ヒメダカ·黄, パンダ, 白, 青, 幹之, ラメ, 紅白, 楊貴妃, 透明鱗, アルビノ, ダルマ, 半ダルマ, ヒレ長,
  スワロー, 出目, 水泡眼, カガミ鱗) 각각이 승격 또는 사유 주석을 갖는다.
- AC-3: 근거가 약한 것은 승격하지 않는다. tenme 는 天眼 을 빼고 スモールアイ·点目 를 `unverified_labels` 에 둔다(点目 는 단일 출처).
  akabuchi·nijikin 은 "업계 표기 없음" 주석, fusahire 의 房ヒレ 는 그대로, longfin 은 무라벨 유지.
  fukumaku(腹膜青)·black(ブラック)·gold(黄金 おうごん) 는 승격 기준 2·3 을 따져 결정하고 판정을 주석과 rulings 에 남긴다.
- AC-4: hikari description 을 Kon 2026 Table 1 원문(PMC12915790)과 대조하고 해당 셀을 보고에 인용한다.
  Kon 이 anal 이면 seed 의 전사 오류로 고친다. Kon 이 pelvic 이면 description 은 그대로 두고 JMA·hinsyu-zukan 과의
  불일치를 주석으로 남긴다.
- AC-5: Da mutant 의 `aliases` 는 바꾸지 않는다. Daタイプ 는 업계가 ヒカリ体型 을 부르는 말이지 lab mutant 의 이름 변형이
  아니므로(PRD §8) hikari 쪽 주석에만 기록한다.
- AC-6: kagamirin·fusahire 에 대해 JMA 매뉴얼의 해당 서술을 확인한다. 뒷받침하면 JMA 를 evidence 로 추가하고,
  다르게 말하면 불일치를 기록하고, 언급이 없으면 notes 에 그렇게 적는다.
- AC-7: miyuki 의 category 는 바꾸지 않는다. BODY_COLOR vs JMA 体外光 불일치를 ADR 후보로 보고에 올린다.
- AC-8: `python -m medaka_ontology.cli validate` 와 `pytest` 가 통과한다. 건너뛴 테스트가 있으면 이름과 사유를 적는다.
  seed 에서 생성되어 커밋되는 산출물(`data/dossier/` 등)이 이번 변경으로 달라져야 하면 재생성하거나, 못 하면 사유를 보고한다.

## 열린 결정
- 권위 순서(JMA > 도감 > 번식장 > 블로그)는 잠정. 이번 작업은 이 순서를 승격 기준 1 의 출처 선택에만 쓴다.
- miyuki 의 광택 축 도입 여부(ADR).

## 변경 이력
- 2026-09-29 이전 spec(브리딩 용어 전수 목록, AC-1..AC-7 전부 통과)은 `.harness/archive/spec-breeder-vocabulary-2026-09.md` 로 옮겼다.
