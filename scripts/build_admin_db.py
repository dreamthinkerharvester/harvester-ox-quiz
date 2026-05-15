#!/usr/bin/env python3
"""
행정사 기출문제 PDF → OX 퀴즈 SQLite DB 변환 + 중요도(frequency/star_rating) 분석.

처리 전략:
  행정학개론: 이형재(or 김재준) 해설 PDF → 정답표 + 해설 텍스트 추출 → OX 변환
  행정법/민법: 시험지 파싱 후 해설 텍스트는 enrich_session.py 세션 보강으로 입력

중요도:
  frequency  = 동일 문항이 여러 연도에 등장한 횟수 (텍스트 정규화 유사도 기반)
  star_rating = min(5, frequency)   → ★ 1~5개

사용법:
  python3 scripts/build_admin_db.py          # 전체 실행
  python3 scripts/build_admin_db.py --dry-run  # DB 변경 없이 통계만
"""

import hashlib
import re
import sqlite3
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
DRIVE_BASE = Path.home() / "Library/CloudStorage/GoogleDrive-kakaiuina@gmail.com/내 드라이브/공기출"

# ── 과목별 PDF 경로 + 메타 ─────────────────────────────────────────────────
ADMIN_SUBJECTS = [
    # (year, 직렬, 과목, 시험지_PDF, 해설_PDF_list, qid_start, qid_end, 해설_offset)
    # qid_start..qid_end: 시험지 문항 번호, 해설_offset: 해설PDF 번호 = 시험지 번호 + offset
    {
        "year": 2025, "exam_round": 13,
        "subject": "행정학개론", "phase": "1교시",
        "slug": "admin-2025-r13-haengjeong",
        "exam_pdf": "2025/전문직-행정사/행정학개론 문제/행정학개론.pdf",
        "answer_pdfs": [
            ("2025/전문직-행정사/행정학개론 문제/2025 행정사 행정학개론 해설 이형재.pdf", 0),
            ("2025/전문직-행정사/행정학개론 문제/2025 행정사 행정학개론 해설 김재준.pdf", 0),
        ],
        "qid_start": 51, "qid_end": 75,
    },
    {
        "year": 2025, "exam_round": 13,
        "subject": "행정법", "phase": "1교시",
        "slug": "admin-2025-r13-haengjeongbeop",
        "exam_pdf": "2025/전문직-행정사/행정법 문제/행정법.pdf",
        "answer_pdfs": [],  # 이미지 기반 — 해설은 enrich_session 보강
        "qid_start": 26, "qid_end": 50,
    },
    {
        "year": 2025, "exam_round": 13,
        "subject": "민법", "phase": "1교시",
        "slug": "admin-2025-r13-minbeop",
        "exam_pdf": "2025/전문직-행정사/민법/민법.pdf",
        "answer_pdfs": [],
        "qid_start": 1, "qid_end": 25,
    },
    {
        "year": 2024, "exam_round": 12,
        "subject": "행정학개론", "phase": "1교시",
        "slug": "admin-2024-r12-haengjeong",
        "exam_pdf": "2024/전문직-행정사/행정학개론 문제/행정학개론.pdf",
        "answer_pdfs": [
            ("2024/전문직-행정사/행정학개론 문제/2024 행정사 행정학개론 해설 이형재.pdf", 50),  # 01~25 체계
            ("2024/전문직-행정사/행정학개론 문제/2024 행정사 행정학개론 해설 김재준.pdf", 0),   # 51~75 직접
        ],
        # 이형재(01~25)+50=51~75 / 김재준(51~75)+0=51~75
        "qid_start": 51, "qid_end": 75,
    },
    {
        "year": 2024, "exam_round": 12,
        "subject": "행정법", "phase": "1교시",
        "slug": "admin-2024-r12-haengjeongbeop",
        "exam_pdf": "2024/전문직-행정사/행정법 문제/행정법.pdf",
        "answer_pdfs": [],
        "qid_start": 26, "qid_end": 50,
    },
    {
        "year": 2024, "exam_round": 12,
        "subject": "민법", "phase": "1교시",
        "slug": "admin-2024-r12-minbeop",
        "exam_pdf": "2024/전문직-행정사/민법/민법.pdf",
        "answer_pdfs": [],
        "qid_start": 1, "qid_end": 25,
    },
]

CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
CIRCLED_INV = {v: k for k, v in CIRCLED.items()}
SUB_LETTERS = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]
MIN_STMT_LEN = 12


# ── 텍스트 정규화 (중복 감지용) ──────────────────────────────────────────
def normalize_stmt(s: str) -> str:
    """공백·구두점 제거 + NFC → 유사도 비교용 해시 키."""
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s.lower()


def stmt_hash(s: str) -> str:
    return hashlib.sha256(normalize_stmt(s).encode()).hexdigest()[:16]


# ── PDF 추출 ─────────────────────────────────────────────────────────────
def pdf_to_text(pdf_path: Path) -> str:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=False
    )
    return result.stdout or ""


# ── 정답표 파싱 (이형재 / 김재준 해설 PDF) ──────────────────────────────
ANSWER_LINE_RE = re.compile(
    r"\b(\d{1,2})\s+([①②③④⑤])\s+(?:\d{1,2}\s+[①②③④⑤]\s+){0,4}"
)

def parse_answer_table(pdf_path: Path, qid_offset: int = 0) -> dict:
    """정답표 파싱 → {exam_qid: answer_num (1~5)}.

    이형재 해설: "01 ① 02 ② ... 05 ③" 라인 패턴
    김재준 해설: "51. ④" 또는 "문 51. ... 정답 및 해설 51. ④" 패턴
    """
    text = pdf_to_text(pdf_path)
    answers = {}

    # 방법 1: "N ① N ② ..." 테이블 스타일 (이형재)
    for m in re.finditer(r"(\d{1,2})\s+([①②③④⑤])", text):
        qnum = int(m.group(1))
        ans_char = m.group(2)
        exam_qnum = qnum + qid_offset
        if 1 <= exam_qnum <= 100 and ans_char in CIRCLED:
            answers[exam_qnum] = CIRCLED[ans_char]

    # 방법 2: "51. ④" 스타일 (김재준)
    if not answers:
        for m in re.finditer(r"(\d{1,2})\.\s*([①②③④⑤])", text):
            qnum = int(m.group(1))
            ans_char = m.group(2)
            exam_qnum = qnum + qid_offset
            if 1 <= exam_qnum <= 100 and ans_char in CIRCLED:
                answers[exam_qnum] = CIRCLED[ans_char]

    return answers


# ── 해설 텍스트 파싱 (이형재·김재준) ────────────────────────────────────
def parse_explanations(pdf_path: Path, qid_offset: int = 0) -> dict:
    """문항별 해설 텍스트 파싱 → {exam_qid: explanation_text}."""
    text = pdf_to_text(pdf_path)
    explanations = {}

    # 각 문항 번호 블록 감지 (이형재 스타일: 단독 줄의 숫자)
    qnum_pattern = re.compile(r"^\s*(\d{1,2})\s*$", re.MULTILINE)
    positions = [(m.start(), int(m.group(1))) for m in qnum_pattern.finditer(text)
                 if 1 <= int(m.group(1)) <= 75]

    for i, (pos, qnum) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        block = text[pos:end]
        # 해설 섹션 추출
        expl_match = re.search(r"해설\s*\n(.+?)(?=\n\s*정답|\Z)", block, re.DOTALL)
        if expl_match:
            expl = re.sub(r"\s+", " ", expl_match.group(1)).strip()[:400]
            exam_qnum = qnum + qid_offset
            if 1 <= exam_qnum <= 100 and expl:
                explanations[exam_qnum] = expl

    return explanations


# ── 시험지 파싱 ─────────────────────────────────────────────────────────
@dataclass
class ParsedQuestion:
    qid: int
    stem: str
    qtype: str
    options: list = field(default_factory=list)
    sub_items: dict = field(default_factory=dict)


def detect_qtype(stem: str) -> str:
    has_wrong = bool(re.search(r"옳지\s*않은|틀린|타당하지\s*않은|아닌", stem))
    has_correct = bool(re.search(r"옳은|맞는|타당한|올바른", stem))
    has_all = bool(re.search(r"모두\s*고른|모두\s*옳은|모두\s*옳지", stem))
    if has_all and has_wrong:
        return "sub-all-wrong"
    if has_all:
        return "sub-all-correct"
    if has_wrong:
        return "opt-wrong"
    if has_correct:
        return "opt-correct"
    return "unknown"


def parse_exam_pdf(pdf_path: Path, qid_start: int, qid_end: int) -> dict:
    """시험지 PDF → {qid: ParsedQuestion}."""
    text = pdf_to_text(pdf_path)
    qmap = {}
    qstart_pat = re.compile(r"^\s*(\d{1,3})\.\s+(.+)", re.MULTILINE)
    matches = list(qstart_pat.finditer(text))

    for i, m in enumerate(matches):
        qid = int(m.group(1))
        if not (qid_start <= qid <= qid_end):
            continue
        if qid in qmap:
            continue
        block_start = m.start()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[block_start:block_end]

        first_opt = re.search(r"[①ㄱ]", block)
        stem_end = first_opt.start() if first_opt else len(block)
        stem = block[:stem_end]
        stem = re.sub(r"^\s*\d+\.\s+", "", stem).strip()
        stem = re.sub(r"\s+", " ", stem)

        qtype = detect_qtype(stem)

        # 옵션 추출
        options = [None] * 5
        positions_opt = []
        for sym, idx in CIRCLED.items():
            for om in re.finditer(re.escape(sym), block):
                positions_opt.append((om.start(), idx))
        positions_opt.sort()
        seen_opt = set()
        sel = []
        for pos, idx in positions_opt:
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

        # ㄱㄴㄷ sub-items
        sub_items = {}
        if qtype.startswith("sub-"):
            sub_positions = []
            first_circ = re.search(r"[①②③④⑤]", block)
            cutoff = first_circ.start() if first_circ else len(block)
            for ltr in SUB_LETTERS:
                for sm in re.finditer(rf"{ltr}\.\s", block):
                    if sm.start() < cutoff:
                        sub_positions.append((sm.start(), ltr))
            sub_positions.sort()
            seen_ltr = set()
            final_sub = []
            for pos, ltr in sub_positions:
                if ltr not in seen_ltr:
                    seen_ltr.add(ltr)
                    final_sub.append((pos, ltr))
            final_sub.sort()
            for j, (pos, ltr) in enumerate(final_sub):
                end = final_sub[j + 1][0] if j + 1 < len(final_sub) else cutoff
                st = block[pos + len(ltr) + 1:end].strip()
                sub_items[ltr] = re.sub(r"\s+", " ", st).strip()

        qmap[qid] = ParsedQuestion(
            qid=qid, stem=stem, qtype=qtype,
            options=options, sub_items=sub_items,
        )
    return qmap


# ── OX 변환 ─────────────────────────────────────────────────────────────
@dataclass
class OXItem:
    statement: str
    answer: str
    source_qid: int
    source_option: str
    explanation: str = ""


def convert_to_ox(q: ParsedQuestion, answer_num: int) -> list:
    items = []
    if q.qtype in ("opt-correct", "opt-wrong"):
        for i, opt in enumerate(q.options):
            if not opt or len(opt) < MIN_STMT_LEN:
                continue
            is_target = (i + 1) == answer_num
            ox = ("O" if q.qtype == "opt-correct" else "X") if is_target \
                 else ("X" if q.qtype == "opt-correct" else "O")
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
        chosen = set(re.findall(r"[ㄱㄴㄷㄹㅁ]", ans_text))
        if not chosen:
            return []
        for ltr, item_raw in q.sub_items.items():
            item_text = re.sub(r"\s+", " ", item_raw).strip()
            if len(item_text) < MIN_STMT_LEN:
                continue
            is_chosen = ltr in chosen
            ox = ("O" if q.qtype == "sub-all-correct" else "X") if is_chosen \
                 else ("X" if q.qtype == "sub-all-correct" else "O")
            items.append(OXItem(
                statement=item_text,
                answer=ox,
                source_qid=q.qid,
                source_option=ltr,
            ))
    return items


# ── DB 헬퍼 ─────────────────────────────────────────────────────────────
ADMIN_EXAM_GROUP_TPL = "행정사 1차 · {year}년 제{round}회"


def ensure_admin_columns(conn):
    """star_rating, frequency 컬럼이 없으면 추가."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)")}
    for col, defn in [("star_rating", "INTEGER NOT NULL DEFAULT 0"),
                      ("frequency",   "INTEGER NOT NULL DEFAULT 1")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE questions ADD COLUMN {col} {defn}")
    conn.commit()


def upsert_category(conn, meta: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO categories
           (slug, name, exam_group, subject, phase, source, exam_year, exam_round, display_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug) DO UPDATE SET
               name=excluded.name, exam_group=excluded.exam_group,
               subject=excluded.subject, phase=excluded.phase""",
        (meta["slug"], meta["subject"],
         ADMIN_EXAM_GROUP_TPL.format(year=meta["year"], round=meta["exam_round"]),
         meta["subject"], meta["phase"], "행정사 1차",
         meta["year"], meta["exam_round"], meta.get("display_order", 200))
    )
    conn.execute("SELECT id FROM categories WHERE slug=?", (meta["slug"],))
    cur.execute("SELECT id FROM categories WHERE slug=?", (meta["slug"],))
    return cur.fetchone()[0]


def compute_frequency_and_stars(conn):
    """전체 questions 중 statement 해시가 같은 것들의 frequency/star_rating 갱신.
    행정사 카테고리(slug 'admin-') 한정으로 비교.
    """
    # 행정사 카테고리 id 수집
    admin_cat_ids = set(
        r[0] for r in conn.execute(
            "SELECT id FROM categories WHERE slug LIKE 'admin-%'"
        )
    )
    if not admin_cat_ids:
        return 0
    # statement → row_ids 매핑
    rows = conn.execute(
        f"SELECT id, statement FROM questions WHERE category_id IN ({','.join('?'*len(admin_cat_ids))})",
        list(admin_cat_ids),
    ).fetchall()
    hash_map = {}
    for qid, stmt in rows:
        h = stmt_hash(stmt or "")
        hash_map.setdefault(h, []).append(qid)

    updated = 0
    for h, ids in hash_map.items():
        freq = len(ids)
        star = min(5, freq)
        conn.executemany(
            "UPDATE questions SET frequency=?, star_rating=? WHERE id=?",
            [(freq, star, qid) for qid in ids],
        )
        updated += len(ids)
    conn.commit()
    return updated


# ── 메인 ─────────────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv
    conn = sqlite3.connect(DB_PATH)
    ensure_admin_columns(conn)

    total_ox = 0
    total_with_expl = 0
    summary = []

    for subj in ADMIN_SUBJECTS:
        exam_pdf_path = DRIVE_BASE / subj["exam_pdf"]
        print(f"\n[{subj['year']} 행정사 {subj['subject']}]")
        if not exam_pdf_path.exists():
            print(f"  ⚠ 시험지 없음: {exam_pdf_path}")
            continue

        # 정답 파싱
        answers = {}
        explanations = {}
        for ans_pdf_rel, offset in subj.get("answer_pdfs", []):
            ans_path = DRIVE_BASE / ans_pdf_rel
            if not ans_path.exists():
                print(f"  ⚠ 해설 없음: {ans_path.name}")
                continue
            try:
                ans = parse_answer_table(ans_path, qid_offset=offset)
                expl = parse_explanations(ans_path, qid_offset=offset)
                if len(ans) > len(answers):
                    answers = ans
                for k, v in expl.items():
                    if k not in explanations:
                        explanations[k] = v
                print(f"  → 해설 {ans_path.name[:40]}: 정답 {len(ans)}건, 해설 {len(expl)}건")
            except Exception as e:
                print(f"  ⚠ 해설 파싱 실패: {e}")

        # 시험지 파싱
        qmap = parse_exam_pdf(exam_pdf_path, subj["qid_start"], subj["qid_end"])
        print(f"  시험지: {len(qmap)}문항 파싱됨")

        # 정답 없는 경우 스킵 안 하고 unknown으로 저장 (나중에 세션 보강)
        cat_id = upsert_category(conn, subj)
        ox_count = 0
        skip_count = 0
        expl_count = 0

        for qid in range(subj["qid_start"], subj["qid_end"] + 1):
            q = qmap.get(qid)
            if not q or q.qtype == "unknown":
                skip_count += 1
                continue
            ans_num = answers.get(qid)
            if ans_num is None:
                skip_count += 1
                continue
            ox_items = convert_to_ox(q, ans_num)
            if not ox_items:
                skip_count += 1
                continue

            expl_text = explanations.get(qid, "")

            if not dry_run:
                for ox in ox_items:
                    # 해설 결정: explanation_o/x 중 정답에 해당하는 것에 엑스플 넣기
                    explanation_o = expl_text if ox.answer == "O" else None
                    explanation_x = expl_text if ox.answer == "X" else None
                    conn.execute(
                        """INSERT OR REPLACE INTO questions
                           (category_id, statement, answer, explanation,
                            source_qid, source_option, qtype, source_pdf,
                            explanation_o, explanation_x,
                            meta_quality, frequency, star_rating)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,1,0)""",
                        (cat_id, ox.statement, ox.answer, expl_text,
                         ox.source_qid, ox.source_option, q.qtype,
                         exam_pdf_path.name,
                         explanation_o, explanation_x,
                         50 if expl_text else 10)
                    )
            ox_count += len(ox_items)
            if expl_text:
                expl_count += len(ox_items)

        if not dry_run:
            conn.execute(
                """UPDATE categories SET total_count=(
                       SELECT COUNT(*) FROM questions WHERE category_id=?
                   ) WHERE id=?""",
                (cat_id, cat_id)
            )
            conn.commit()

        total_ox += ox_count
        total_with_expl += expl_count
        summary.append({
            "subject": f"{subj['year']} {subj['subject']}",
            "ox": ox_count, "skip": skip_count, "expl": expl_count,
        })
        print(f"  OX 변환: {ox_count}건, 스킵: {skip_count}건, 해설 있음: {expl_count}건")

    # frequency / star_rating 갱신
    if not dry_run:
        n_updated = compute_frequency_and_stars(conn)
        print(f"\n★ 중요도 분석 완료: {n_updated}건 frequency/star_rating 갱신")

        # 중복 문항 확인
        dup = conn.execute("""
            SELECT q.statement, COUNT(*) cnt, GROUP_CONCAT(c.slug) slugs
            FROM questions q JOIN categories c ON q.category_id=c.id
            WHERE c.slug LIKE 'admin-%' AND q.frequency > 1
            GROUP BY q.statement
            ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        if dup:
            print("\n[반복 출제 문항 Top 10 (frequency > 1)]")
            for r in dup:
                print(f"  {r[1]}회 | {r[0][:80]}...")

    conn.close()

    print(f"\n{'=' * 60}")
    print(f"행정사 {'(DRY RUN)' if dry_run else '완료'}")
    print(f"{'=' * 60}")
    for s in summary:
        print(f"  {s['subject']:30} OX={s['ox']:3}  skip={s['skip']:2}  해설={s['expl']:3}")
    print(f"\n  TOTAL OX: {total_ox}건  해설 있음: {total_with_expl}건")

    if not dry_run:
        print("\n다음 단계:")
        print("  1. 행정법/민법 해설: python3 scripts/enrich_session.py export --category admin-2025-r13-haengjeongbeop --limit 50")
        print("  2. JSON export:      python3 scripts/export_quiz_json.py --both")
        print("  3. commit/push:      git add data/ && git commit && git push")


if __name__ == "__main__":
    main()
