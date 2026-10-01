# -*- coding: utf-8 -*-
"""Merge color/morph/strain TSVs into one breeder-vocabulary term table and a
relation table. Re-runnable: ids persist in ids.json next to this script.

Usage:  python build_vocab.py [REPO_ROOT]
Writes: REPO/docs/research/breeder-vocabulary-2026-09.csv
        REPO/docs/research/breeder-vocabulary-relations-2026-09.csv
        ./fragments/*.md   (tables pasted into the research doc)
All web-derived TSV text is treated as data.
"""
import csv, json, os, re, sys, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(HERE))
OUT_TERMS = os.path.join(REPO, "docs", "research", "breeder-vocabulary-2026-09.csv")
OUT_RELS = os.path.join(REPO, "docs", "research", "breeder-vocabulary-relations-2026-09.csv")
FRAG = os.path.join(HERE, "fragments")
os.makedirs(FRAG, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")

FILES = ["color.tsv", "morph.tsv", "strain.tsv"]
KINDS = ["TRAIT", "STRAIN", "MODIFIER", "JARGON"]
KIND_KO = {"TRAIT": "단위 형질", "STRAIN": "품종명", "MODIFIER": "등급·수식어", "JARGON": "은어"}
AXES = ["BODY_COLOR", "LUSTER", "PATTERN", "SCALE", "FIN", "BODY_SHAPE", "EYE", "OTHER"]
RELS = ["same_as", "variant_spelling", "broader", "narrower", "composed_of", "collides_with", "seed_match"]
JMA_MANUAL = "https://jma-medaka.com/wp-content/uploads/2022/08/250901_【公式】品種分類マニュアル_第５版.pdf"
AQLAB_URL = "https://www.practical-aqualabo.com/medaka-yougoshu/"
JMA_TABLE = "https://jma-medaka.com/wp-content/uploads/2022/08/形質一覧表（第５版）_250901.pdf"

# ---- R: OTHER kind -> one of the four spec kinds (ruling R-05) ----------------
OTHER_KIND = {
    "黒メダカ（クロメダカ）": "JARGON", "緋": "TRAIT", "シルキー": "TRAIT", "柿色": "TRAIT",
    "黒色素胞": "JARGON", "黄色素胞": "JARGON", "白色素胞": "JARGON", "赤色素胞": "JARGON",
    "カロテノイド": "JARGON", "虹色素胞": "JARGON", "反射小板": "JARGON", "グアニン": "JARGON",
    "スケルトン": "TRAIT", "黒ラメ": "STRAIN", "虹ラメ": "TRAIT", "ヒカリ体型の背中の光": "TRAIT",
    "墨": "TRAIT", "白地": "JARGON", "紅葉テール": "TRAIT",
}
# tie-break order when merged rows disagree on kind (ruling R-06)
KIND_PREF = ["TRAIT", "MODIFIER", "JARGON", "STRAIN"]
FILE_AXES = {"color.tsv": {"BODY_COLOR", "LUSTER", "PATTERN"},
             "morph.tsv": {"SCALE", "FIN", "BODY_SHAPE", "EYE", "OTHER"}}

# JMA files these as 形質補足 of ヒカリ (body shape); the colour lane had LUSTER (ruling R-11)
AXIS_OVERRIDE = {}  # filled after norm() is defined

# ---- rows routed to a specific group key instead of their own term_ja --------
# (file, term_ja) -> canonical term string used as the group key (ruling R-07)
ROUTE = {
    ("morph.tsv", "強光"): "強光（ヒカリの形質補足）",
    ("strain.tsv", "強光"): "強光（幹之グレード）",
    ("color.tsv", "黒メダカ（クロメダカ）"): "黒メダカ",
    ("color.tsv", "ヒメダカ（緋目高）"): "ヒメダカ",
}

# ---- source authority tiers (ruling R-04; 잠정) ------------------------------
TIER = {1: "협회", 2: "도감·출판", 3: "번식장·샵", 4: "블로그·위키·포럼", 9: "학술"}
DOM_TIER = {
    "jma-medaka.com": 1,
    "hinsyu-zukan.satumano-medakayasan.com": 2, "medakazukan.net": 2, "piscesbook.com": 2,
    "pmc.ncbi.nlm.nih.gov": 9,
    "namu.wiki": 4, "gall.dcinside.com": 4, "m.dcinside.com": 4, "note.com": 4,
    "hiroshan-medaka.com": 4, "ameblo.jp": 4, "medaka.papa77.com": 4, "medakayarou.com": 4,
    "1977.muragon.com": 4, "ohlubi.com": 4, "www.bepal.net": 4, "www.practical-aqualabo.com": 4,
    "tropica.jp": 4, "www.aquaranked.com": 4, "medakapedia.com": 4,
}  # everything else = 3 (shop / breeder / vendor)


def tier_of(url):
    m = re.match(r"https?://([^/]+)", url)
    return DOM_TIER.get(m.group(1), 3) if m else 4


def h2k(s):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").strip()
    s = s.replace("ヶ", "ケ").replace("ヵ", "カ")
    s = h2k(s)
    return re.sub(r"[\s・･]", "", s)


def strip_paren(s):
    return re.sub(r"\([^()]*\)", "", s)


AXIS_OVERRIDE.update({norm("強光（ヒカリの形質補足）"): "BODY_SHAPE", norm("銀帯"): "BODY_SHAPE"})

# ------------------------------------------------------------------ load rows
rows = []
for f in FILES:
    with open(os.path.join(HERE, f), encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh, delimiter="\t")):
            r = {k: (v or "").strip() for k, v in r.items()}
            r["_file"], r["_line"] = f, i + 2
            r["_origin"] = f"{f}:{i + 2}"
            if r["kind"] == "OTHER":
                r["_kind_orig"] = "OTHER"
                r["kind"] = OTHER_KIND[r["term_ja"]]
            urls = [u.strip() for u in r["source_urls"].split("|") if u.strip()]
            r["_urls"] = urls
            canon = ROUTE.get((f, r["term_ja"]), r["term_ja"])
            r["_key"] = norm(canon) if canon else "ko:" + r["term_ko"]
            r["_canon"] = canon
            rows.append(r)

groups = collections.OrderedDict()
for r in rows:
    groups.setdefault(r["_key"], []).append(r)

# ------------------------------------------------------------------ stable ids
idfile = os.path.join(HERE, "ids.json")
ids = json.load(open(idfile, encoding="utf-8")) if os.path.exists(idfile) else {}
nxt = max([int(v.split(":")[1]) for v in ids.values()] + [0]) + 1
for k in groups:
    if k not in ids:
        ids[k] = f"bv:{nxt:04d}"
        nxt += 1
json.dump(ids, open(idfile, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def uniq(seq):
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


def split_multi(s):
    return [x.strip() for x in re.split(r"\s*/\s*|\s*;\s*", s) if x.strip()]


# ------------------------------------------------------------------ merge
terms = []
by_id = {}
for k, rs in groups.items():
    tid = ids[k]
    canon_counts = collections.Counter(r["_canon"] for r in rs)
    term_ja = canon_counts.most_common(1)[0][0] if rs[0]["_canon"] else ""
    variants = uniq([r["term_ja"] for r in rs if r["term_ja"] and r["term_ja"] != term_ja])
    readings = uniq([r["reading"] for r in rs])
    notes = []
    if len(set(norm(x) for x in readings)) > 1:
        notes.append("읽기 이견: " + " / ".join(readings))
    # kind
    kc = collections.Counter(r["kind"] for r in rs)
    top = max(kc.values())
    kind = [x for x in KIND_PREF if kc.get(x) == top][0]
    if len(kc) > 1:
        notes.append("kind 이견: " + ", ".join(f"{r['_origin']}={r['kind']}" for r in rs))
    # axis
    ac = collections.Counter(r["axis"] for r in rs)
    top = max(ac.values())
    cands = [a for a in ac if ac[a] == top]
    axis = cands[0]
    if len(cands) > 1:
        for r in rs:
            if r["axis"] in cands and r["axis"] in FILE_AXES.get(r["_file"], set()):
                axis = r["axis"]
                break
    axis = AXIS_OVERRIDE.get(k, axis)
    if len(ac) > 1:
        notes.append("axis 이견: " + ", ".join(f"{r['_origin']}={r['axis']}" for r in rs))
    # definition: row with the best-tier source first
    ranked = sorted(rs, key=lambda r: min([tier_of(u) for u in r["_urls"]] + [9]))
    definition = ranked[0]["definition"]
    for r in ranked[1:]:
        if r["definition"] and r["definition"] != definition:
            notes.append(f"[다른 정의 {r['_origin']}] {r['definition']}")
    notes += uniq([r["notes"] for r in rs])
    urls = uniq([u for r in rs for u in r["_urls"]])
    tiers = sorted(set(tier_of(u) for u in urls))
    hobby = [t for t in tiers if t != 9]
    best = hobby[0] if hobby else 9
    unv = []
    if not term_ja:
        unv.append("term_ja 없음(한국 판매명)")
    alltext = " ".join(r["notes"] + " " + r["term_en"] for r in rs)
    if re.search(r"読み 추정|읽기 추정|読み 추정", alltext):
        unv.append("읽기 추정")
    if re.search(r"검색 스니펫|검색 요약|snippet|검색 결과 제목", alltext):
        unv.append("일부 서술이 검색 스니펫 근거")
    if re.search(r"\(inferred\)", " ".join(r["term_en"] for r in rs)):
        unv.append("영문 대응 추론")
    if len(urls) == 1 and best >= 3:
        unv.append("단일 출처(샵·블로그)")
    t = dict(id=tid, term_ja=term_ja, reading=readings[0] if readings else "",
             term_ko=" / ".join(uniq([x for r in rs for x in split_multi(r["term_ko"])])),
             term_en=" / ".join(uniq([x for r in rs for x in split_multi(r["term_en"])])),
             kind=kind, axis=axis, definition=definition, variants=" / ".join(variants),
             source_urls=" | ".join(urls), n_sources=len(urls),
             best_tier=f"{best}:{TIER[best]}", accessed=" | ".join(uniq([r["accessed"] for r in rs])),
             unverified="; ".join(unv), collected_in="; ".join(r["_origin"] for r in rs),
             notes=" ‖ ".join(notes))
    t["_rows"] = rs
    terms.append(t)
    by_id[tid] = t

# ---- attested orthographic variants get their own row (ruling R-10) ---------
VARIANT_ROWS = [  # variant, base term, url where the variant is printed, what differs
    ("クロメダカ", "黒メダカ", "https://t-aquagarden.com/column/medaka_variety", "가타카나 표기"),
    ("緋目高", "ヒメダカ", JMA_MANUAL, "한자 표기"),
    ("ヒレナガ", "ヒレ長", "https://t-aquagarden.com/column/medaka_body", "가타카나 표기"),
    ("背びれなし", "背ビレ無し", "https://www.soramedaka.com/type", "히라가나 표기"),
    ("ビックアイ", "ビッグアイ", JMA_MANUAL, "JMA 본문 표기(형질표는 ビッグアイ)"),
    ("曜変天目", "陽変天目", "https://nekomanma7.ocnk.net/product-list/47", "한자 표기(曜/陽)"),
]
variant_pairs = []
for v, base, url, what in VARIANT_ROWS:
    b = next(t for t in terms if norm(t["term_ja"]) == norm(base))
    k = norm(v)
    assert k not in groups, v
    if k not in ids:
        ids[k] = f"bv:{nxt:04d}"
        nxt += 1
    t = dict(id=ids[k], term_ja=v, reading=b["reading"], term_ko="", term_en="", kind=b["kind"], axis=b["axis"],
             definition=f"{base}({b['id']})의 표기 변형 — {what}. 정의는 기준 행을 따른다.", variants="",
             source_urls=url, n_sources=1, best_tier=f"{tier_of(url)}:{TIER[tier_of(url)]}", accessed="2026-09-28",
             unverified="표기 변형 행", collected_in="build:variant", notes="")
    t["_rows"] = []
    terms.append(t)
    by_id[t["id"]] = t
    variant_pairs.append((b["id"], t["id"], url))
json.dump(ids, open(idfile, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

# ---- post-verification corrections (AC-6 pass, 2026-09-28) ------------------
# R-14: a term whose only source does not print it is flagged, not left looking verified.
TERM_FLAGS = {
    norm("上物"): ("출처 본문에 표기 없음(JMA PDF 84쪽 텍스트 추출에서 미검출, 그림 라벨 추론)",
                  "AC-6 검증: 인용한 JMA PDF 본문에 「上物」이 없다. 이 행은 그림 라벨 추론이며 출처 미확인."),
}
# R-15: 홍색소포 is 虹色素胞 (iridophore), easily misread as 紅色素胞 (적색소포); gloss once per definition.
IRIDO = "홍색소포"
IRIDO_GLOSS = "홍색소포(虹, 구아닌 반사)"
for t in terms:
    k = norm(t["term_ja"])
    if k in TERM_FLAGS:
        flag, note = TERM_FLAGS[k]
        t["unverified"] = "; ".join(x for x in [t["unverified"], flag] if x)
        t["notes"] = " ‖ ".join(x for x in [t["notes"], note] if x)
    d = t["definition"]
    i = d.find(IRIDO)
    if i >= 0 and not d[i + len(IRIDO):].startswith("("):
        t["definition"] = d[:i] + IRIDO_GLOSS + d[i + len(IRIDO):]

# ------------------------------------------------------------------ resolver
index = collections.defaultdict(list)       # normalized name -> ids
for t in terms:
    names = [t["term_ja"]] + t["variants"].split(" / ")
    for n in names:
        if n:
            index[norm(n)].append(t["id"])
    for r in t["_rows"]:
        index[norm(r["term_ja"])].append(t["id"])
for k in index:
    index[k] = uniq(index[k])

AMBIG = {  # bare word used in two senses -> pick by subject axis
    norm("強光"): lambda subj: norm("強光（ヒカリの形質補足）") if subj and subj["axis"] == "BODY_SHAPE"
    else norm("強光（幹之グレード）"),
}
SUFFIXES = ["メダカ", "メダカ", "体色", "系統", "系", "形質", "(品種名)", "品種名"]


# component spellings that name an existing row (ruling R-08).
# 黒 = ブラック: JMA writes ブラック as 黒 only inside two-colour names (黄黒 etc.).
ALIAS = {norm(k): norm(v) for k, v in {
    "黒": "ブラック", "3色": "三色", "白ラメ": "ラメ（白）", "多色ラメ": "ラメ（多色）", "白錦": "白斑",
}.items()}


# (subject, object) pairs whose object string must not bind to a same-spelled row:
# 鮮紅's official JMA name 青ラメ means 青 body + ラメ, not the row 青ラメ (blue lamé).
NO_RESOLVE = {(norm("鮮紅"), norm("青ラメ"))}


def resolve(name, subj=None):
    n = norm(name)
    if not n:
        return None
    if subj and (norm(subj["term_ja"]), n) in NO_RESOLVE:
        return None
    n = ALIAS.get(n, n)
    if n in AMBIG:
        n = AMBIG[n](subj)
    cands = [n, strip_paren(n)]
    more = []
    for c in cands:
        for s in SUFFIXES:
            s = norm(s)
            if c.endswith(s) and len(c) > len(s):
                more.append(c[: -len(s)])
    cands += more
    for c in cands:
        if c in AMBIG:
            c = AMBIG[c](subj)
        if c in index:
            return index[c][0]
    return None


def reading_kata(t):
    return norm(t["reading"]) if t["reading"] else ""


def same_word(a, b):
    """variant_spelling test: same word in a different script/orthography."""
    na, nb = norm(a["term_ja"]), norm(b["term_ja"])
    ra, rb = reading_kata(a), reading_kata(b)
    if na == nb:
        return True
    if ra and (ra == nb or (rb and ra == rb)):
        return True
    if rb and rb == na:
        return True
    return False


# ------------------------------------------------------------------ relations
rels = collections.OrderedDict()   # (s, rel, o) -> dict
dropped = collections.Counter()
unresolved = collections.Counter()


def add(s, rel, o, basis, origin, olabel=None):
    assert rel in RELS, rel
    if s == o:
        return
    if rel in ("same_as", "variant_spelling", "collides_with") and o and not o.startswith("seed:") and o < s:
        s, o = o, s
    key = (s, rel, o or "?" + (olabel or ""))
    if key in rels:
        e = rels[key]
        if basis not in e["basis"].split(" | "):
            # prefer source-stated basis first
            parts = e["basis"].split(" | ") + [basis]
            parts.sort(key=lambda b: 0 if b.startswith("source:") else 1)
            e["basis"] = " | ".join(parts)
        if origin not in e["origin"]:
            e["origin"] += "; " + origin
        return
    rels[key] = dict(subject_id=s, relation=rel, object_id=o or "",
                     object_label=olabel or "", basis=basis, origin=origin)


# Local page texts we hold. A relation stated in a row is attributed to the first
# source URL of that row whose text we can check and that mentions the object;
# failing that, to the first URL we cannot check (ruling R-09).
LOCAL = {}
for url, fn in [(JMA_MANUAL, "raw/jma5.txt"), (AQLAB_URL, "raw/aqualab_yougo.txt")]:
    LOCAL[url] = norm(open(os.path.join(HERE, fn), encoding="utf-8").read())


def pick_url(urls, obj):
    o = [norm(x) for x in re.split(r"[+/]", strip_paren(norm(obj))) if x.strip()]
    for u in urls:
        if u in LOCAL and o and all(x in LOCAL[u] for x in o):
            return u
    # the one-page JMA trait table is a subset of the manual: if the manual text
    # lacks the object, the table does too, so skip it as well
    for u in urls:
        if u not in LOCAL and u != JMA_TABLE:
            return u
    return urls[0]


for r in rows:
    sid = ids[r["_key"]]
    subj = by_id[sid]
    for part in [p.strip() for p in r["related_terms"].split(";") if p.strip()]:
        inferred = False
        if part.startswith("inferred:"):
            inferred, part = True, part[len("inferred:"):]
        if ":" not in part:
            dropped["(형식 불명)"] += 1
            continue
        rel, obj = part.split(":", 1)
        if obj.startswith("inferred:"):
            inferred, obj = True, obj[len("inferred:"):]
        if "(inferred)" in obj:
            inferred, obj = True, obj.replace("(inferred)", "")
        basis = (f"inferred:수집 lane 추론({r['_origin']})" if inferred else f"source:{pick_url(r['_urls'], obj)}")
        if rel in ("contrasts", "related", "derived_from"):
            dropped[rel] += 1
            continue
        if rel == "composed_of":
            comps = [c.strip() for alt in obj.split(" / ") for c in alt.split("+") if c.strip()]
            for c in comps:
                oid = resolve(c, subj)
                if not oid:
                    unresolved[c] += 1
                add(sid, "composed_of", oid, basis, r["_origin"], c)
            continue
        oid = resolve(obj, subj)
        if not oid:
            unresolved[obj] += 1
        if rel == "same_as":
            relx = "variant_spelling" if oid and same_word(subj, by_id[oid]) else "same_as"
            add(sid, relx, oid, basis, r["_origin"], obj)
        elif rel == "contains":
            add(sid, "narrower", oid, basis, r["_origin"], obj)
        elif rel == "contained_in":
            add(sid, "broader", oid, basis, r["_origin"], obj)
        else:
            dropped[rel] += 1

for bid, vid, url in variant_pairs:
    add(bid, "variant_spelling", vid, f"source:{url}", "build:variant")

# JMA naming: X（Y） sub-forms are narrower concepts of X (inferred)
for t in terms:
    m = re.match(r"^(.+?)[（(](.+)[）)]$", t["term_ja"])
    if m:
        pid = resolve(m.group(1))
        if pid and pid != t["id"]:
            add(pid, "narrower", t["id"], "inferred:JMA 표기 X（Y）는 X의 형질보충·세분형", "build:paren")

# ---- manual relations (collisions, synonymy the collectors noted in prose) --
AQLAB = AQLAB_URL
MANUAL = [
    ("強光（ヒカリの形質補足）", "collides_with", "強光（幹之グレード）", f"source:{JMA_MANUAL}", "JMA는 ヒカリ 형질보충, 애호가는 幹之 등급"),
    ("強光（幹之グレード）", "same_as", "スーパー光", "source:https://www.aqualassic.com/medaka_miyuki/", ""),
    ("黄金", "collides_with", "黄金(こがね)", "source:https://www.gex-fp.co.jp/fish/breed_cat/medaka_catalog/", ""),
    ("斑", "collides_with", "斑(まだら)", "source:https://piscesbook.com/archives/category/newinfomation/medaka-zukan", ""),
    ("ヒカリ", "collides_with", "体外光", f"source:{AQLAB}", ""),
    ("光りメダカ", "collides_with", "体外光", "inferred:한자 光가 광택 축(体外光·体内光·強光)의 접미사와 겹침", ""),
    ("ヒカリ", "collides_with", "ロングフィン", "source:https://namu.wiki/w/%EC%86%A1%EC%82%AC%EB%A6%AC", "나무위키 '롱핀 타입인 히카리'"),
    ("ロングフィン", "same_as", "ヒレ長", "source:https://t-aquagarden.com/column/medaka_variety", "TAG만 동일시; JMA는 구분"),
    ("ロングフィン", "collides_with", "ヒレ長", f"source:{JMA_MANUAL}", "JMA: 연조만 신장 vs 연조+기막"),
    ("鉄仮面", "collides_with", "フルボディ", "source:https://jasma.sc/medaka/mikiyuki/", "JASMA는 구분, 다수 샵은 동일시"),
    ("紅白", "collides_with", "琥珀", "source:https://themedakaemporium.co.uk/our-medaka", "영문 Kohaku 혼동"),
    ("Hitomi", "collides_with", "瞳", "source:https://medakazukan.net/jmaninteinumber/", "같은 읽기 ひとみ, 다른 품종"),
    ("ショート", "collides_with", "ショートボディ", "source:https://medakanoyakata.muragon.com/entry/352.html", ""),
    ("非透明鱗", "collides_with", "透明鱗（ホホ無し）", f"source:{JMA_MANUAL}", "JMA 경고: 非透明鱗이 ホホ無し를 뜻하기도"),
    ("黒メダカ", "collides_with", "ブラック", f"source:{JMA_MANUAL}", ""),
    ("流星", "composed_of", "マルコ", "source:https://medakazukan.net/jmaninteinumber/", ""),
    ("点目", "same_as", "スモールアイ", "source:https://ameblo.jp/medakaan-west-shop/entry-11948732359.html", ""),
    ("Daタイプ", "same_as", "ヒカリ", "source:https://hinsyu-zukan.satumano-medakayasan.com/%E7%94%A8%E8%AA%9E%E9%9B%86/", ""),
    ("強透明鱗", "narrower", "パンダ", f"source:{JMA_MANUAL}", ""),
    ("強透明鱗", "narrower", "シースルー", f"source:{JMA_MANUAL}", ""),
]
for s, rel, o, basis, _ in MANUAL:
    if not basis:
        continue
    sid, oid = resolve(s), resolve(o)
    if not sid or not oid:
        print("MANUAL UNRESOLVED", s, o, sid, oid)
        continue
    add(sid, rel, oid, basis, "build:manual")

# ---- second pass (2026-10): edges the first pass got wrong ------------------
# docs/research/vocabulary-audit-2026-10.md found these by reading `same_as`
# transitively and by cross-checking the table against the seed's own rulings.
# Each fix names its ruling; the lane TSVs are left as collected, so what a
# source said and what we concluded from it stay apart.
REVISED = "revised:2026-10 2차 정제"
FIX_RETYPE = [
    # (subject, old relation, object, new relation or None to drop, ruling)
    # JMA's 2020 nickname table glosses オロチ as ブラック + 背地反応なし: a
    # narrower form, not another name. Kon maps them to different loci.
    ("ブラック", "same_as", "オロチ", "narrower", "R-34"),
    # 強透明鱗 is the JMA diagram term that resolves to パンダ on a normal eye and
    # シースルー on an albino one; the manual edges above already say narrower.
    ("パンダ", "same_as", "強透明鱗", None, "R-35"),
    # 幹之 is the nickname of a strain (青 + 体外光); 体外光 is one of its traits.
    ("幹之", "same_as", "体外光", None, "R-36"),
    # R-27 read JMA's カガミ cell as unrelated to カガミ鱗; the edge contradicted it.
    ("カガミ", "same_as", "カガミ鱗", None, "R-37"),
]
for s, old, o, new, ruling in FIX_RETYPE:
    sid, oid = resolve(s), resolve(o)
    key = next((k for k in ((sid, old, oid), (oid, old, sid)) if k in rels), None)
    assert key, ("FIX target missing", s, old, o)
    edge = rels.pop(key)
    if new:
        add(sid, new, oid, f"{edge['basis']} | {REVISED} {ruling}", edge["origin"] + "; build:revised")

# A same_as that the table also records as a collision is a dispute between
# sources, not a synonym. It stays, so the dispute is visible, but carries a
# marker no transitive reading may cross (check_vocab enforces this).
for (s, rel, o), edge in rels.items():
    if rel != "same_as":
        continue
    if (s, "collides_with", o) in rels or (o, "collides_with", s) in rels:
        edge["basis"] += f" | disputed:같은 쌍에 collides_with 기록 ({REVISED} R-38)"
# The same holds one step out: 極光 is same_as both フルボディ and 鉄仮面, which
# JASMA keeps apart, so either edge alone would carry the collision across.
collisions = [(s, o) for (s, rel, o) in rels if rel == "collides_with" and not o.startswith("seed:")]
same_edges = {(s, o): e for (s, rel, o), e in rels.items() if rel == "same_as" and o}
for a, b in collisions:
    nbr = collections.defaultdict(set)
    for (s, o) in same_edges:
        nbr[s].add(o)
        nbr[o].add(s)
    for c in nbr[a] & nbr[b]:
        for x in (a, b):
            e = same_edges.get((x, c)) or same_edges.get((c, x))
            if "disputed:" not in e["basis"]:
                e["basis"] += f" | disputed:{by_id[c]['term_ja']} 을 거쳐 collides_with 쌍을 잇는다 ({REVISED} R-38)"

# Scattered synonym: a Korean shop's 시로부치 is the transliteration of 白斑
# (しろぶち); the row itself says so in its notes, but nothing linked the two.
add("bv:0132", "same_as", "bv:0555", f"inferred:bv:0555 notes — 白ブチ(しろぶち)의 음역 ({REVISED} R-42)", "build:revised")

# ------------------------------------------------------------------ seed coverage
import yaml  # noqa: E402
seed = []
for f in ["10-entities-traits.yaml", "12-entities-breeder-traits.yaml"]:
    d = yaml.safe_load(open(os.path.join(REPO, "data", "seed", f), encoding="utf-8"))
    for e in d["entities"]:
        if e["label"] == "OrnamentalTrait":
            seed.append(e)

# status: M = matched, C = only a colliding name, L = lab only, N = no match found
# each: (seed name, status, [(term, relation, basis)], seed label, hobby form, label verdict)
SEED = [
    ("orochi", "M", [("オロチ", "seed_match", f"source:{JMA_MANUAL}")], "オロチ", "オロチ", "일치"),
    ("aurora", "M", [("オーロラ", "seed_match", f"source:{JMA_MANUAL}"), ("半透明鱗", "seed_match", "inferred:Kon 정의(아가미뚜껑 홍색소포 소실)=JMA オーロラ 형질=半透明鱗")], "オーロラ", "オーロラ", "일치 (단 계통명·형질명 동음)"),
    ("sanshoku", "M", [("三色", "seed_match", f"source:{JMA_MANUAL}")], "三色", "三色 (JMA 품종명 白朱赤斑 / 朱赤透明鱗斑)", "일치"),
    ("kurobuchi", "M", [("黒斑", "seed_match", f"source:{JMA_MANUAL}"), ("斑", "seed_match", "inferred:JMA가 흑반 무늬 호칭을 斑(ぶち)로 통일")], "黒斑", "黒斑(くろぶち), 斑(ぶち)", "일치 — JMA 후리가나 くろぶち로 로마자 kurobuchi 확인"),
    # R-39: 白朱赤 is same_as 紅白 (JMA), so matching it here made akabuchi = kouhaku.
    # Kon defines akabuchi as the union of sanshoku and kouhaku; no trade word names it.
    ("akabuchi", "N", [], "赤斑", "업계 용어 없음 (白朱赤·紅白은 하위 형질 kouhaku 의 이름)", "불일치 — 赤斑은 업계 표기로 확인 안 됨. 비슷한 朱赤斑(しゅあかぶち)은 朱赤 바탕에 흑반(斑)이라 뜻이 다름"),
    ("blackrim", "M", [("ブラックリム", "seed_match", f"source:{JMA_MANUAL}")], "—", "ブラックリム", "라벨 없음"),
    ("yellow", "M", [("黄", "seed_match", f"source:{JMA_MANUAL}"), ("ヒメダカ", "seed_match", f"source:{JMA_MANUAL}")], "ヒメダカ, 黄", "黄 (JMA 형질), ヒメダカ (통칭)", "일치"),
    ("YWKo", "N", [], "—", "업계 용어 없음 (Kon의 분석용 합성 클래스: 黄·白·紅白)", "라벨 없음"),
    ("black", "M", [("ブラック", "seed_match", f"source:{JMA_MANUAL}")], "黒", "ブラック (2색 표기에서만 黒: 黄黒, 黒オレンジ)", "부분 불일치 — 단독 黒/黒メダカ는 야생형을 가리킬 수 있음(JMA)"),
    ("panda", "M", [("パンダ", "seed_match", f"source:{JMA_MANUAL}")], "パンダ", "パンダ", "일치"),
    ("white", "M", [("白", "seed_match", f"source:{JMA_MANUAL}")], "白", "白（クリーム）/ シルキー", "일치"),
    ("blue", "M", [("青", "seed_match", f"source:{JMA_MANUAL}")], "青", "青", "일치"),
    ("miyuki", "M", [("幹之", "seed_match", f"source:{JMA_MANUAL}"), ("体外光", "seed_match", "inferred:Kon 정의(등쪽 이소성 홍색소포)=JMA 형질명 体外光")], "幹之", "幹之 (닉네임), 体外光 (JMA 형질)", "일치 (단 seed는 BODY_COLOR, 업계는 광택 축)"),
    ("rame", "M", [("ラメ", "seed_match", f"source:{JMA_MANUAL}")], "ラメ", "ラメ", "일치"),
    ("kouhaku", "M", [("紅白", "seed_match", f"source:{JMA_MANUAL}"), ("白朱赤", "seed_match", "inferred:JMA 품종명 표기 白朱赤 = 紅白")], "紅白", "紅白 (JMA 표기 白朱赤)", "일치"),
    ("kuroaka", "M", [("黒オレンジ", "seed_match", "inferred:Kon 정의(오렌지 바탕+흑반)=JMA 2색 표기 ブラック+オレンジ; 번식장 표기는 赤黒(女雛·来光)")], "黒赤", "赤黒 (hinsyu-zukan), 黒オレンジ (JMA 2색 표기)", "불일치 — 黒赤 표기 미확인, 업계는 赤黒 순서"),
    ("fukumaku", "M", [("腹膜青", "seed_match", "inferred:Kon 'blue silver-coloured peritoneum' = JMA 共通補足 腹膜青"), ("腹膜光", "collides_with", "inferred:JMA §3.8.2/§3.8.3 이 발현 조건이 반대인 별개 형질로 구분(R-21, R-40)")], "腹膜", "腹膜青 / 腹膜光", "불일치 — 腹膜은 해부 부위명이고 형질명은 腹膜青 또는 腹膜光"),
    ("yokihi", "M", [("楊貴妃", "seed_match", f"source:{JMA_MANUAL}"), ("朱赤", "seed_match", "inferred:JMA 공식 형질명 朱赤(楊貴妃는 닉네임)")], "楊貴妃", "楊貴妃 (JMA 형질명 朱赤)", "일치"),
    ("gold", "M", [("黄金", "seed_match", "inferred:Kon 'gold'(갈색 기반·흑색 감소) ↔ 黄金(おうごん, en Gold); 黄金(こがね)과는 별개")], "—", "黄金(おうごん)", "라벨 없음 — 붙일 때 黄金(こがね) 품종과 충돌 주의"),
    ("toumeirin", "M", [("透明鱗", "seed_match", f"source:{JMA_MANUAL}")], "透明鱗", "透明鱗", "일치"),
    ("albino", "M", [("アルビノ", "seed_match", f"source:{JMA_MANUAL}")], "アルビノ", "アルビノ", "일치"),
    ("nijikin", "N", [], "虹金", "대응 용어 못 찾음 (가장 가까운 후보: 全身体内光, 추론·약함)", "불일치 — 虹金은 어떤 출처에도 없음"),
    # R-41: Daタイプ is the trade's word for the ヒカリ body shape (hinsyu-zukan
    # glossary: ヒカリ体型（Daタイプ）), so it maps to the breeder trait. The lab Da
    # mutant is reached only through putatively_same_as in the seed (PRD §8).
    ("hikari", "M", [("ヒカリ", "seed_match", f"source:{JMA_MANUAL}"), ("Daタイプ", "seed_match", "source:https://hinsyu-zukan.satumano-medakayasan.com/%E7%94%A8%E8%AA%9E%E9%9B%86/")], "光", "ヒカリ (가타카나). 光りメダカ·光体型은 JMA 각주의 드문 표기", "불일치 — 업계는 ヒカリ. 한자 光는 광택 축(体外光 등)과 충돌"),
    ("daruma", "M", [("ダルマ", "seed_match", f"source:{JMA_MANUAL}")], "ダルマ", "ダルマ", "일치"),
    ("handaruma", "M", [("半ダルマ", "seed_match", f"source:{JMA_MANUAL}")], "半ダルマ", "半ダルマ", "일치"),
    ("hirenaga", "M", [("ヒレ長", "seed_match", f"source:{JMA_MANUAL}")], "ヒレ長", "ヒレ長 (변형 ヒレナガ)", "일치"),
    ("swallow", "M", [("スワロー", "seed_match", f"source:{JMA_MANUAL}")], "スワロー", "スワロー", "일치"),
    ("longfin", "C", [("ロングフィン", "collides_with", "inferred:Kon longfin=꼬리 외 6개 지느러미 신장; JMA ロングフィン=등·뒷지느러미 연조만 신장")], "—", "ロングフィン (정의가 다름)", "라벨 없음 — 붙이면 안 됨"),
    ("reallongfin", "M", [("リアルロングフィン", "seed_match", f"source:{JMA_MANUAL}")], "—", "リアルロングフィン", "라벨 없음"),
    ("nodorsalfin", "M", [("マルコ", "seed_match", f"source:{JMA_MANUAL}"), ("背ビレ無し", "seed_match", f"source:{JMA_MANUAL}")], "—", "マルコ（背ビレ無し）", "라벨 없음"),
    ("deme", "M", [("出目", "seed_match", f"source:{JMA_MANUAL}")], "出目", "出目", "일치"),
    ("bigeye", "M", [("ビッグアイ", "seed_match", f"source:{JMA_MANUAL}")], "—", "ビッグアイ (본문 ビックアイ)", "라벨 없음"),
    ("tenme", "M", [("スモールアイ", "seed_match", "inferred:Kon 'small pupil; small eyeballs in some cases' = JMA スモールアイ(동공 위축)"), ("点目", "seed_match", "inferred:点目(てんめ)은 スモールアイ 별칭이며 로마자 tenme와 읽기 일치")], "天眼", "点目 = スモールアイ", "불일치 — 天眼은 어떤 출처에도 없음. 天眼은 てんがん으로 읽혀 tenme가 안 됨. 頂点眼(위를 향한 눈)과도 다름"),
    ("suihougan", "M", [("水泡眼", "seed_match", f"source:{JMA_MANUAL}")], "水泡眼", "水泡眼", "일치"),
    ("Da mutant", "L", [], "—", "lab only (업계의 Daタイプ 는 hikari 의 표기; 둘의 관계는 seed 의 putatively_same_as)", "—"),
    ("guanineless", "L", [], "—", "lab only", "—"),
    ("few melanophore", "L", [], "—", "lab only", "—"),
    ("leucophore free", "L", [], "—", "lab only", "—"),
    ("leucophore free-2", "L", [], "—", "lab only", "—"),
    ("white leucophore", "L", [], "—", "lab only", "—"),
    ("many leucophores-3", "L", [], "—", "lab only", "—"),
    ("panda (pa) lab mutant", "L", [("パンダ", "collides_with", "inferred:seed가 이름만 같은 별개 실험실 변이로 명시")], "—", "lab only (이름만 パンダ와 충돌)", "—"),
    ("fused centrum", "L", [], "—", "lab only (ダルマ와 표현형 유사, 동일성 미확인)", "—"),
    ("kagamirin", "M", [("カガミ鱗", "seed_match", "source:https://piscesbook.com/archives/11622")], "カガミ鱗 (japanese_name)", "カガミ鱗 / カガミ", "일치"),
    ("fusahire", "M", [("フサヒレ", "seed_match", f"source:{JMA_MANUAL}")], "房ヒレ (unverified)", "フサヒレ (가타카나만)", "미확인 — 房ヒレ은 어떤 출처에도 없음(seed 주석과 같음)"),
]
seed_names = [e["name"] for e in seed]
assert [s[0] for s in SEED] == seed_names, set(seed_names) ^ set(s[0] for s in SEED)
for name, st, matches, *_ in SEED:
    for term, rel, basis in matches:
        tid = resolve(term)
        if not tid:
            print("SEED UNRESOLVED", name, term)
            continue
        add(tid, rel, "seed:" + name, basis, "build:seed")

# ------------------------------------------------------------------ write CSVs
TCOLS = ["id", "term_ja", "reading", "term_ko", "term_en", "kind", "axis", "definition", "variants",
         "source_urls", "n_sources", "best_tier", "accessed", "unverified", "collected_in", "notes"]
with open(OUT_TERMS, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=TCOLS, quoting=csv.QUOTE_ALL, extrasaction="ignore")
    w.writeheader()
    for t in sorted(terms, key=lambda t: t["id"]):
        w.writerow(t)

RCOLS = ["subject_id", "subject_term", "relation", "object_id", "object_term", "basis", "origin"]


def label(i):
    if not i:
        return ""
    if i.startswith("seed:"):
        return i[5:]
    return by_id[i]["term_ja"] or by_id[i]["term_ko"]


rel_list = list(rels.values())
for e in rel_list:
    e["subject_term"] = label(e["subject_id"])
    e["object_term"] = label(e["object_id"]) if e["object_id"] else e["object_label"] + " (미등록)"
with open(OUT_RELS, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=RCOLS, quoting=csv.QUOTE_ALL, extrasaction="ignore")
    w.writeheader()
    for e in rel_list:
        w.writerow(e)

# ------------------------------------------------------------------ fragments for the doc
def md_table(head, body):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in body]
    return "\n".join(out) + "\n"


kc = collections.Counter(t["kind"] for t in terms)
ac = collections.Counter(t["axis"] for t in terms)
cross = collections.Counter((t["axis"], t["kind"]) for t in terms)
body = [[a] + [cross[(a, k)] for k in KINDS] + [ac[a]] for a in AXES]
body.append(["합계"] + [kc[k] for k in KINDS] + [len(terms)])
open(os.path.join(FRAG, "counts.md"), "w", encoding="utf-8").write(
    md_table(["axis \\ kind"] + [f"{k} ({KIND_KO[k]})" for k in KINDS] + ["합계"], body))

tc = collections.Counter(t["best_tier"] for t in terms)
open(os.path.join(FRAG, "tiers.md"), "w", encoding="utf-8").write(
    md_table(["가장 높은 출처 등급", "용어 수"], sorted(tc.items())))

rc = collections.Counter(e["relation"] for e in rel_list)
rb = collections.Counter((e["relation"], "source" if e["basis"].startswith("source:") else "inferred") for e in rel_list)
unres = sum(1 for e in rel_list if not e["object_id"])
open(os.path.join(FRAG, "relcounts.md"), "w", encoding="utf-8").write(
    md_table(["relation", "행 수", "출처 근거", "추론"], [[r, rc[r], rb[(r, "source")], rb[(r, "inferred")]] for r in RELS]))

seed_rows = []
STL = {"M": "대응", "C": "이름만 충돌", "L": "lab only", "N": "no match found"}
for name, st, matches, slabel, hobby, verdict in SEED:
    m = "; ".join(f"{t} ({resolve(t)}, {rel})" for t, rel, _ in matches) or hobby
    seed_rows.append([name, STL[st], m, slabel, verdict])
open(os.path.join(FRAG, "seed.md"), "w", encoding="utf-8").write(
    md_table(["seed trait", "상태", "업계 용어 (id, 관계)", "seed 라벨", "라벨 대조"], seed_rows))

stats = dict(rows_in=len(rows), terms=len(terms), merged_groups=sum(1 for g in groups.values() if len(g) > 1),
             rels=len(rel_list), unresolved_rel_rows=unres, dropped=dict(dropped),
             top_unresolved=unresolved.most_common(25), seed_status=dict(collections.Counter(s[1] for s in SEED)),
             unverified_terms=sum(1 for t in terms if t["unverified"]),
             unverified_breakdown=dict(collections.Counter(x for t in terms for x in t["unverified"].split("; ") if x)))
json.dump(stats, open(os.path.join(FRAG, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False, indent=1))
