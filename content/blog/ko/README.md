# 관상 메다카 형질 시리즈 — 한국어 블로그 초안

`data/dossier/*.md` 의 형질 도시에(dossier) 한 건이 글 한 편이 된다. 도시에는
근거와 그 근거의 강도를 같이 들고 있고, **이 시리즈의 존재 이유는 그 강도를
독자에게 잃어버리지 않고 전달하는 것**이다. 관상어 커뮤니티에서 "이 품종은
무슨무슨 유전자" 라는 문장이 근거 등급 없이 돌아다니다가 사실로 굳는 것이
이 저장소가 막으려는 실패다. 글에서도 같은 것을 막는다.

## 근거 등급 표기

글 맨 위에 배지 한 줄을 반드시 단다. 세 단계뿐이고, 도시에의
`Strongest evidence` 최댓값에서 기계적으로 결정된다.

| 배지 | 도시에 근거 등급 | 뜻 |
|---|---|---|
| 🟢 **원인 규명** | `CAUSAL_VARIANT`, `FUNCTIONAL_VALIDATION` | 변이를 재현했더니 형질이 나왔다 |
| 🟡 **후보 유전자** | `FINE_MAPPING`, `EXPRESSION_ASSOCIATION` | 유전자 이름은 나왔지만 확정은 아니다 |
| ⚪ **구간만 확인** | `QTL_GWAS_ASSOCIATION`, `OBSERVATIONAL`, `UNKNOWN` | 염색체 어디쯤인지까지만 안다 |

배지는 도시에의 **`## Genetics` 표 `Strongest evidence` 열**에서만 읽는다.
`## Evidence` 절에는 다른 claim 의 등급과 비교 계층(다른 종의 실험) 등급까지
섞여 있어서, 그쪽을 보면 배지가 과대평가된다.

40편 중 🟢 는 **9편**이다 — albino, da-mutant, few-melanophore, fused-centrum,
guanineless, hikari, leucophore-free, orochi, yellow.

그리고 이 9편에서 시리즈의 가장 큰 사실이 나온다. **원인 근거가 2026년
관상 품종 GWAS 에서 온 것은 오로치 하나뿐이다.**

| 형질 | 원인 근거의 출처 연도 |
|---|---|
| orochi | **2026** (편집 표현형 재현) |
| few-melanophore | 2020 |
| guanineless | 2017 |
| leucophore-free | 2014 |
| hikari / da-mutant | 2012 / 2004 |
| fused-centrum | 2010 |
| albino | 1995, 2006 |
| yellow | 2001 |

**관상 메다카에서 "이 유전자 때문"이라고 말할 수 있는 형질은, 대부분 관상
품종을 연구해서 밝혀진 것이 아니다.** 실험실 돌연변이체 연구가 먼저 답을
찾아 두었고 2026년 GWAS 가 그것을 품종에서 확인한 구조다. 시리즈가 반복해서
말해야 하는 것이 이 구조다.

(원논문이 새로 제시한 trait-gene 배정 26건만 따로 보면 🟢 는 오로치·히카리
둘이다. 저장소 루트 README 의 그 문장과 위 9편은 세는 범위가 다르다.)

## 용어 대응표

원문 용어를 한국어로 옮길 때 글마다 흔들리면 안 되므로 여기서 고정한다.

| 영문 | 한국어 | 비고 |
|---|---|---|
| melanophore | 흑색소포 | 첫 등장 시 원어 병기 |
| xanthophore | 황색소포 | |
| iridophore | 홍색소포(구아닌 색소포) | 반짝임의 원인. 애호가 표현 "라메/광" 과 연결 |
| leucophore | 백색소포 | 메다카 특유. 제브라피시에 없음 |
| GWAS | 전장유전체 연관분석 | 첫 등장 시 영문 병기 |
| best P | 최고 P값 | **작은 P ≠ 강한 근거.** 아래 참조 |
| QTL interval | 연관 구간 | |
| candidate gene | 후보 유전자 | "원인 유전자" 로 쓰지 않는다 |
| functional validation | 기능 검증 | 유전자 편집으로 표현형 재현 |
| causal variant | 원인 변이 | |

## P값을 크기순으로 읽지 않는다

시리즈 전체에 걸리는 독법이다. 후쿠마쿠는 개체 **4마리**에서
P = 5.71 × 10⁻⁵⁹ 가 나왔고 구간 안에 유전자가 198개 있다. 라메는 **47마리**에서
P = 1.33 × 10⁻⁹, 유전자 38개, 후보 지목 0건이다. 천문학적으로 작은 P값은
근거의 강도가 아니라 **표본이 작다는 사실**을 반영할 수 있다.

그래서 P값은 **반드시 개체 수와 구간 내 유전자 수를 옆에 붙여서** 쓴다.
셋 중 하나만 떼어 쓴 문장은 이 시리즈의 문장이 아니다.

## 쓰지 않는 표현

- "**~때문이다**" → 🟢 아니면 쓰지 않는다. 🟡 이하는 "**후보로 지목됐다**".
- "**교배하면 나온다**" → 이 저장소는 교배 예측을 하지 않는다(PRD §14).
  유전 양식 언급은 원논문 Table 1 기재 사항까지만.
- 일본어 표기(オロチ 등)는 **출처 없는 재구성**이다. 본문에 쓰되 각주로
  "원논문에 일본어 표기 없음" 을 단다.

## 파일

40개 도시에 = 40편. `_template.md` 는 틀, 이 파일은 규칙이다.

먼저 쓴 기준점 3편:

| 파일 | 배지 | 왜 먼저 썼나 |
|---|---|---|
| `orochi.md` | 🟢 | 최고 등급이 어떻게 생겼는지의 기준점 |
| `panda.md` | ⚪ (충돌) | 근거가 싸우는 형질을 어떻게 쓰는가 |
| `miyuki.md` | ⚪ | 대다수가 여기 해당 |

나머지 37편은 주제 클러스터로 묶어 작성했다. 클러스터가 곧 상호 참조
단위다 — §헷갈리기 쉬운 것 절이 서로를 가리키기 때문에 같은 묶음 안에서
써야 경계가 어긋나지 않는다.

| 클러스터 | 형질 |
|---|---|
| 고전 색소 좌위 | albino 🟢, yellow 🟢, white, black, gold |
| 홍색소포·투명 | guanineless 🟢, toumeirin, fukumaku, nijikin, blue, rame |
| 복합 무늬 | ywko, akabuchi, kurobuchi, sanshoku, kouhaku, kuroaka, blackrim, yokihi |
| 체형 | hikari 🟢, da-mutant 🟢, fused-centrum 🟢, daruma, handaruma |
| 지느러미 | hirenaga 🟡, longfin, reallongfin, swallow, nodorsalfin |
| 눈 | deme 🟡, bigeye, tenme, suihougan |
| 색소세포 돌연변이체 | few-melanophore 🟢, leucophore-free 🟢, aurora 🟡, panda-pa-lab-mutant |

브리더 품종이 아니라 **실험실 돌연변이체**인 항목: `da-mutant`,
`few-melanophore`, `fused-centrum`, `guanineless`, `leucophore-free`,
`panda-pa-lab-mutant`. 이들은 "품종 소개"가 아니라 "이 품종들의 실험실 짝"
장르로 쓴다.

## 검사

초안을 고친 뒤에는 기계 검사를 돌린다. 사람이 볼 수 없는 종류의 실패를
잡는다.

- 배지가 도시에 `Strongest evidence` 최댓값과 일치하는가
- 본문의 좌표·P값·개체 수·유전자 수가 **어느 도시에에도 없는 값이 아닌가**
  (조작 검사. 다른 형질 도시에의 값을 교차 인용하는 것은 정상)
- `## 아직 모르는 것` 절이 있는가
- 일본어 표기가 해당 도시에의 unverified labels 안에 있는가
- 상대 링크가 실재하는 파일을 가리키는가
- `category` 가 `vocabulary.py` 의 `TraitCategory` 정본 값이고 도시에와 같은가
