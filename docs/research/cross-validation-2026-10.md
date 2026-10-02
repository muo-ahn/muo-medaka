# 교배 질의 검증 (2026-10)

유전 층(ADR 0006)이 **발표된 교배를 재현할 만큼 표현력이 있고 정직한지** 확인한 기록이다. spec AC-7, AC-8.
테스트는 `tests/test_genetics.py`, 질의는 `python -m medaka_ontology.cli cross`.

**범위.** 이 기록은 질의를 처음 만들 때(ADR 0006)의 검증이다. 2026-10-02 사용자 결정으로 자손 형질 예측은 정식
기능이 되었다(ADR 0007, PRD §14). 교배 추천·전략·개체 관리는 여전히 비목표다. 아래 수치는 그대로이며 테스트가
고정한다. 질의는 seed 의 claim 만 읽으며(Neo4j 없이 돈다), seed 가 말하지 않은 것은 알지 못한다.

## 모형이 읽는 것

| 규칙 | 읽는 claim | 이 검증에서의 값 |
|---|---|---|
| 좌위와 대립유전자 | `allele_of` | b 좌위(slc45a2) B/b, r 좌위 R/r, i 좌위(tyr) I/i, pd, d, … |
| 우열 | `dominant_over` | B > b, R > r (sasano2012 Methods 문장), I > i 등은 INFERRED |
| 성연관 | `inherited_as sex-linked` | r 좌위. 수컷 유전자형은 X 대립유전자, Y 대립유전자 순 |
| 형질 | `requires_allele` | yellow = b/b + R, white = b/b + r/r, blue = B + r/r (sasano2012 Table 3) |
| 가림 | `masks` | albino → blue, albino → panda (JMA) |
| 구성 | `composed_of` | seethrough = albino + panda (JMA §3.8.10) |

가정(출력이 매번 밝힌다): 성비 1:1(XY, dmy 가 Y), 성연관이 아닌 좌위는 독립 분리, r 좌위와 성 결정 좌위는 완전 연관
(재조합 0 — 출처에 비율이 없어서 spec 이 정한 값), 지정하지 않은 좌위는 야생형 동형.

## (a) Hayasaka 2019: Hd-rRII1 계통 유지 교배

원문(PMC6382872): "The allele R of the r locus (a sex-linked pigment gene) is located on the Y chromosome. In this
strain, X r X r females have a white body color, whereas X r Y R males have an orange-red body color."

```
cross --mother "b/b r/r" --father "b/b r/R"        (어미 X^r X^r, 아비 X^r Y^R)
딸   100%  white          아들  100%  yellow
```

계통을 유지하는 교배의 결과는 딸 전부 흰색, 아들 전부 주황이다. 재현됐다.

**이 일치가 말하는 것.** R 이 Y 에 있다는 것은 입력이므로(claim 으로 seed 에 들어 있다) 이 결과는 모형이 그 입력을 올바르게
읽는다는 확인이지 독립된 관찰의 시험이 아니다. 음성 대조로, 같은 질의에서 r 좌위를 상염색체로 바꾸면 딸이 전부 흰색이
아니다(테스트가 확인한다). 성연관 claim 이 결과를 만든다.

## (b) Sasano 2012: Cross I 역교배

원문(PMC3467165): 교배는 (Actb-SLa:GFP × Hd-rr) × Hd-rr(암 × 수). Methods 에서 "The Ci SLa+ B, and R alleles are dominant to
the ci SLa– b, and r alleles, respectively." 이고 "none of the four loci were linked to each other".
Actb-SLa:GFP 는 B/B R/R, Hd-rr 은 b/b 이고 "identical to the Hd-rR inbred strain except that its Y chromosome has
the mutated r allele" (수컷 X^r Y^r).

F1 암컷은 B/b, X^R X^r 이고 이것을 Hd-rr 수컷(b/b, X^r Y^r)에 교배한다.

```
cross --mother "B/b R/r" --father "b/b r/r"
각 성별 :  blue 1/4   none(야생형) 1/4   white 1/4   yellow 1/4
B 보유 1/2, R 보유 1/2 (각 성별에서)
```

Table 4 의 관측(78마리 F2)과 1:1 의 적합도:

| 기준 | 관측 (있음:없음) | n | χ² (df 1) | P |
|---|---|---:|---:|---:|
| B 대립유전자, 수컷 | 32 : 23 | 55 | 1.47 | 0.225 |
| B 대립유전자, 암컷 | 15 : 8 | 23 | 2.13 | 0.144 |
| B 대립유전자, 전체 | 47 : 31 | 78 | 3.28 | 0.070 |
| R 대립유전자, 수컷 | 25 : 19 | 44 | 0.82 | 0.366 |
| R 대립유전자, 암컷 | 12 : 8 | 20 | 0.80 | 0.371 |
| R 대립유전자, 전체 | 37 : 27 | 64 | 1.56 | 0.211 |
| **성비 (Y 유전자)** | **55 : 23** | 78 | **13.13** | **0.0003** |

R 은 "판정 불가" 14마리(수컷 11, 암컷 3)를 뺀 값이다. B 와 R 은 예측 비율과 맞는다(P > 0.05, 전체 B 는 경계).
**성비는 맞지 않는다.** 55 대 23 은 1:1 에서 크게 벗어나고, 이 편차를 b·r 좌위로 설명할 수 없다. 둘 다 성 결정과 무관한
좌위이고, sasano2012 는 그에 대해 아무 말도 하지 않으며, 이 온톨로지에 그 편차를 낼 claim 도 없다. 설명하지 않고 보고만
한다.

**이 일치가 말하는 것.** 역교배의 1:1 은 모형이 약해도 나오는 예측이라 변별력이 낮다. 이 검증이 확인하는 것은
(i) 유전자형 → 형질 변환이 Table 3 의 표현형 분류와 일관되는 것, (ii) 관측이 예측에서 크게 벗어나지 않는 것, (iii) 벗어난 곳
(성비)을 숨기지 않는 것이다. Table 4 는 한계 분포만 주므로 네 형질 클래스의 결합 분포(1/4씩)는 관측과 비교하지 못했다.

## (c) 성연관 때문에 9:3:3:1 이 깨지는 예

yellow 암컷(b/b, X^R X^R) × blue 수컷(B/B, X^r Y^r). F1 은 전부 B/b 이고 야생형이다.

```
F1 암컷 B/b R/r  ×  F1 수컷 B/b X^R Y^r        (cross --mother "B/b R/r" --father "B/b R/r")
F2 암컷 : 야생형 3/4,  yellow 1/4,  blue 0,  white 0
F2 수컷 : 야생형 3/8,  blue 3/8,  yellow 1/8,  white 1/8
```

r 이 상염색체라면 양쪽 성에서 야생형 9/16, blue 3/16, yellow 3/16, white 1/16 이다. 성연관이면 F2 암컷은 아비에게서 X^R 을
받으므로 R 을 항상 가져 blue 와 white 가 나올 수 없고, 수컷은 3:3:1:1 로 갈라진다. 테스트는 두 분포를 모두 단언한다.

이 예는 **관측 수치와 비교한 것이 아니라 모형의 예측**이다. 발표된 F2 계수는 쓰지 않았다.

## 그 밖의 확인

- **seethrough 1/16.** albino(i/i)와 panda(pd/pd)의 F1 은 I/i pd+/pd 이고 F1 끼리 교배하면 야생형 9/16, albino 3/16,
  panda 3/16, seethrough 1/16 이다. seethrough 가 발현되면 부분(albino, panda)을 흡수해서 따로 세지 않는다.
- **albino 의 가림.** i/i B/B r/r 는 genotype 상 blue 지만 albino 만 보인다(`masks`, JMA §3.3.1).
- **다인자 거부.** orochi·miyuki 는 "not predictable (multilocus, kon2026)" 이고, 표현형 입력에 넣으면 거부한다. aurora 같은
  형질은 "유전 데이터 없음"이라고 한다.
- **증거 수준.** 예측한 형질마다 근거 claim 중 가장 약한 것이 같이 나온다. yellow·white 는 OBSERVATIONAL(sasano2012 Table 3),
  albino·seethrough 는 INFERRED(우열이 Table 1 의 Recessive 에서 추론한 것), reallongfin 은 BREEDER_OBSERVATION(himemedaka_rlf).

## 한계

1. 발표된 교배 중 **독립 관측으로 모형을 시험한 것은 (b)의 한계 분포뿐**이다. (a)는 출처의 진술, (c)는 예측이다.
2. seed 가 모르는 좌위(예: 다른 알비노 좌위 oca2)는 모형에 없다. albino 두 부모가 서로 다른 좌위를 가졌다면 F1 이 야생형일
   수 있다는 가정이 출력에 적힌다.
3. 재조합 0 은 가정이다. r 과 성 결정 좌위 사이에 재조합이 있으면 (a)의 "100%"는 깨진다.
4. 표현형 입력의 가설 집합은 닫힌 집합(보이는 형질의 좌위, 그 좌위를 쓰는 형질, 그것들을 가리는 형질의 좌위)이고 나머지
   좌위는 야생형 동형이다(R-61).
