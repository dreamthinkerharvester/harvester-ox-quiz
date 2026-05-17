#!/usr/bin/env python3
r"""
공기출 표준 양식 PDF (2024+) 자동 인벤토리 + OX 변환 + DB 적재.

이미 빌더가 있는 직렬(세무사·행정사·회계사)는 자동 제외.
공기출 "정답은 N이다" 패턴 평문 추출이 가능한 해설 PDF만 처리.

추출 전략 (build_cpa_db.py 와 동일):
  시험지: pdfplumber 좌·우 컬럼 crop → pymupdf fallback
  해설:   pdfplumber + cid 글리프 제거 + `(\d+)번 ... 정답[은이]? ([①-⑤])` 매칭

지원 직렬·slug 코드:
  국가직-9급 → g9   /  국가직-7급 → g7   /  지방직-9급 → l9  /  지방직-7급 → l7
  서울시-9급 → s9   /  서울시-7급 → s7   /  국회직-9급 → na9 /  국회직-8급 → na8
  경찰-간부  → pol-cmdr / 경찰-기타 → pol-misc / 경찰-승진 → pol-prom
  소방-간부  → fire-cmdr / 소방-기타 → fire-misc / 소방-승진 → fire-prom
  군무원-9급 → ms9 / 군무원-7급 → ms7 / 군무원-기타 → ms-misc
  해경-승진  → cg-prom / 해경-간부 → cg-cmdr
  법원직-9급 → ct9 / 기상직-9급 → met9

사용법:
  python3 scripts/build_generic_db.py --dry-run       # 인벤토리만
  python3 scripts/build_generic_db.py                 # 전체 처리
  python3 scripts/build_generic_db.py --year 2025     # 특정 연도만
  python3 scripts/build_generic_db.py --jik 국가직-9급 # 특정 직렬만
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber  # type: ignore
import fitz  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
DRIVE_BASE = Path.home() / "Library/CloudStorage/GoogleDrive-kakaiuina@gmail.com/내 드라이브/공기출"

# 이미 별도 빌더가 처리하는 직렬 (중복 방지)
SKIP_JIKRYEOL = {"전문직-세무사", "전문직-행정사", "전문직-회계사"}

# 직렬명 → slug prefix
JIK_CODE = {
    "국가직-9급": "g9", "국가직-7급": "g7", "국가직-5급": "g5",
    "지방직-9급": "l9", "지방직-7급": "l7",
    "서울시-9급": "s9", "서울시-7급": "s7",
    "국회직-9급": "na9", "국회직-8급": "na8", "국회직-5급": "na5",
    "법원직-9급": "ct9", "법원직-5급": "ct5",
    "경찰-간부": "pol-cmdr", "경찰-기타": "pol-misc", "경찰-승진": "pol-prom",
    "경찰-특공대": "pol-spec",
    "소방-간부": "fire-cmdr", "소방-기타": "fire-misc", "소방-승진": "fire-prom",
    "군무원-9급": "ms9", "군무원-7급": "ms7", "군무원-5급": "ms5",
    "군무원-기타": "ms-misc",
    "해경-승진": "cg-prom", "해경-간부": "cg-cmdr", "해경-기타": "cg-misc",
    "기상직-9급": "met9",
    "전문직-노무사": "cpla", "전문직-감정평가사": "appr",
    "전문직-경영지도사": "bizmgt", "전문직-변호사": "law",
    "전문직-관세사": "customs", "전문직-가맹거래사": "franch",
    "기타": "misc", "기타-비상대비": "emrg",
}

# 회계사 빼고 나머지 직렬은 한국어 sub-items (ㄱ-ㅁ)
SUB_LETTERS_KO = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]
SUB_LETTERS_EN = ["a", "b", "c", "d", "e"]

CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
           "➀": 1, "➁": 2, "➂": 3, "➃": 4, "➄": 5}
CIRCLED_INV = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
MIN_STMT_LEN = 12

# 직렬 디스플레이 라벨 (exam_group 용)
EXAM_GROUP_TPL = "{display} · {year}년"
DISPLAY_NAMES = {
    "국가직-9급": "국가직 9급", "국가직-7급": "국가직 7급", "국가직-5급": "국가직 5급",
    "지방직-9급": "지방직 9급", "지방직-7급": "지방직 7급",
    "서울시-9급": "서울시 9급", "서울시-7급": "서울시 7급",
    "국회직-9급": "국회직 9급", "국회직-8급": "국회직 8급", "국회직-5급": "국회직 5급",
    "법원직-9급": "법원직 9급", "법원직-5급": "법원직 5급",
    "경찰-간부": "경찰 간부", "경찰-기타": "경찰", "경찰-승진": "경찰 승진",
    "경찰-특공대": "경찰 특공대",
    "소방-간부": "소방 간부", "소방-기타": "소방", "소방-승진": "소방 승진",
    "군무원-9급": "군무원 9급", "군무원-7급": "군무원 7급", "군무원-5급": "군무원 5급",
    "군무원-기타": "군무원",
    "해경-승진": "해경 승진", "해경-간부": "해경 간부", "해경-기타": "해경",
    "기상직-9급": "기상직 9급",
    "전문직-노무사": "노무사 1차", "전문직-감정평가사": "감정평가사 1차",
    "전문직-경영지도사": "경영지도사 1차", "전문직-변호사": "변호사시험",
    "전문직-관세사": "관세사 1차", "전문직-가맹거래사": "가맹거래사 1차",
    "기타": "기타", "기타-비상대비": "비상대비",
}


# ── 텍스트 헬퍼 ───────────────────────────────────────────────────────────
def strip_cid(text: str) -> str:
    return re.sub(r"\(cid:\d+\)", " ", text or "")


def normalize_stmt(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s.lower()


def stmt_hash(s: str) -> str:
    return hashlib.sha256(normalize_stmt(s).encode()).hexdigest()[:16]


def subject_to_slug(subject_name: str) -> str:
    """과목 디렉토리 이름 → slug. '경제학개론 문제' → 'economics-intro'."""
    s = re.sub(r"\s+문제$", "", subject_name).strip()
    # 한국어를 직접 slug로 (충돌 방지를 위해 hash 첨가)
    h = hashlib.md5(s.encode()).hexdigest()[:6]
    # ASCII 친화: 한글 제거 + hash
    ascii_part = re.sub(r"[^a-zA-Z0-9-]", "", s.replace(" ", "-"))
    return ascii_part + "-" + h if ascii_part else "subj-" + h


# ── 시험지 추출 ──────────────────────────────────────────────────────────
def extract_exam_text(pdf_path: Path) -> str:
    """시험지 PDF → 단일 텍스트. 좌·우 컬럼 분리 후 합치기.
    pdfplumber 실패 시 pymupdf fallback."""
    chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                w, h = page.width, page.height
                left = page.crop((0, 0, w / 2 + 5, h)).extract_text() or ""
                right = page.crop((w / 2 - 5, 0, w, h)).extract_text() or ""
                # 만약 한쪽이 비어있다면 단일 컬럼으로 판단
                if not right.strip() or len(right) < 50:
                    chunks.append(page.extract_text() or "")
                else:
                    chunks.append(left)
                    chunks.append(right)
        return "\n".join(chunks)
    except Exception:
        try:
            doc = fitz.open(pdf_path)
            chunks = []
            for page in doc:
                w, h = page.rect.width, page.rect.height
                left = page.get_text("text", clip=fitz.Rect(0, 0, w / 2 + 5, h)) or ""
                right = page.get_text("text", clip=fitz.Rect(w / 2 - 5, 0, w, h)) or ""
                if not right.strip() or len(right) < 50:
                    chunks.append(page.get_text() or "")
                else:
                    chunks.append(left)
                    chunks.append(right)
            doc.close()
            return "\n".join(chunks)
        except Exception:
            return ""


# ── 해설 정답 추출 ───────────────────────────────────────────────────────
ANSWER_NEAR_RE = re.compile(
    r"(\d+)\s*번.{0,300}?정답[은이]?.{0,40}?([①②③④⑤➀➁➂➃➄])",
    re.DOTALL,
)


def parse_answer_table(pdf_path: Path) -> dict[int, int]:
    """해설 PDF → {qid: 1~5}. pdfplumber → pymupdf fallback."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        try:
            doc = fitz.open(pdf_path)
            full = "\n".join(p.get_text() or "" for p in doc)
            doc.close()
        except Exception:
            return {}
    full = strip_cid(full)
    answers: dict[int, int] = {}
    for m in ANSWER_NEAR_RE.finditer(full):
        n = int(m.group(1))
        if n in answers:
            continue
        if 1 <= n <= 100:
            answers[n] = CIRCLED[m.group(2)]
    return answers


# ── qtype 판정 + 시험지 파싱 ─────────────────────────────────────────────
QTYPE_PATTERNS = {
    "sub-all-correct": re.compile(r"(?:옳은\s*것을?\s*모두|적절한\s*항목만을\s*모두\s*(?:선택|고른)|맞는\s*것을?\s*모두)"),
    "sub-all-wrong":   re.compile(r"(?:옳지\s*않은\s*것을?\s*모두|적절하지\s*않은\s*항목만을\s*모두|틀린\s*것을?\s*모두)"),
    "opt-wrong":       re.compile(r"(?:가장\s*적절하지\s*않은\s*것은|옳지\s*않은\s*것은|틀린\s*것은|아닌\s*것은)"),
    "opt-correct":     re.compile(r"(?:가장\s*적절한\s*것은|옳은\s*것은|타당한\s*것은|올바른\s*것은|맞는\s*것은)"),
}


def detect_qtype(stem: str) -> str:
    s = re.sub(r"\s+", " ", stem)
    if QTYPE_PATTERNS["sub-all-wrong"].search(s):
        return "sub-all-wrong"
    if QTYPE_PATTERNS["sub-all-correct"].search(s):
        return "sub-all-correct"
    if QTYPE_PATTERNS["opt-wrong"].search(s):
        return "opt-wrong"
    if QTYPE_PATTERNS["opt-correct"].search(s):
        return "opt-correct"
    return "unknown"


@dataclass
class ParsedQuestion:
    qid: int
    stem: str
    qtype: str
    options: list = field(default_factory=list)
    sub_items: dict = field(default_factory=dict)


def parse_exam(text: str, qid_start: int, qid_end: int, sub_letters: list) -> dict[int, ParsedQuestion]:
    qmap: dict[int, ParsedQuestion] = {}
    qstart_pat = re.compile(r"(?:^|\n)\s*(\d{1,3})\.\s+(.+?)(?=\n\s*\d{1,3}\.\s+|\Z)", re.DOTALL)
    for m in qstart_pat.finditer(text):
        qid = int(m.group(1))
        if not (qid_start <= qid <= qid_end):
            continue
        if qid in qmap:
            continue
        block = m.group(0)
        first_opt = re.search(r"[①②③④⑤➀➁➂➃➄]", block)
        sub_alt = re.search(rf"\n\s*[{re.escape(''.join(sub_letters))}]\.\s", block)
        stem_end_pos = []
        if first_opt: stem_end_pos.append(first_opt.start())
        if sub_alt:   stem_end_pos.append(sub_alt.start())
        stem_end = min(stem_end_pos) if stem_end_pos else min(len(block), 250)
        stem = block[:stem_end]
        stem = re.sub(r"^\s*\d+\.\s+", "", stem).strip()
        stem = re.sub(r"\s+", " ", stem)
        qtype = detect_qtype(stem)

        # 옵션 ①~⑤
        options: list = [None] * 5
        opt_positions = []
        for sym, idx in CIRCLED.items():
            for om in re.finditer(re.escape(sym), block):
                opt_positions.append((om.start(), idx))
        opt_positions.sort()
        seen_opt = set()
        sel = []
        for pos, idx in opt_positions:
            if idx not in seen_opt:
                seen_opt.add(idx)
                sel.append((pos, idx))
            if len(sel) == 5:
                break
        sel.sort()
        for j, (pos, idx) in enumerate(sel):
            end = sel[j + 1][0] if j + 1 < len(sel) else len(block)
            opt_text = re.sub(r"\s+", " ", block[pos + 1:end].strip())
            options[idx - 1] = opt_text

        # sub-items
        sub_items = {}
        if qtype.startswith("sub-"):
            first_circ = re.search(r"[①②③④⑤➀➁➂➃➄]", block)
            cutoff = first_circ.start() if first_circ else len(block)
            sub_positions = []
            for ltr in sub_letters:
                for sm in re.finditer(rf"(?:^|\n)\s*{re.escape(ltr)}\.\s", block):
                    if sm.start() < cutoff:
                        sub_positions.append((sm.start(), ltr))
            sub_positions.sort()
            seen = set()
            final = []
            for pos, ltr in sub_positions:
                if ltr not in seen:
                    seen.add(ltr)
                    final.append((pos, ltr))
            for j, (pos, ltr) in enumerate(final):
                end = final[j + 1][0] if j + 1 < len(final) else cutoff
                slice_text = block[pos:end]
                slice_text = re.sub(rf"^\s*{re.escape(ltr)}\.\s*", "", slice_text)
                sub_items[ltr] = re.sub(r"\s+", " ", slice_text).strip()

        qmap[qid] = ParsedQuestion(qid=qid, stem=stem, qtype=qtype,
                                   options=options, sub_items=sub_items)
    return qmap


@dataclass
class OXItem:
    statement: str
    answer: str
    source_qid: int
    source_option: str


def convert_to_ox(q: ParsedQuestion, answer_num: int, sub_letters: list) -> list[OXItem]:
    items: list[OXItem] = []
    if q.qtype in ("opt-correct", "opt-wrong"):
        for i, opt in enumerate(q.options):
            if not opt or len(opt) < MIN_STMT_LEN:
                continue
            is_target = (i + 1) == answer_num
            ox = ("O" if q.qtype == "opt-correct" else "X") if is_target else \
                 ("X" if q.qtype == "opt-correct" else "O")
            items.append(OXItem(statement=opt, answer=ox, source_qid=q.qid,
                                source_option=CIRCLED_INV.get(i + 1, f"_{i+1}")))
    elif q.qtype in ("sub-all-correct", "sub-all-wrong"):
        if not q.sub_items or not any(q.options):
            return []
        if not (1 <= answer_num <= 5):
            return []
        ans_text = q.options[answer_num - 1] or ""
        chosen = set(c for c in ans_text if c in sub_letters)
        if not chosen:
            return []
        for ltr, item_raw in q.sub_items.items():
            item_text = re.sub(r"\s+", " ", item_raw).strip()
            if len(item_text) < MIN_STMT_LEN:
                continue
            is_chosen = ltr in chosen
            ox = ("O" if q.qtype == "sub-all-correct" else "X") if is_chosen else \
                 ("X" if q.qtype == "sub-all-correct" else "O")
            items.append(OXItem(statement=item_text, answer=ox, source_qid=q.qid,
                                source_option=ltr))
    return items


# ── 자동 인벤토리 ───────────────────────────────────────────────────────
@dataclass
class Subject:
    year: int
    jik: str
    subject_name: str
    exam_path: Path
    answer_path: Path


def discover(min_year: int = 2024, filter_jik: str | None = None) -> list[Subject]:
    found: list[Subject] = []
    for year_dir in sorted(DRIVE_BASE.iterdir(), key=lambda p: p.name, reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        if year < min_year:
            continue
        for jik_dir in sorted(year_dir.iterdir()):
            if not jik_dir.is_dir():
                continue
            jik = jik_dir.name
            if jik in SKIP_JIKRYEOL:
                continue
            if jik not in JIK_CODE:
                continue
            if filter_jik and jik != filter_jik:
                continue
            for subj_dir in sorted(jik_dir.iterdir()):
                if not subj_dir.is_dir():
                    continue
                pdfs = list(subj_dir.glob("*.pdf"))
                exam = next((p for p in pdfs if "해설" not in p.name
                             and "정답" not in p.name and "가답안" not in p.name), None)
                ans = next((p for p in pdfs if "해설" in p.name and "공기출" in p.name), None)
                if not ans:
                    ans = next((p for p in pdfs if "해설" in p.name), None)
                if exam and ans:
                    found.append(Subject(year=year, jik=jik,
                                         subject_name=subj_dir.name,
                                         exam_path=exam, answer_path=ans))
    return found


# ── DB 적재 ─────────────────────────────────────────────────────────────
def upsert_category(conn: sqlite3.Connection, subj: Subject) -> int:
    jik_code = JIK_CODE[subj.jik]
    slug = f"{jik_code}-{subj.year}-{subject_to_slug(subj.subject_name)}"
    subject_clean = re.sub(r"\s+문제$", "", subj.subject_name).strip()
    exam_group = EXAM_GROUP_TPL.format(display=DISPLAY_NAMES[subj.jik], year=subj.year)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO categories
           (slug, name, exam_group, subject, source, exam_year, display_order)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug) DO UPDATE SET
               name=excluded.name, exam_group=excluded.exam_group, subject=excluded.subject""",
        (slug, subject_clean, exam_group, subject_clean,
         DISPLAY_NAMES[subj.jik], subj.year, 500)
    )
    cur.execute("SELECT id FROM categories WHERE slug=?", (slug,))
    return cur.fetchone()[0]


def compute_frequency_stars(conn: sqlite3.Connection):
    """전체 카테고리에서 동일 statement 해시 → frequency·star_rating."""
    rows = conn.execute("SELECT id, statement FROM questions").fetchall()
    hash_map: dict[str, list[int]] = {}
    for qid, stmt in rows:
        hash_map.setdefault(stmt_hash(stmt or ""), []).append(qid)
    for ids in hash_map.values():
        freq = len(ids)
        star = min(5, freq)
        conn.executemany("UPDATE questions SET frequency=?, star_rating=? WHERE id=?",
                         [(freq, star, q) for q in ids])
    conn.commit()


# ── 메인 ────────────────────────────────────────────────────────────────
def process_subject(conn: sqlite3.Connection, subj: Subject, dry_run: bool) -> tuple[int, int, str]:
    """단일 과목 처리. (ox_count, qid_max, reason) 반환."""
    answers = parse_answer_table(subj.answer_path)
    if not answers:
        return 0, 0, "no-answers"

    text = extract_exam_text(subj.exam_path)
    if not text or len(text) < 200:
        return 0, 0, "exam-empty"

    qid_start, qid_end = 1, 100
    sub_letters = SUB_LETTERS_KO
    qmap = parse_exam(text, qid_start, qid_end, sub_letters)
    if not qmap:
        return 0, 0, "no-questions-parsed"

    cat_id = upsert_category(conn, subj) if not dry_run else -1
    ox_count = 0
    for qid in range(qid_start, qid_end + 1):
        q = qmap.get(qid)
        if not q or q.qtype == "unknown":
            continue
        ans_num = answers.get(qid)
        if ans_num is None:
            continue
        ox_items = convert_to_ox(q, ans_num, sub_letters)
        if not ox_items:
            continue
        if not dry_run:
            for ox in ox_items:
                conn.execute(
                    """INSERT OR REPLACE INTO questions
                       (category_id, statement, answer, explanation,
                        source_qid, source_option, qtype, source_pdf,
                        meta_quality, frequency, star_rating)
                       VALUES (?,?,?,?,?,?,?,?,?,1,0)""",
                    (cat_id, ox.statement, ox.answer, "",
                     ox.source_qid, ox.source_option, q.qtype,
                     subj.exam_path.name, 10)
                )
        ox_count += len(ox_items)
    if not dry_run:
        conn.execute(
            "UPDATE categories SET total_count=(SELECT COUNT(*) FROM questions WHERE category_id=?) WHERE id=?",
            (cat_id, cat_id),
        )
        conn.commit()
    return ox_count, max(qmap.keys()) if qmap else 0, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--year", type=int, default=2024)
    ap.add_argument("--jik", default=None, help="특정 직렬만 (예: 국가직-9급)")
    ap.add_argument("--limit", type=int, default=0, help="N개 과목만 (디버그)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ DB 없음: {DB_PATH}", file=sys.stderr)
        return 1

    print(f"인벤토리 중 (year>={args.year}, jik={args.jik or 'ALL'})...", flush=True)
    subjects = discover(min_year=args.year, filter_jik=args.jik)
    if args.limit:
        subjects = subjects[: args.limit]
    print(f"발견된 페어: {len(subjects)}")

    conn = sqlite3.connect(DB_PATH)
    from collections import Counter
    stats_by_jik: dict[str, dict] = {}
    fail_reasons: Counter = Counter()
    total_ox = 0
    processed = 0

    for i, subj in enumerate(subjects, 1):
        if i % 20 == 0:
            print(f"  ... {i}/{len(subjects)} (total OX={total_ox})", flush=True)
        try:
            ox, qmax, reason = process_subject(conn, subj, args.dry_run)
        except Exception as e:
            ox, qmax, reason = 0, 0, f"exception:{type(e).__name__}"
        processed += 1
        if reason != "ok":
            fail_reasons[reason] += 1
        total_ox += ox
        stats_by_jik.setdefault(subj.jik, {"subj": 0, "ox": 0, "failed": 0})
        stats_by_jik[subj.jik]["subj"] += 1
        if ox > 0:
            stats_by_jik[subj.jik]["ox"] += ox
        else:
            stats_by_jik[subj.jik]["failed"] += 1

    if not args.dry_run and total_ox > 0:
        print("★ 중요도 분석...", flush=True)
        compute_frequency_stars(conn)
    conn.close()

    print(f"\n{'='*60}")
    print(f"Generic builder {'(DRY)' if args.dry_run else '완료'} — TOTAL OX={total_ox}")
    print(f"{'='*60}")
    print(f"  {'직렬':<22} {'subj':>4} {'ox':>5} {'failed':>6}")
    for jik in sorted(stats_by_jik):
        d = stats_by_jik[jik]
        print(f"  {jik:<22} {d['subj']:>4} {d['ox']:>5} {d['failed']:>6}")
    print(f"\n  실패 사유: {dict(fail_reasons)}")

    if not args.dry_run:
        print("\n다음 단계:")
        print("  1. python3 scripts/validate_ox.py --apply --strip-artifacts")
        print("  2. python3 scripts/export_quiz_json.py --both")
    return 0


if __name__ == "__main__":
    sys.exit(main())
