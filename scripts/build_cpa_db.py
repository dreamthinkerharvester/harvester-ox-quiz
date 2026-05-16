#!/usr/bin/env python3
"""
공인회계사(CPA) 1차 시험 PDF → OX 퀴즈 SQLite DB 변환.

핵심 차이 (행정사·세무사 빌더와 비교):
  - 시험지: 2단 레이아웃 → pdfplumber 로 좌/우 column crop 후 concat
  - 해설: pypdf 생성 PDF (글리프 매핑 깨짐) → pdfplumber + cid 제거 + 정답 패턴 매칭
  - sub-items: 회계사는 영문자 a/b/c/d/e 사용 (행정사는 ㄱ/ㄴ/ㄷ/ㄹ/ㅁ)
  - qtype 어구: "가장 적절하지 않은", "적절한 항목만을 모두 선택한" 등

사용법:
  python3 scripts/build_cpa_db.py             # 전체 실행
  python3 scripts/build_cpa_db.py --dry-run   # 통계만, DB 변경 없음
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber  # type: ignore
import fitz  # type: ignore  # pymupdf, pdfplumber EOF fallback

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
DRIVE_BASE = Path.home() / "Library/CloudStorage/GoogleDrive-kakaiuina@gmail.com/내 드라이브/공기출"

# ── 과목 메타 ────────────────────────────────────────────────────────────
# 해설 PDF가 존재하는 케이스만 등록. 시험지만 있는 케이스(2024 경제원론·상법·세법)는
# 별도 정답 입수 후 추가 등록.
CPA_SUBJECTS = [
    # 2026 회계사 (5과목 모두 해설 있음)
    {
        "year": 2026, "exam_round": 61,
        "subject": "경영학", "phase": "1교시",
        "slug": "cpa-2026-r61-management",
        "exam_pdf": "2026/전문직-회계사/경영학 문제/경영학.pdf",
        "answer_pdf": "2026/전문직-회계사/경영학 문제/2026 회계사 경영학 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 40,
    },
    {
        "year": 2026, "exam_round": 61,
        "subject": "경제원론", "phase": "1교시",
        "slug": "cpa-2026-r61-economics",
        "exam_pdf": "2026/전문직-회계사/경제원론 문제/경제원론.pdf",
        "answer_pdf": "2026/전문직-회계사/경제원론 문제/2026 회계사 경제원론 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 40,
    },
    {
        "year": 2026, "exam_round": 61,
        "subject": "기업법", "phase": "1교시",
        "slug": "cpa-2026-r61-corplaw",
        "exam_pdf": "2026/전문직-회계사/기업법 문제/기업법.pdf",
        "answer_pdf": "2026/전문직-회계사/기업법 문제/2026 회계사 기업법 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 40,
    },
    {
        "year": 2026, "exam_round": 61,
        "subject": "세법개론", "phase": "1교시",
        "slug": "cpa-2026-r61-tax",
        "exam_pdf": "2026/전문직-회계사/세법개론 문제/세법개론.pdf",
        "answer_pdf": "2026/전문직-회계사/세법개론 문제/2026 회계사 세법개론 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 40,
    },
    {
        "year": 2026, "exam_round": 61,
        "subject": "회계학", "phase": "2교시",
        "slug": "cpa-2026-r61-accounting",
        "exam_pdf": "2026/전문직-회계사/회계학 문제/회계학.pdf",
        "answer_pdf": "2026/전문직-회계사/회계학 문제/2026 회계사 회계학 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 50,
    },
    # 2024 회계사 (해설 있는 2과목만)
    {
        "year": 2024, "exam_round": 59,
        "subject": "경영학", "phase": "1교시",
        "slug": "cpa-2024-r59-management",
        "exam_pdf": "2024/전문직-회계사/경영학 문제/01.경영학(1형)문제_2024.pdf",
        "answer_pdf": "2024/전문직-회계사/경영학 문제/2024 회계사 경영학 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 40,
    },
    {
        "year": 2024, "exam_round": 59,
        "subject": "회계학", "phase": "2교시",
        "slug": "cpa-2024-r59-accounting",
        "exam_pdf": "2024/전문직-회계사/회계학 문제/03.회계학(1형)문제_2024.pdf",
        "answer_pdf": "2024/전문직-회계사/회계학 문제/2024 회계사 회계학 해설 공기출.pdf",
        "qid_start": 1, "qid_end": 50,
    },
]

CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
           "➀": 1, "➁": 2, "➂": 3, "➃": 4, "➄": 5}
CIRCLED_INV = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
SUB_LETTERS = ["a", "b", "c", "d", "e"]   # 회계사 시험지는 영문자
MIN_STMT_LEN = 12


# ── 텍스트 헬퍼 ───────────────────────────────────────────────────────────
def normalize_stmt(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s.lower()


def stmt_hash(s: str) -> str:
    return hashlib.sha256(normalize_stmt(s).encode()).hexdigest()[:16]


def strip_cid(text: str) -> str:
    """pdfplumber가 매핑 못한 글리프(cid:NNNNN) 제거. 공백으로 치환."""
    return re.sub(r"\(cid:\d+\)", " ", text or "")


# ── 시험지 추출 (2단 레이아웃) ─────────────────────────────────────────────
def extract_exam_text(pdf_path: Path) -> str:
    """회계사 시험지 PDF → 좌→우 컬럼 순서로 단일 텍스트 합치기.
    pdfplumber 우선 시도 → 손상/EOF 시 pymupdf로 fallback (Hancom PDF 일부 케이스)."""
    chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                w, h = page.width, page.height
                left = page.crop((0, 0, w / 2 + 5, h)).extract_text() or ""
                right = page.crop((w / 2 - 5, 0, w, h)).extract_text() or ""
                chunks.append(left)
                chunks.append(right)
        return "\n".join(chunks)
    except Exception as e:
        print(f"  ⚠ pdfplumber 실패({e}) → pymupdf fallback", flush=True)
        chunks = []
        doc = fitz.open(pdf_path)
        for page in doc:
            w = page.rect.width
            h = page.rect.height
            # pymupdf clip rect 기반 좌·우 분리
            left_rect = fitz.Rect(0, 0, w / 2 + 5, h)
            right_rect = fitz.Rect(w / 2 - 5, 0, w, h)
            chunks.append(page.get_text("text", clip=left_rect) or "")
            chunks.append(page.get_text("text", clip=right_rect) or "")
        doc.close()
        return "\n".join(chunks)


# ── 해설 PDF에서 정답표 추출 ─────────────────────────────────────────────
ANSWER_NEAR_RE = re.compile(
    r"(\d+)\s*번.{0,300}?정답[은이]?.{0,40}?([①②③④⑤➀➁➂➃➄])",
    re.DOTALL,
)

def parse_answer_table(pdf_path: Path) -> dict[int, int]:
    """해설 PDF → {qid: 1~5}. cid 글리프는 무시하고 평문 한국어 + 기호만 사용."""
    full_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_chunks.append(page.extract_text() or "")
    full = "\n".join(full_chunks)
    full = strip_cid(full)

    answers = {}
    for m in ANSWER_NEAR_RE.finditer(full):
        qnum = int(m.group(1))
        ans_char = m.group(2)
        if 1 <= qnum <= 100 and ans_char in CIRCLED:
            if qnum not in answers:  # 첫 매치만 (해설은 같은 문항을 여러 번 언급 가능)
                answers[qnum] = CIRCLED[ans_char]
    return answers


# ── 시험지 파싱 ─────────────────────────────────────────────────────────
@dataclass
class ParsedQuestion:
    qid: int
    stem: str
    qtype: str
    options: list = field(default_factory=list)
    sub_items: dict = field(default_factory=dict)


# 회계사 어구 — "가장 적절하지 않은 것", "적절한 항목만을 모두 선택한 것", 등
QTYPE_PATTERNS = {
    "sub-all-correct": re.compile(r"적절한\s*항목만을\s*모두\s*(?:선택|고른).*?것은|옳은\s*것을?\s*모두"),
    "sub-all-wrong":   re.compile(r"적절하지\s*않은\s*항목만을\s*모두|옳지\s*않은\s*것을?\s*모두"),
    "opt-wrong":       re.compile(r"가장\s*적절하지\s*않은\s*것은|옳지\s*않은\s*것은|틀린\s*것은|아닌\s*것은"),
    "opt-correct":     re.compile(r"가장\s*적절한\s*것은|옳은\s*것은|타당한\s*것은|올바른\s*것은|맞는\s*것은"),
}


def detect_qtype(stem: str) -> str:
    s = re.sub(r"\s+", " ", stem)
    # sub-all-* 우선 (sub 단어가 단순 opt-* 표현 포함)
    if QTYPE_PATTERNS["sub-all-wrong"].search(s):
        return "sub-all-wrong"
    if QTYPE_PATTERNS["sub-all-correct"].search(s):
        return "sub-all-correct"
    if QTYPE_PATTERNS["opt-wrong"].search(s):
        return "opt-wrong"
    if QTYPE_PATTERNS["opt-correct"].search(s):
        return "opt-correct"
    return "unknown"


def parse_exam_pdf(pdf_path: Path, qid_start: int, qid_end: int) -> dict[int, ParsedQuestion]:
    text = extract_exam_text(pdf_path)
    qmap: dict[int, ParsedQuestion] = {}

    # 문항 시작점: 줄 시작에 "N." 패턴
    qstart_pat = re.compile(r"(?:^|\n)\s*(\d{1,3})\.\s+(.+?)(?=\n\s*\d{1,3}\.\s+|\Z)", re.DOTALL)
    matches = list(qstart_pat.finditer(text))

    for m in matches:
        qid = int(m.group(1))
        if not (qid_start <= qid <= qid_end):
            continue
        if qid in qmap:
            continue
        block = m.group(0)

        # 문항 stem: 첫 줄 또는 ?로 끝나는 첫 문장
        # 옵션(①~⑤) 또는 sub-item(a.~e.) 시작점 이전까지
        first_opt = re.search(r"[①②③④⑤➀➁➂➃➄]|\n\s*[a-e]\.\s", block)
        stem_end = first_opt.start() if first_opt else min(len(block), 200)
        stem = block[:stem_end]
        stem = re.sub(r"^\s*\d+\.\s+", "", stem).strip()
        stem = re.sub(r"\s+", " ", stem)

        qtype = detect_qtype(stem)

        # 옵션 ①~⑤ 추출
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
            opt_text = block[pos + 1:end].strip()
            opt_text = re.sub(r"\s+", " ", opt_text)
            options[idx - 1] = opt_text

        # sub-items a/b/c/d/e (sub-all-* 일 때만)
        sub_items = {}
        if qtype.startswith("sub-"):
            first_circ = re.search(r"[①②③④⑤➀➁➂➃➄]", block)
            cutoff = first_circ.start() if first_circ else len(block)
            sub_positions = []
            for ltr in SUB_LETTERS:
                for sm in re.finditer(rf"(?:^|\n)\s*{ltr}\.\s", block):
                    if sm.start() < cutoff:
                        sub_positions.append((sm.start(), ltr))
            sub_positions.sort()
            seen_ltr = set()
            final_sub = []
            for pos, ltr in sub_positions:
                if ltr not in seen_ltr:
                    seen_ltr.add(ltr)
                    final_sub.append((pos, ltr))
            for j, (pos, ltr) in enumerate(final_sub):
                end = final_sub[j + 1][0] if j + 1 < len(final_sub) else cutoff
                # ltr 위치에서 'X. ' 부분 skip
                slice_text = block[pos:end]
                slice_text = re.sub(rf"^\s*{ltr}\.\s*", "", slice_text)
                sub_items[ltr] = re.sub(r"\s+", " ", slice_text).strip()

        qmap[qid] = ParsedQuestion(qid=qid, stem=stem, qtype=qtype,
                                   options=options, sub_items=sub_items)
    return qmap


# ── OX 변환 ─────────────────────────────────────────────────────────────
@dataclass
class OXItem:
    statement: str
    answer: str  # "O" or "X"
    source_qid: int
    source_option: str


def convert_to_ox(q: ParsedQuestion, answer_num: int) -> list[OXItem]:
    items: list[OXItem] = []
    if q.qtype in ("opt-correct", "opt-wrong"):
        for i, opt in enumerate(q.options):
            if not opt or len(opt) < MIN_STMT_LEN:
                continue
            is_target = (i + 1) == answer_num
            if q.qtype == "opt-correct":
                ox = "O" if is_target else "X"
            else:
                ox = "X" if is_target else "O"
            items.append(OXItem(
                statement=opt,
                answer=ox,
                source_qid=q.qid,
                source_option=CIRCLED_INV.get(i + 1, f"_{i+1}"),
            ))
    elif q.qtype in ("sub-all-correct", "sub-all-wrong"):
        if not q.sub_items or not any(q.options):
            return []
        if not (1 <= answer_num <= 5):
            return []
        ans_text = q.options[answer_num - 1] or ""
        chosen = set(re.findall(r"[a-e]", ans_text))
        if not chosen:
            return []
        for ltr, item_raw in q.sub_items.items():
            item_text = re.sub(r"\s+", " ", item_raw).strip()
            if len(item_text) < MIN_STMT_LEN:
                continue
            is_chosen = ltr in chosen
            if q.qtype == "sub-all-correct":
                ox = "O" if is_chosen else "X"
            else:
                ox = "X" if is_chosen else "O"
            items.append(OXItem(
                statement=item_text,
                answer=ox,
                source_qid=q.qid,
                source_option=ltr,
            ))
    return items


# ── DB 적재 ─────────────────────────────────────────────────────────────
CPA_EXAM_GROUP_TPL = "회계사 1차 · {year}년 제{round}회"


def upsert_category(conn: sqlite3.Connection, meta: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO categories
           (slug, name, exam_group, subject, phase, source,
            exam_year, exam_round, display_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug) DO UPDATE SET
               name=excluded.name, exam_group=excluded.exam_group,
               subject=excluded.subject, phase=excluded.phase""",
        (meta["slug"], meta["subject"],
         CPA_EXAM_GROUP_TPL.format(year=meta["year"], round=meta["exam_round"]),
         meta["subject"], meta["phase"], "회계사 1차",
         meta["year"], meta["exam_round"], meta.get("display_order", 300))
    )
    cur.execute("SELECT id FROM categories WHERE slug=?", (meta["slug"],))
    return cur.fetchone()[0]


def compute_frequency_and_stars(conn: sqlite3.Connection) -> int:
    """회계사 카테고리(slug 'cpa-') 내 statement 해시별 frequency·star 갱신."""
    cat_ids = [r[0] for r in conn.execute("SELECT id FROM categories WHERE slug LIKE 'cpa-%'")]
    if not cat_ids:
        return 0
    rows = conn.execute(
        f"SELECT id, statement FROM questions WHERE category_id IN ({','.join('?'*len(cat_ids))})",
        cat_ids,
    ).fetchall()
    hash_map: dict[str, list[int]] = {}
    for qid, stmt in rows:
        h = stmt_hash(stmt or "")
        hash_map.setdefault(h, []).append(qid)
    n = 0
    for ids in hash_map.values():
        freq = len(ids)
        star = min(5, freq)
        conn.executemany(
            "UPDATE questions SET frequency=?, star_rating=? WHERE id=?",
            [(freq, star, qid) for qid in ids],
        )
        n += len(ids)
    conn.commit()
    return n


# ── 메인 ────────────────────────────────────────────────────────────────
def main() -> int:
    dry_run = "--dry-run" in sys.argv
    if not DB_PATH.exists():
        print(f"❌ DB 없음: {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    total_ox = 0
    summary: list[dict] = []

    for subj in CPA_SUBJECTS:
        exam_path = DRIVE_BASE / subj["exam_pdf"]
        ans_path = DRIVE_BASE / subj["answer_pdf"]
        print(f"\n[{subj['year']} 회계사 {subj['subject']}]")
        if not exam_path.exists():
            print(f"  ⚠ 시험지 없음: {exam_path}")
            continue
        if not ans_path.exists():
            print(f"  ⚠ 해설 없음: {ans_path}")
            continue

        # 정답 추출
        try:
            answers = parse_answer_table(ans_path)
            print(f"  해설 {ans_path.name[:40]}: 정답 {len(answers)}개")
        except Exception as e:
            print(f"  ⚠ 해설 파싱 실패: {e}")
            answers = {}

        # 시험지 추출
        try:
            qmap = parse_exam_pdf(exam_path, subj["qid_start"], subj["qid_end"])
            print(f"  시험지: {len(qmap)}문항 파싱됨")
        except Exception as e:
            print(f"  ⚠ 시험지 파싱 실패: {e}")
            continue

        cat_id = upsert_category(conn, subj) if not dry_run else -1
        ox_count = 0
        skip_count = 0
        unknown_count = 0
        no_ans_count = 0
        for qid in range(subj["qid_start"], subj["qid_end"] + 1):
            q = qmap.get(qid)
            if not q:
                skip_count += 1
                continue
            if q.qtype == "unknown":
                unknown_count += 1
                continue
            ans_num = answers.get(qid)
            if ans_num is None:
                no_ans_count += 1
                continue
            ox_items = convert_to_ox(q, ans_num)
            if not ox_items:
                skip_count += 1
                continue
            if not dry_run:
                for ox in ox_items:
                    conn.execute(
                        """INSERT OR REPLACE INTO questions
                           (category_id, statement, answer, explanation,
                            source_qid, source_option, qtype, source_pdf,
                            explanation_o, explanation_x,
                            meta_quality, frequency, star_rating)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,1,0)""",
                        (cat_id, ox.statement, ox.answer, "",
                         ox.source_qid, ox.source_option, q.qtype,
                         exam_path.name, None, None, 10)
                    )
            ox_count += len(ox_items)

        if not dry_run:
            conn.execute(
                "UPDATE categories SET total_count=(SELECT COUNT(*) FROM questions WHERE category_id=?) WHERE id=?",
                (cat_id, cat_id),
            )
            conn.commit()

        total_ox += ox_count
        summary.append({
            "label": f"{subj['year']} {subj['subject']}",
            "ox": ox_count, "skip": skip_count,
            "unknown": unknown_count, "no_ans": no_ans_count,
        })
        print(f"  OX 변환: {ox_count}건 (스킵 {skip_count}, qtype unknown {unknown_count}, 정답없음 {no_ans_count})")

    # frequency 분석
    if not dry_run and total_ox > 0:
        n = compute_frequency_and_stars(conn)
        print(f"\n★ 중요도 분석: {n}건 frequency/star 갱신")
        # 반복 출제 Top
        dup = conn.execute("""
            SELECT q.statement, COUNT(*) cnt
            FROM questions q JOIN categories c ON q.category_id=c.id
            WHERE c.slug LIKE 'cpa-%' AND q.frequency > 1
            GROUP BY q.statement ORDER BY cnt DESC LIMIT 5
        """).fetchall()
        if dup:
            print("\n[반복 출제 Top 5]")
            for r in dup:
                print(f"  {r[1]}회 | {r[0][:80]}")

    conn.close()
    print(f"\n{'='*60}")
    print(f"CPA {'(DRY RUN)' if dry_run else '완료'}  TOTAL OX={total_ox}")
    print(f"{'='*60}")
    for s in summary:
        print(f"  {s['label']:24}  OX={s['ox']:3}  skip={s['skip']:2}  unk={s['unknown']:2}  no_ans={s['no_ans']:2}")

    if not dry_run:
        print("\n다음 단계:")
        print("  1. python3 scripts/validate_ox.py --apply --strip-artifacts")
        print("  2. python3 scripts/export_quiz_json.py --both")
    return 0


if __name__ == "__main__":
    sys.exit(main())
