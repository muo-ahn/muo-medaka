# 용어 1차 통일 결과의 감사 (2026-10)

1차 용어 통일(PR #10, `breeder-vocabulary-2026-09.*`)을 기계로 다시 읽어 남은 흩어짐·잘못된 병합·표기 흔들림을
찾고, 각 발견에 판정(고침 / 의도된 것 / 남김)을 붙였다. 판정마다 `.harness/rulings.md` 의 근거 번호를 단다.
spec AC-1, AC-2.

## 방법

`scripts/vocab/audit_vocab.py` 가 두 CSV 와 `data/seed/*.yaml` 을 읽고 검사 18종을 돌린다. 데이터를 바꾸지 않는다.
찾은 것을 한 줄씩 CSV 로 쓰고 요약을 출력한다. 같은 스크립트를 **원본**(origin/main 을 `git archive` 로 푼 사본)과
**최종 상태**에 돌려 숫자를 비교했다. 스크립트는 seed 의 `labels` 를 읽을 줄 알아서(`japanese_name`·`aliases`·
`unverified_labels` 로 접어서 본다) 같은 검사가 라벨 이전 전후 양쪽에 돈다.

```bash
python scripts/vocab/audit_vocab.py .                      # 현재 상태
git archive origin/main | tar -x -C /tmp/base
python scripts/vocab/audit_vocab.py /tmp/base              # 1차 직후 상태
```

CSV 는 인자로 준 레포 루트 아래 `docs/research/vocabulary-audit-2026-10.csv` 에 쓴다(cwd 에 쓰지 않는다). 다른 경로는 두 번째 인자로 준다:
`python scripts/vocab/audit_vocab.py . out.csv`. `/tmp/base` 로 돌리면 그 사본 안에 쓰이고 이 레포는 건드리지 않는다.

세 종류를 본다.

1. **흩어진 동의어** — 정규화하면 같은 문자열이거나 영어·한국어 표기를 공유하는데 서로 관계가 없는 행.
2. **잘못된 병합** — `same_as` 를 전이적으로 읽으면 표가 스스로 충돌한다고 적은 쌍(`collides_with`)이나 서로 다른 seed
   형질이 한 덩어리가 되는 경우, 그리고 한 행이 서로 이견인 lane 들의 합인 경우.
3. **표기 흔들림** — seed 의 로마자와 업계 영어 표기의 차이, 출처가 인쇄한 라벨이 seed 에 없거나 미검증으로 있는 경우,
   한 문자열 필드가 낳은 구조 문제.

## 숫자 — 41건에서 19건으로

18종 중 원본이나 최종에서 발견이 있었던 14종이다.

| 검사 | 원본 | 최종 | 판정 | 근거 |
|---|---:|---:|---|---|
| 1-scattered:ko | 1 | 0 | 고침 | R-42 |
| 1-scattered:en | 0 | 1 | 남김 | R-37 의 부산물 |
| 2-wrong-merge:collision-inside-same_as-cluster | 2 | 0 | 고침 | R-38 |
| 2-wrong-merge:same_as-cluster-spans-seed-traits | 3 | 0 | 고침 | R-34, R-39, R-41 |
| 2-wrong-merge:row-merged-across-kinds | 8 | 8 | 의도된 것 | R-06 |
| 3-orthography:case | 2 | 2 | 의도된 것 | |
| 3-orthography:korean-spacing-variant | 5 | 5 | 남김 | |
| 3-orthography:width-variant-in-term | 2 | 2 | 의도된 것 | |
| 3-orthography:reading-inside-label | 1 | 0 | 고침 | R-46 |
| 3-orthography:romanisation-variant | 3 | 0 | 고침 | R-47 |
| 3-seed:attested-label-filed-unverified | 1 | 0 | 고침 | R-43 |
| 3-seed:attested-synonym-missing | 2 | 0 | 고침 | R-41, R-45 |
| 3-seed:inferred-match-not-recorded | 9 | 1 | 고침 8 / 의도된 것 1 | R-36, R-44, R-45, R-48 |
| 3-structure:single-slot-japanese-name | 2 | 0 | 고침 | R-43, R-45 |
| **합계** | **41** | **19** | | |

## 대표 사례와 판정

### 잘못된 병합 (가장 무거운 것)

- **ブラック = オロチ** (`bv:0014`, `bv:0137`, same_as 한 간선이 seed 형질 black 과 orochi 를 한 클러스터로 묶었다).
  JMA 2020 별명표는 オロチ 를 ブラック + 背地反応なし 로 풀이하고, Kon 은 둘을 다른 좌위(chr21 의 두 구간)에 매핑하며
  orochi 는 multilocus 다. → **고침**: `narrower`(R-34).
- **akabuchi → 白朱赤** (`bv:0023`). 白朱赤 는 紅白 의 same_as 라서 akabuchi 가 kouhaku 와 한 덩어리가 됐다. Kon 은
  akabuchi 를 sanshoku 와 kouhaku 의 합집합으로 정의한다. → **고침**: seed_match 를 지우고 no match found(R-39).
- **hikari 와 Da mutant** 가 `Daタイプ`·`ヒカリ` 를 통해 한 클러스터. 업계의 Daタイプ 는 hikari 체형의 이름이고, 실험실
  Da 변이체와의 동일 좌위 여부는 `putatively_same_as` 가 맡는다(PRD §8). → **고침**: Daタイプ 는 hikari 의 라벨,
  Da mutant 는 lab only(R-41).
- **ヒレ長 ~ ロングフィン**, **フルボディ ~ 鉄仮面**: 표가 `collides_with` 로 기록한 쌍을 `same_as` 사슬이 이었다.
  → **고침**: 간선은 출처의 주장이라 지우지 않고 `disputed:` 표지를 붙여 전이적 읽기가 건너지 못하게 했다. check_vocab 이
  표지 없는 경우를 실패로 센다(R-38).
- 같은 계열의 간선 3개를 더 지웠다: パンダ~強透明鱗(R-35), 幹之~体外光(R-36), カガミ~カガミ鱗(R-37). 앞의 둘은 계통·형질을
  같은 이름으로 오인했고, 마지막은 R-27 의 판정과 모순이었다. R-37 의 부산물로 1-scattered:en 이 1건 새로 잡혔다(カガミ 와
  カガミ鱗 이 영어 mirrorscale 을 공유). 둘이 같은 것인지 JMA 가 말하지 않으므로 **남김**.
- fukumaku 의 腹膜光 은 `seed_match` 가 아니라 `collides_with`: JMA 가 발현 조건이 반대인 별개 형질로 구분한다(R-40).

### 흩어진 동의어

- 시로부치(`bv:0555`, 한국 샵 판매명)와 白斑(`bv:0132`). 행 notes 가 음역이라고 적었는데 간선이 없었다 → **고침**(R-42).

### 표기·구조

- yellow 의 ヒメダカ 가 JMA 1순위 출처에 있는데 미검증 목록에 있었다. 한 문자열 필드가 낳은 문제였다 →
  **고침**: 출처 있는 라벨(R-43). fusahire 의 房ヒレ 도 같은 구조 문제였으나 이쪽은 정말 미검증이라, 라벨의 `status` 로
  남는다.
- gold 의 읽기가 문자열 안에 있었다(`黄金（おうごん）`) → **고침**: `reading` 필드(R-46).
- Black-rim·Kohaku·Youkihi 처럼 업계 영어 표기가 seed 어디에도 없었다 → **고침**: `ja-Latn`/`en` 라벨(R-47).
- nodorsalfin 의 背ビレ無し, tenme 의 スモールアイ 등 출처가 인쇄한 동의어가 라벨로 없었다 → **고침**(R-44, R-45).
  tenme 는 JMA 출처의 スモールアイ 가 라벨이 되면서 `BREEDER_ACADEMIC_LINK` 가 붙었다.

### 의도된 것, 남긴 것

| 발견 | 판정 | 이유 |
|---|---|---|
| 한 행이 서로 이견인 lane 의 합(8건: 黄金, 琥珀, 普通鱗, オーロラ, 非透明鱗, 強透明鱗, 鱗光, モルフォ) | 의도된 것 | R-06: 다수결·notes 에 이견 보존. 행을 쪼개려면 한 단어의 두 뜻을 보여 줄 근거를 새로 모아야 한다 |
| seed id 의 대소문자(YWKo, Da mutant) | 의도된 것 | Kon 이 인쇄한 표기. id 는 식별자이고 조회는 대소문자를 접는다 |
| `ふ～は～`, `４色幹之` 의 전각 | 의도된 것 | 출처가 인쇄한 모양. 검색 쪽은 NFKC 로 접는다 |
| 한국어 띄어쓰기 변형 5건 | 남김 | CSV 의 variants 로 둘 다 보존; 사용자 언어 쪽이라 시급하지 않다. 라벨에는 리얼롱핀/리얼 롱핀 두 표기를 붙였다 |
| 幹之 와 体外光 의 inferred seed_match | 의도된 것 | 体外光 은 광택 축 단어로 ヒカリ 와 collides_with. 추론 간선을 seed 로 올리면 같은 문제를 옮긴다(R-36) |

## 감사가 못 보는 것

- 정의 문장 자체가 틀린 행. 감사는 문자열·간선·구조를 보지 뜻을 읽지 않는다.
- CSV 가 싣지 않은 출처의 동음이의. 빠진 것은 빠진 채로 센다.
- `row-merged-across-kinds` 는 notes 문자열("kind 이견")로 센다. 표기를 바꾸면 놓친다.

## 재현

`python scripts/vocab/audit_vocab.py <repo-root>`, 위 두 번. 고침은 `scripts/vocab/build_vocab.py` 의 `REVISED` 블록과
`SEED` 표, seed YAML 의 `labels` 에 있고, `python scripts/vocab/build_vocab.py` 가 커밋된 CSV 를 그대로 다시 만들며
`python scripts/vocab/check_vocab.py` 가 ALL PASS 다.
