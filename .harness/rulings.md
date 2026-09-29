# Rulings

- R-01 [2026-09-28] 산출물을 seed가 아닌 docs/research/ 에 둔다 / 사용자 요청은 "나열과 매핑"이고 ontology 편입은 다음 단계 / 파일을 data/seed 로 옮기면 된다
- R-02 [2026-09-28] 수집을 축별 3개 lane(색·광택 / 형태 / 품종명·수식어)으로 병렬화한다 / 축이 독립적이고 품종명은 조합이라 따로 모으는 게 매핑에 유리 / 단일 수집으로 합치면 된다
- R-03 [2026-09-28] 한국어 표기 열을 포함한다 / 사용자 언어이고 한국 시장은 일본어 음차를 쓴다 / 열을 지우면 된다
- R-04 [2026-09-28] 출처 등급을 도메인으로 매긴다: 1 JMA / 2 hinsyu-zukan·medakazukan·piscesbook / 3 샵·번식장(GEX 포함) / 4 블로그·위키·포럼·practical-aqualabo·medakapedia(자동 생성 흔적), PMC는 학술로 따로 / spec의 잠정 순서를 기계적으로 적용하려면 도메인 표가 필요 / build_vocab.py 의 DOM_TIER 를 고치면 된다
- R-05 [2026-09-28] 수집표 kind=OTHER 19행을 네 kind로 옮긴다: 색소포·구아닌 등 생물학 용어는 JARGON, 색·무늬 별칭(シルキー, スケルトン, 墨 …)은 TRAIT, 黒ラメ는 STRAIN / AC-2 는 네 kind 만 허용 / OTHER_KIND 표를 고치면 된다
- R-06 [2026-09-28] 병합 시 kind·axis 가 갈리면 다수결, 동률이면 kind 는 TRAIT>MODIFIER>JARGON>STRAIN, axis 는 그 축을 맡은 lane 의 값. 갈린 값은 notes 에 남긴다 / 같은 이름의 형질과 품종이 있을 때 형질 쪽이 더 일반적인 뜻 / KIND_PREF·FILE_AXES 를 고치면 된다
- R-07 [2026-09-28] 형태 lane 의 強光 은 強光（ヒカリの形質補足）, 품종 lane 의 強光 은 強光（幹之グレード）로 보내 두 뜻 행으로 둔다. 黒メダカ（クロメダカ）·ヒメダカ（緋目高）는 괄호 없는 행에 합친다 / 한 단어가 두 축에 걸친 충돌을 한 행에 섞지 않기 위해 / ROUTE 표를 지우면 된다
- R-08 [2026-09-28] 관계 목적어 해석에 별칭을 쓴다: 黒→ブラック, 3色→三色, 白ラメ→ラメ（白）, 多色ラメ→ラメ（多色）, 白錦→白斑. 鮮紅 의 공식명 青ラメ 는 青ラメ 행(라메 색)에 묶지 않는다 / JMA 는 2색 표기에서만 ブラック 을 黒으로 쓴다 / ALIAS·NO_RESOLVE 를 고치면 된다
- R-09 [2026-09-28] 출처 명시 관계의 basis URL = 그 수집 행의 출처 중 로컬 본문(JMA 매뉴얼, practical-aqualabo)에서 목적어가 확인되는 첫 URL, 없으면 확인 불가한 첫 URL(JMA 형질표 제외). contrasts·related·derived_from 190행은 닫힌 집합 밖이라 버린다 / 수집표가 관계별 URL 을 따로 적지 않았다 / pick_url 을 고치면 된다
- R-10 [2026-09-28] 출처에 찍힌 표기 변형 6개(クロメダカ, 緋目高, ヒレナガ, 背びれなし, ビックアイ, 曜変天目)에 행을 주고 variant_spelling 으로 잇는다 / variant_spelling 은 양끝 id 가 필요하다 / VARIANT_ROWS 를 비우면 된다
- R-11 [2026-09-28] 強光（ヒカリの形質補足）와 銀帯 의 axis 를 BODY_SHAPE 로 둔다(색 lane 은 LUSTER) / JMA 가 ヒカリ 체형의 形質補足 으로 분류 / AXIS_OVERRIDE 를 비우면 된다
- R-12 [2026-09-28] broader/narrower 는 SKOS 방향(A narrower B = B 가 A 보다 좁다). 수집표 contains→narrower, contained_in→broader. JMA 의 X（Y） 표기는 X narrower X（Y） 로 추론 / 방향을 한 가지로 고정해야 표가 읽힌다 / 관계 방향을 뒤집으면 된다
- R-13 [2026-09-28] seed 대응 중 akabuchi→白朱赤, kuroaka→黒オレンジ, fukumaku→腹膜青·腹膜光, gold→黄金, tenme→スモールアイ·点目, Da mutant→Daタイプ·ヒカリ 는 정의 대조 추론으로 두고 basis 를 inferred 로 표시. longfin 은 seed_match 가 아니라 collides_with / 같은 이름이 없거나 이름이 같아도 정의가 다르다 / build_vocab.py 의 SEED 표를 고치면 된다
- R-14 [2026-09-28] AC-6 검증에서 출처 본문에 표기가 없던 上物(bv:0277)은 행을 지우지 않고 unverified 에 "출처 본문에 표기 없음" 을 달고 notes 에 검증 결과를 남긴다 / 추론으로 생긴 행이 검증된 것처럼 보이면 안 되지만, 실제 인쇄 출처를 찾으면 살릴 수 있다 / build_vocab.py 의 TERM_FLAGS 에서 빼면 된다
- R-15 [2026-09-28] 홍색소포(虹色素胞, iridophore)가 적색소포(紅色素胞)로 읽히지 않도록 md 에 용어 주의를 두고, CSV definition 에서는 행마다 첫 "홍색소포" 를 "홍색소포(虹, 구아닌 반사)" 로 바꾼다(16행; notes 는 원문 유지) / 용어 자체는 맞으니 바꾸지 않고 풀이만 붙인다 / IRIDO_GLOSS 치환을 지우면 된다
- R-16 [2026-09-29] 빌드 스크립트를 임시 scratchpad에서 scripts/vocab/ 로 복사해 커밋 대상에 넣는다; raw/ (제3자 원문)는 .gitignore 에 추가해 디스크에만 남긴다 / docs/research/ 의 CSV가 재생성 가능해야 하는데 scratchpad는 세션 종료 시 사라진다 / scripts/vocab 삭제 + .gitignore의 scripts/vocab/raw/ 줄 삭제로 되돌린다
