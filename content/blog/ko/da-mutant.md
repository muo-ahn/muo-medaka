---
trait: da-mutant
category: BODY_SHAPE
evidence_badge: causal
sources:
  - doi: 10.1093/molbev/msag021
  - doi: 10.1016/j.cub.2012.01.063
  - doi: 10.1016/j.mod.2004.04.006
  - doi: 10.1242/dev.088567
status: draft
---

# Double anal fin — 히카리의 유전학이 실제로 만들어진 곳

> **한 줄 요약**: Da 는 관상 품종이 아니라 **실험실 돌연변이체**다. 배쪽 절반이
> 측면 정중선을 기준으로 거울상 복제되고, 원인은 *zic1/zic4* 인핸서에 끼어든
> 트랜스포존 삽입이다. [히카리](hikari.md)가 가진 🟢 근거는 이 계통에서 만들어졌다.
>
> **근거 등급: 🟢 원인 규명**

## 어떤 물고기인가 — 파는 물고기가 아니다

이 글은 품종 소개가 아니다. Da(Double anal fin)는 브리더가 고정한 계통이 아니라
유전학 실험실이 잡아서 이름을 붙이고 분석한 돌연변이체다. 이 시리즈에 들어와
있는 이유는 하나다 — **관상 품종 히카리의 근거가 이 물고기에서 나왔기 때문**이다.

기재는 한 문장으로 끝난다. 배쪽 절반이 측면 정중선을 기준으로 **거울상으로
복제된다.** 등 쪽에 있어야 할 것 대신 배 쪽의 것이 한 벌 더 서는 몸이다.
이름에 "항문지느러미가 둘" 이 들어간 것도 그래서지만, 이름의 유래를 논문이
따로 적어주지는 않았으니 여기까지는 이름과 기재를 맞춰 읽은 것으로 남겨 둔다.

![](img/da-mutant.jpg)

이 저장소가 Da 에 기록한 표현형 항목은 **하나**다 — 등/배 정체성 전환.
히카리 쪽에는 항목이 둘이고, 두 번째가 등의 은빛(이소성 홍색소포)이다.
기록에 없다는 것이 물고기에 없다는 뜻은 아니지만, 두 항목의 기재를
지느러미 단위로 맞춰본 근거는 이 저장소에 없다.

## 어디까지 밝혀졌나

Da 의 근거는 GWAS가 아니라 **세 편의 기능 연구**로 쌓였다. 연관 구간 숫자도,
구간 안 유전자 개수도 없다. 이 시리즈에서는 드문 모양이다.

**① Ohtsuka 등 (2004) — 자리를 찾았다.** *zic1* 과 *zic4* 가 Da 좌위 안에 있다는
것을 밝히고, 두 유전자를 몸통-꼬리 영역의 등/배 패턴 형성에 연결했다.

**② Moriyama 등 (2012) — 병변을 찾았다.** *zic1/zic4* 인핸서 영역에 끼어든 큰
트랜스포존이 두 유전자의 전사를 **중배엽에서만** 잃게 만든다. 같은 논문은 이
삽입이 diphycercal 형 꼬리 골격까지 만든다고 적는다. 인핸서가 망가진 것이므로
유전자 자체가 없어진 것과는 다른 종류의 변이다.

**③ Kawanishi 등 (2013) — 무엇이 망가졌는지 보였다.** *zic1/zic4* 발현이 체절의
**등쪽 절반에서만** 사라진다. 여기서 두 유전자는 등쪽 모듈의 **선택자
유전자(selector gene)** 로 규정된다. Da 는 "유전자가 고장난 돌연변이체" 가 아니라
**인핸서 돌연변이체**이고, 그래서 손실이 조직 단위로 끊긴다.

| 대상 | 관계 | 근거 등급 | 내용 |
|---|---|---|---|
| *zic1/zic4* 인핸서 트랜스포존 삽입 | 원인 변이 | 🟢 원인 변이 | 인핸서 삽입 → 중배엽 특이적 전사 손실 |
| *zic1* | 연관 유전자 | 🟢 기능 검증 | 20번 염색체. 체절 등쪽 절반에서 발현 소실 |

## 히카리와 같은 것인가 — 이 저장소가 답을 미루는 이유

근거는 꽤 멀리 갔다. Kon 등(2026)은 히카리의 chr20 피크가 *zic1/zic4* 자리와
겹친다고 적고, **Da 에서 알려진 그 삽입이 히카리 35마리 전부에서 확인됐다**고
적는다. 여기까지 읽으면 "히카리 = Da" 라고 쓰고 싶어진다.

그런데 이 저장소는 둘을 별개 항목으로 두고 `putatively_same_as` — "같을 수도
있다" 관계만 걸어 둔다. 이유는 근거가 약해서가 아니라 **두 문장이 다른 종류의
진술이기 때문**이다(PRD §8).

- "이름이 같은 병변을 공유한다" → 35마리 전원 확인. 관찰 사실이다.
- "같은 유전적 배경이다" → 계통의 역사, 배경 변이, 다른 좌위의 기여까지
  포함하는 주장이다. 히카리는 브리더가 오래 고정해 온 계통이고, Da 는 단일
  병변으로 정의된 실험실 계통이다. 계통의 역사가 다르면 같은 병변을
  공유하면서도 배경은 다를 수 있다.

두 번째 문장을 하려면 첫 번째와 다른 증거가 필요하다. 그 증거가 오면 이
저장소는 관계를 승격시키면 되고, 그때까지는 승격하지 않는다. 브리더 형질과
학술 계통을 잇는 주장은 이 저장소에서 자동으로 통과되지 않고 사람 검토
대기열에 올라간다 — 히카리 쪽에 걸린 검토 대기 7건 중 하나가 정확히 이것이다.

같은 이유로 이 저장소는 관상 품종 [판다](panda.md)와 실험실 돌연변이체
`panda (pa)` 도 별개로 둔다. 구조가 같은 결정이다.

## 아직 모르는 것

- **히카리와의 동일성.** 위에 쓴 그대로다. 삽입 공유는 확인됐고, 배경 동일성은
  주장되지 않았다.
- **은빛.** Da 쪽 기록에는 홍색소포 항목이 없다. *zic1/zic4* 손실이 등에
  홍색소포를 만드는지를 직접 본 실험은 이 저장소의 근거 목록에 없다.
- 이 형질에 걸린 근거 3건이 사람 검토 대기 상태다(NEW_CAUSAL_VARIANT).

## 출처

- Ohtsuka 등 (2004) Possible roles of zic1 and zic4, identified within the
  medaka Double anal fin (Da) locus, in dorsoventral patterning of the
  trunk-tail region. *Mech Dev*.
  [doi:10.1016/j.mod.2004.04.006](https://doi.org/10.1016/j.mod.2004.04.006)
- Moriyama 등 (2012) The medaka zic1/zic4 mutant provides molecular insights
  into teleost caudal fin evolution. *Curr Biol*.
  [doi:10.1016/j.cub.2012.01.063](https://doi.org/10.1016/j.cub.2012.01.063)
- Kawanishi 등 (2013) Modular development of the teleost trunk along the
  dorsoventral axis and zic1/zic4 as selector genes in the dorsal module.
  *Development*.
  [doi:10.1242/dev.088567](https://doi.org/10.1242/dev.088567)
- Kon T. *et al.* (2026) Genomic consequences of domestication and the
  diversification of body coloration and morphology in ornamental medaka
  strains. *Mol Biol Evol* 43(2):msag021.
  [doi:10.1093/molbev/msag021](https://doi.org/10.1093/molbev/msag021)
