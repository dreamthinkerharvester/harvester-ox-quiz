#!/usr/bin/env python3
r"""
OX 자기완결성(self-containment) 검증 시스템.

핵심 원칙: OX 문항은 그 문장 하나만으로 O/X를 판단할 수 있어야 한다.
원본 객관식에서 단순 추출된 fragment(빈칸 조합, 명사구 단독, 페이지 푸터 등)는
플레이어가 외부 컨텍스트 없이 평가할 수 없으므로 ox_valid=0 으로 마크.

플래그 체계 (FAIL=재생 불가 / WARN=의심 / PASS=정상):

  [E1_BLANK_FRAGMENT] "ㄱ:", "ㄴ:" 등으로 시작하는 빈칸 조합  (FAIL)
  [E2_OPTION_PREFIX]  ①~⑩ 같은 선택지 번호로 시작                (FAIL)
  [E3_BARE_VALUE]     단일 숫자·단위만 (예: "30일", "5,000원")    (FAIL)
  [E4_NOUN_ONLY]      한국어 종결어미 부재 + 짧음(<24자)          (FAIL)
  [E5_SINGLE_WORD]    공백 0 + 짧음(<14자)                       (FAIL)
  [E6_TERM_DASH]      "단어 - 단어" 패턴 + 종결어미 부재          (FAIL)
  [E7_MID_FRAGMENT]   시작이 비한글(특수문자/조사) + 짧음          (FAIL)
  [E8_EXTERNAL_REF]   "다음 중", "위의", "아래의" 등 외부 참조    (FAIL)
  [E9_QUESTION_STEM]  의문문 또는 question stem ("옳은 것은?")    (FAIL)
  [E10_ALL_OPTIONS]   ①~⑤ 모두 본문에 — 다른 문제 fragment 잔재  (FAIL)
  [E11_MATH_FORMULA]  계산형 — 수학기호 + 화폐 다수 (× ÷ ∑ ￦)    (FAIL)
  [E12_SOURCE_BLOCK]  (가)·(나)·(다) 2개+ — 외부 사례 의존        (FAIL)
  [E13_OCR_BROKEN]    OCR 깨짐 ("20 1년", "재 무 상 표")          (FAIL)
  [E14_EXTERNAL_BLOCK] "다음 글/지문/시/<보기>" 외부 자료 참조    (FAIL)
  [W1_NO_PREDICATE]   종결어미 부재(≥24자) — 학습용 가능           (WARN)
  [W2_NUM_HEAVY]      숫자 비율 >40%                              (WARN)
  [W3_PAGE_ARTIFACT]  PDF 페이지 푸터 잔재 ("2024년도 제..A형..")  (WARN, auto-strip 가능)

자동 정제(--strip-artifacts):
  - 끝부분 PDF 푸터 제거: r"\d{4}년도?\s*제\d+회.*\(\s*\d+\s*-\s*\d+\s*\)$"
  - 중간 잘려나간 stem 잔재 제거: "송의 한계에 관한 설명으로..." 같은 트레일링

사용법:
  python3 scripts/validate_ox.py                       # 검증 + 리포트
  python3 scripts/validate_ox.py --apply               # DB ox_valid/ox_flags 갱신
  python3 scripts/validate_ox.py --apply --strip-artifacts  # 갱신 + 자동 정제
  python3 scripts/validate_ox.py --sample 20           # FAIL 샘플 20개 미리보기
  python3 scripts/validate_ox.py --by-category         # 카테고리별 PASS율

설계 의도:
  - 1466건 코퍼스에서 명백한 fragment만 차단 (보수적). 학습용으로도 유용한 짧은
    문장은 WARN으로 두고 노출은 유지. 사용자가 frontend/export에서 ox_valid=0
    필터를 적용할지 결정.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"


# ── 패턴 정의 ───────────────────────────────────────────────────────────

# 한국어 종결어미 — 어말 매칭 (loose 중간 매칭 금지: "관한"의 "한" 같은 false match 방지)
#   다/이다/한다/된다/있다/없다/아니다 — 평서형 종결
#   함/음/임/됨 — 명사화 종결
#   요/네/지 — 회화체 (드물지만 OX에선 거의 없음)
# 뒤에 마침표·물음표·괄호 등이 붙는 경우도 포함하기 위해 어말 검사 시 우선 정제.
PREDICATE_ENDING_RE = re.compile(
    r"(?:이다|아니다|있다|없다|한다|된다|같다|옳다|틀리다|보다|"
    r"하였다|되었다|있었다|없었다|이었다|아니었다|"
    r"하였음|되었음|있었음|"
    r"있음|없음|함|됨|임|"
    r"수\s*있다|수\s*없다|수\s*있음|수\s*없음|"
    r"하여야\s*한다|되어야\s*한다|아니어야\s*한다|"
    r"습니다|입니다|"
    r"다)"
    r"\s*\.?\s*$"  # 종결어미 후 공백·마침표 어느 순서든 허용 ("다 .", "다.", "다 ", "다" )
)
TRAILING_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")

# 빈칸 조합 fragment
BLANK_FRAGMENT_RE = re.compile(r"^\s*(?:ㄱ|ㄴ|ㄷ|ㄹ|ㅁ)\s*:")
BLANK_PAIR_RE = re.compile(r"(?:ㄱ|ㄴ|ㄷ|ㄹ)\s*:[^,]{1,30},\s*(?:ㄴ|ㄷ|ㄹ|ㅁ)\s*:")

# 선택지 번호 시작
OPTION_PREFIX_RE = re.compile(r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]")

# bare value (숫자 + 한국어 단위)
BARE_VALUE_RE = re.compile(
    r"^\s*[₩\$￦]?[\d,]+(?:\.\d+)?\s*(?:[%‰원만억]|일|시간|분|초|년|월|개|명|회|조|점|배|등|미터|cm|kg|mm|m|km|°|℃|t|kt)?\s*$"
)

# 외부 참조 (이 문장 단독으로는 평가 불가). 보수적: 명백한 question-stem 패턴만.
# 주의: "위법한", "위임", "다음 각 호" 등 합법 표현 false positive 방지.
EXTERNAL_REF_RE = re.compile(
    r"^\s*다음\s*중(?:에서)?\b"
    r"|^\s*(?:위|아래|상기|하기|상술한|전술한)\s*(?:의|에서|와|과|는|에)?\s*[ㄱㄴㄷㄹㅁ]\b"
    r"|^\s*(?:위|아래)\s*표\b"
    r"|옳은\s*것을\s*모두\s*고른\s*것은"
    r"|옳지\s*않은\s*것을\s*모두\s*고른\s*것은"
)

# 단어 - 단어 패턴 (의미 단편)
TERM_DASH_RE = re.compile(r"^\s*[가-힣A-Za-z0-9]{2,}\s*[-–—]\s*[가-힣A-Za-z0-9]{2,}\s*$")

# 시작이 비한글·비숫자 (PDF 잘림 의심). 숫자 시작은 정상("1년은", "1마일은") 허용.
NON_HANGUL_START_RE = re.compile(r"^[^\sㄱ-ㅎ가-힣A-Za-z0-9(\[\"'《「『]")

# PDF 페이지 푸터 잔재
PAGE_FOOTER_RE = re.compile(
    r"\s*\d{0,3}\s*\d{4}년도?\s*제?\s*\d+\s*회\s*[가-힣]+\s*\d+차?\s*"
    r"\d?\s*교?시?\s*[A-Z형]*\s*\(\s*\d+\s*-\s*\d+\s*\)\s*$"
)

# ── 컨텍스트 의존 패턴 (E10~E14) — 배경지식 외 외부 자료가 있어야 판단 가능 ──
# E10: 다른 문제의 선택지가 본문에 통째로 출현 — fragment 잔재
ALL_OPTIONS_RE = re.compile(r"①.*②.*③.*④.*⑤", re.DOTALL)

# E11: 계산형 — 수학 기호 + 화폐 다수 (×, ÷, ∑, ∫, log 등 + 원/￦)
MATH_SYMBOLS_RE = re.compile(
    r"[∑∫∂∇√∞≤≥≠≈±÷×]"
    r"|\\frac|log\s|sin\s|cos\s|lim\b"
    r"|￦\s*[\d,]+"            # 화폐기호 + 숫자
    r"|\d+×\d|\d+÷\d"          # 수식 직접
)

# E12: 자료 블록 참조 — (가)·(나)·(다)·(라) 패턴 다수 (≥2개)
SOURCE_BLOCK_RE = re.compile(r"\(\s*[가나다라마바사]\s*\)")

# E13: OCR 깨짐 — 한글 사이 숫자 공백 (예: "20 1년도", "재 무 상 표")
OCR_BROKEN_PATTERNS = [
    re.compile(r"[가-힣]\s+\d\s+[가-힣]"),       # "20 1년도"
    re.compile(r"(?:[가-힣]\s){3,}[가-힣]"),     # "재 무 상 표"
    re.compile(r"[가-힣][\d]+×[\d]+[가-힣]?"),  # "20×1년"
    re.compile(r"￦\s*[\d,]+\s*[가-힣]"),        # "￦114,238이다" 같은 정상은 제외할 추가 정제 필요
]

# E14: 외부 글/지문 참조 — "다음 글", "다음 지문", "윗글", "<보기>" 등 명시적 참조
EXTERNAL_BLOCK_RE = re.compile(
    r"(?:다음|위|아래|윗)\s*(?:글|지문|시|작품|보기|자료|장면|대화|논증)"
    r"|<\s*(?:보기|자료|지문|글)\s*>"
    r"|\[\s*(?:보기|자료|지문)\s*\]"
)

# 한국어 종결어미가 명시적으로 부재한 short statement
MIN_PREDICATE_LEN = 24
MIN_SINGLE_WORD_LEN = 14


# ── 텍스트 정제 ─────────────────────────────────────────────────────────

def strip_artifacts(stmt: str) -> tuple[str, list[str]]:
    """페이지 푸터·중간 잘림 등 자동 제거. (cleaned_stmt, applied_changes) 반환."""
    s = stmt
    changes = []

    # 1. PDF 페이지 푸터
    m = PAGE_FOOTER_RE.search(s)
    if m:
        s = PAGE_FOOTER_RE.sub("", s).rstrip()
        changes.append("page-footer")

    # 1b. 종결어미(다·함·음·임) 직후의 OCR 잔재 (예: "...부른다. 채 앙", "...수있다. 안")
    #     평서문 종결 뒤에 짧은 1~4 글자 토큰들이 1~3개 붙은 경우 제거.
    OCR_TAIL_RE = re.compile(
        r"((?:이다|아니다|있다|없다|한다|된다|같다|보다|함|음|임|됨|다))\s*\.\s*"
        r"(?:[가-힣A-Za-z0-9]{1,4}\s+){0,2}[가-힣A-Za-z0-9]{1,4}\s*$"
    )
    m = OCR_TAIL_RE.search(s)
    if m:
        s = OCR_TAIL_RE.sub(m.group(1) + ".", s).rstrip()
        changes.append("ocr-tail-noise")

    # 2. 중간 잘린 stem (한 문장 후 다른 문장의 fragment가 붙은 경우)
    # 예: "ㄱ: 90일, ㄴ: 회복하기 어려운 송의 한계에 관한 설명으로 옳지 않은 것은? (다툼이 있으면 판례에 따름)"
    #     → "ㄱ: 90일, ㄴ: 회복하기 어려운" (의문문 fragment 제거)
    QUESTION_TAIL_RE = re.compile(
        r"\s+[가-힣]{0,10}\s*(?:송의|법의|의|법상|령상|에 관한)\s+설명으로?\s+옳[지은].*?(?:것은\?|것을\?)\s*"
        r"(?:\(.*?\))?\s*$"
    )
    m = QUESTION_TAIL_RE.search(s)
    if m:
        s = QUESTION_TAIL_RE.sub("", s).rstrip()
        changes.append("question-stem-fragment")

    # 3. 다중 공백 정규화
    s2 = re.sub(r"\s+", " ", s).strip()
    if s2 != s:
        changes.append("whitespace")
        s = s2

    return s, changes


# ── 검증 로직 ───────────────────────────────────────────────────────────

def has_predicate(s: str) -> bool:
    """한국어 어말 종결어미 보유 여부. 끝 괄호·구두점 정제 후 어말 매칭."""
    t = TRAILING_PAREN_RE.sub("", s.rstrip())
    return bool(PREDICATE_ENDING_RE.search(t))


def char_ratios(s: str) -> tuple[float, float, float, int]:
    if not s:
        return 0.0, 0.0, 0.0, 0
    han = sum(1 for c in s if "가" <= c <= "힣")
    dig = sum(1 for c in s if c.isdigit())
    sym = sum(1 for c in s if not (c.isalnum() or c.isspace() or "가" <= c <= "힣"))
    L = len(s)
    return han / L, dig / L, sym / L, L


def validate(stmt: str) -> tuple[str, list[str]]:
    """OX 자기완결성 검증. (verdict, flags) 반환.

    verdict ∈ {PASS, WARN, FAIL}
    flags = [E1_..., W2_...] 발견된 플래그 리스트
    """
    if not stmt or not stmt.strip():
        return "FAIL", ["E0_EMPTY"]

    s = unicodedata.normalize("NFC", stmt.strip())
    flags = []
    han_r, dig_r, sym_r, L = char_ratios(s)

    # ── FAIL 룰 (재생 불가) ───
    # E1: 빈칸 조합
    if BLANK_FRAGMENT_RE.search(s) or BLANK_PAIR_RE.search(s):
        flags.append("E1_BLANK_FRAGMENT")

    # E2: 선택지 번호로 시작
    if OPTION_PREFIX_RE.search(s):
        flags.append("E2_OPTION_PREFIX")

    # E3: bare value
    if BARE_VALUE_RE.match(s):
        flags.append("E3_BARE_VALUE")

    # E5: 단일 단어 (먼저 검사 — E4와 우선순위)
    if " " not in s and L < MIN_SINGLE_WORD_LEN:
        flags.append("E5_SINGLE_WORD")

    # E6: 단어 - 단어 패턴
    if TERM_DASH_RE.match(s) and not has_predicate(s):
        flags.append("E6_TERM_DASH")

    # E7: 시작이 비한글 + 짧음
    if NON_HANGUL_START_RE.match(s) and L < 20 and not flags:
        flags.append("E7_MID_FRAGMENT")

    # E8: 외부 참조
    if EXTERNAL_REF_RE.search(s):
        flags.append("E8_EXTERNAL_REF")

    # E9: 의문문/question stem — 평서문이 아니면 OX 불가
    # 어말 정제(괄호 제거) 후 "?" 로 끝나거나, "옳은 것은", "옳지 않은 것은" 패턴 포함
    s_no_paren = TRAILING_PAREN_RE.sub("", s.rstrip())
    if s_no_paren.endswith("?") or re.search(r"옳[은지]\s*않?은?\s*것은\b", s):
        flags.append("E9_QUESTION_STEM")

    # E10: 다른 문제 선택지가 본문에 출현 (①~⑤ 모두 포함) — fragment 잔재
    if ALL_OPTIONS_RE.search(s):
        flags.append("E10_ALL_OPTIONS")

    # E11: 계산형 수식 — 수학 기호/화폐 다수
    if MATH_SYMBOLS_RE.search(s):
        flags.append("E11_MATH_FORMULA")

    # E12: 자료 블록 (가)·(나)·(다) 2개 이상 — 외부 사례 의존
    if len(SOURCE_BLOCK_RE.findall(s)) >= 2:
        flags.append("E12_SOURCE_BLOCK")

    # E13: OCR 깨짐 — 한글 사이에 비정상 공백/숫자
    for pat in OCR_BROKEN_PATTERNS:
        if pat.search(s):
            flags.append("E13_OCR_BROKEN")
            break

    # E14: "다음 글/지문/시/보기" 등 외부 자료 명시 참조
    if EXTERNAL_BLOCK_RE.search(s):
        flags.append("E14_EXTERNAL_BLOCK")

    # E4: 명사구 단독 (종결어미 부재 + 짧음). FAIL 조건 좁게.
    if not has_predicate(s) and L < MIN_PREDICATE_LEN:
        if not any(f.startswith("E") for f in flags):
            flags.append("E4_NOUN_ONLY")

    has_fail = any(f.startswith("E") for f in flags)

    # ── WARN 룰 (의심, 재생 가능) ───
    # W1: 종결어미 부재 (긴 문장)
    if not has_predicate(s) and L >= MIN_PREDICATE_LEN and not has_fail:
        flags.append("W1_NO_PREDICATE")

    # W2: 숫자 비율 >40%
    if dig_r > 0.40 and not has_fail:
        flags.append("W2_NUM_HEAVY")

    # W3: 페이지 푸터 잔재 (FAIL과 동시 가능 — strip 권유)
    if PAGE_FOOTER_RE.search(s):
        flags.append("W3_PAGE_ARTIFACT")

    # ── verdict ───
    if has_fail:
        verdict = "FAIL"
    elif any(f.startswith("W") for f in flags):
        verdict = "WARN"
    else:
        verdict = "PASS"

    return verdict, flags


# ── DB 적용 ─────────────────────────────────────────────────────────────

def run_validation(
    conn: sqlite3.Connection,
    apply: bool = False,
    strip: bool = False,
    sample_n: int = 8,
    by_category: bool = False,
) -> int:
    cur = conn.cursor()
    rows = conn.execute(
        """SELECT q.id, q.statement, q.answer, q.source_qid, q.source_option,
                  c.name AS cat
           FROM questions q JOIN categories c ON q.category_id=c.id
           ORDER BY c.id, q.id"""
    ).fetchall()

    if not rows:
        print("문항 0건", file=sys.stderr)
        return 1

    by_v = Counter()
    by_f = Counter()
    by_cv: dict[str, Counter] = {}
    samples: dict[str, list] = {"FAIL": [], "WARN": []}
    updates: list[tuple[int, int, str, str | None]] = []  # (qid, ox_valid, ox_flags_json, new_stmt)
    strip_count = 0

    for r in rows:
        original = r["statement"]
        stmt = original
        applied = []
        if strip:
            stmt, applied = strip_artifacts(original)
            if applied:
                strip_count += 1

        verdict, flags = validate(stmt)
        by_v[verdict] += 1
        for f in flags:
            by_f[f] += 1
        by_cv.setdefault(r["cat"], Counter())[verdict] += 1

        if verdict in samples and len(samples[verdict]) < sample_n:
            samples[verdict].append((r["cat"], r["source_qid"], r["source_option"],
                                     r["answer"], stmt, flags, applied))

        ox_valid = 0 if verdict == "FAIL" else 1
        flags_json = json.dumps(flags, ensure_ascii=False) if flags else None
        new_stmt = stmt if (strip and applied) else None
        updates.append((r["id"], ox_valid, flags_json, new_stmt))

    total = len(rows)

    # ── 보고 ───
    print("=" * 70)
    print(f"OX 자기완결성 검증 — 총 {total}건")
    print("=" * 70)
    print(f"\n[Verdict 분포]")
    for v in ("PASS", "WARN", "FAIL"):
        n = by_v[v]
        pct = 100 * n / total if total else 0
        bar = "█" * int(pct / 3)
        print(f"  {v:>6}: {n:>4}건 ({pct:5.1f}%)  {bar}")

    print(f"\n[Flag 빈도]")
    for f, n in by_f.most_common():
        print(f"  {f:<25} {n:>4}")

    if by_category:
        print(f"\n[카테고리별]")
        print(f"  {'카테고리':>14}  {'PASS':>4} {'WARN':>4} {'FAIL':>4}   PASS%")
        for cat, c in by_cv.items():
            p, w, f = c.get("PASS", 0), c.get("WARN", 0), c.get("FAIL", 0)
            t = p + w + f
            pct = 100 * p / t if t else 0
            print(f"  {cat:>14}  {p:>4} {w:>4} {f:>4}   {pct:5.1f}%")

    for label in ("FAIL", "WARN"):
        print(f"\n[{label} 샘플 (최대 {sample_n}건)]")
        for cat, qid, opt, ans, stmt, flags, applied in samples[label]:
            preview = stmt if len(stmt) <= 100 else stmt[:97] + "..."
            print(f"  · [{cat}] Q.{qid} ({opt}) {ans}")
            print(f"    \"{preview}\"")
            print(f"    flags: {', '.join(flags)}")
            if applied:
                print(f"    stripped: {', '.join(applied)}")

    if strip:
        print(f"\n[자동 정제] {strip_count}건의 페이지 푸터·잘림 제거 적용")

    # ── DB 갱신 ───
    if apply:
        print(f"\n=== --apply : DB 갱신 ===")
        cnt_fail = sum(1 for _, v, _, _ in updates if v == 0)
        cnt_strip = sum(1 for _, _, _, ns in updates if ns is not None)
        for qid, ox_valid, ox_flags, new_stmt in updates:
            if new_stmt is not None:
                cur.execute(
                    "UPDATE questions SET ox_valid=?, ox_flags=?, statement=? WHERE id=?",
                    (ox_valid, ox_flags, new_stmt, qid),
                )
            else:
                cur.execute(
                    "UPDATE questions SET ox_valid=?, ox_flags=? WHERE id=?",
                    (ox_valid, ox_flags, qid),
                )
        conn.commit()
        print(f"  ✓ ox_valid=0 마크: {cnt_fail}건")
        if strip:
            print(f"  ✓ statement 자동 정제: {cnt_strip}건")
        print(f"  → JSON 재생성: python3 scripts/export_quiz_json.py")
    elif any(v == "FAIL" for v in by_v.elements()):
        print(f"\n💡 DB에 마크: python3 scripts/validate_ox.py --apply")
        if not strip:
            print(f"   페이지 푸터·잘림 자동 정제 함께: --apply --strip-artifacts")

    print()
    return 0


def main():
    ap = argparse.ArgumentParser(description="OX 자기완결성 검증")
    ap.add_argument("--apply", action="store_true",
                    help="DB의 ox_valid/ox_flags 컬럼 갱신")
    ap.add_argument("--strip-artifacts", action="store_true",
                    help="PDF 페이지 푸터·잘림 자동 정제(statement 직접 수정)")
    ap.add_argument("--sample", type=int, default=8,
                    help="FAIL/WARN 샘플 출력 수 (기본 8)")
    ap.add_argument("--by-category", action="store_true",
                    help="카테고리별 분포 표시")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ox_valid 컬럼 존재 확인
    cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    if "ox_valid" not in cols or "ox_flags" not in cols:
        print("⚠ ox_valid/ox_flags 컬럼 없음 — 마이그레이션 필요:", file=sys.stderr)
        print("   sqlite3 data/quiz.db 'ALTER TABLE questions ADD COLUMN ox_valid INTEGER NOT NULL DEFAULT 1;'", file=sys.stderr)
        print("   sqlite3 data/quiz.db 'ALTER TABLE questions ADD COLUMN ox_flags TEXT;'", file=sys.stderr)
        return 1

    return run_validation(
        conn,
        apply=args.apply,
        strip=args.strip_artifacts,
        sample_n=args.sample,
        by_category=args.by_category,
    )


if __name__ == "__main__":
    sys.exit(main())
