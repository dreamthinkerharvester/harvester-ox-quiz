#!/usr/bin/env python3
"""
세무사 기출문제 PDF → OX 퀴즈 SQLite DB 변환 파이프라인.

사용법:
    python3 scripts/build_quiz_db.py

처리 단계:
    1. _refs/세무사기출문제/*.pdf → 텍스트 추출 (pdftotext -layout 가정)
    2. 가답안.pdf → 과목별 정답 맵
    3. 시험지 PDF → 문항/선택지 파싱
    4. OX 변환:
       - Type A "옳은 것은?": 정답 옵션 = O, 나머지 = X
       - Type B "옳지 않은 것은?": 정답 옵션 = X, 나머지 = O
       - Type C "옳은/옳지 않은 것을 모두 고른 것은?" (ㄱㄴㄷㄹ): 정답 조합으로 ㄱㄴㄷㄹ 각각 OX
       - 기타 (계산 문제 등): 스킵
    5. SQLite data/quiz.db에 categories + questions 테이블로 적재
"""

import re
import sqlite3
import subprocess
import sys
import unicodedata
from pathlib import Path
from dataclasses import dataclass


def nfc(s: str) -> str:
    """macOS 파일명(NFD)을 NFC로 정규화."""
    return unicodedata.normalize("NFC", s)


def clean_statement(s: str) -> str:
    """PDF 추출 산출물의 띄어쓰기 artifact 정리 (보수적).

    PDF 폰트 커닝으로 한글 1글자가 단어에서 분리된 경우만 합침.
    예: "이행을 청 구하는" → "이행을 청구하는" (1글자 "청"을 다음 단어와 결합)
    정상 띄어쓰기 (2글자+ 단어 사이 공백) 는 보존.
    """
    if not s:
        return s
    # 다중 공백 → 단일
    s = re.sub(r"\s+", " ", s).strip()
    # 패턴: "단어(2+자) 1글자 단어(1+자)" → "단어 1글자단어" (1글자를 뒤 단어에 결합)
    pat = re.compile(r"([가-힣]{2,})\s+([가-힣])\s+([가-힣]+)")
    prev = None
    while s != prev:
        prev = s
        s = pat.sub(r"\1 \2\3", s)
    return s


# 의미 있는 OX 진술의 최소 길이 (한글 기준).
# 너무 짧으면 단순 용어/개념 나열 — 독립 OX로 부적합.
MIN_OX_STATEMENT_LEN = 12

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "_refs" / "세무사기출문제"
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
SEEDS_DIR = PROJECT_ROOT / "data" / "seeds"
TMP_DIR = Path("/tmp")

# 직접 작성한 시드 카테고리 (CSV 파일 + 메타). 인트로 디폴트는 is_default=True 로 표시.
SEED_CATEGORIES = [
    {
        "slug": "general-knowledge",
        "name": "기본상식",
        "subject": "일반상식",
        "exam_group": None,                    # 단독 카테고리
        "source": "직접 큐레이션 (역사·과학·지리·문화·일상)",
        "is_default": True,
        "display_order": 1,
        "csv": "general-knowledge.csv",
    },
]

# 시험 메타
EXAM_YEAR = 2026
EXAM_ROUND = 63
EXAM_SOURCE = "세무사 1차"
EXAM_GROUP_TAX = "세무사 1차 · 2026년 제63회"

# 과목 ↔ PDF 파일 매핑 + 메타데이터
SUBJECT_MAP = [
    {"slug": "tax-2026-r63-jaejeong",   "name": "재정학",       "subject": "재정학",       "phase": "1교시",         "display_order": 11, "pdf": "1교시 시험지 원본.pdf",             "qid_start": 1,  "qid_end": 40},
    {"slug": "tax-2026-r63-sebeop",     "name": "세법학개론",    "subject": "세법학개론",    "phase": "1교시",         "display_order": 12, "pdf": "1교시 시험지 원본.pdf",             "qid_start": 41, "qid_end": 80},
    {"slug": "tax-2026-r63-hoegyeoe",   "name": "회계학개론",    "subject": "회계학개론",    "phase": "2교시",         "display_order": 13, "pdf": "2교시 시험지 원본(상법).pdf",      "qid_start": 1,  "qid_end": 40},
    {"slug": "tax-2026-r63-sangbeop",   "name": "상법",         "subject": "상법",         "phase": "2교시 (선택)",  "display_order": 14, "pdf": "2교시 시험지 원본(상법).pdf",      "qid_start": 41, "qid_end": 80},
    {"slug": "tax-2026-r63-minbeop",    "name": "민법",         "subject": "민법",         "phase": "2교시 (선택)",  "display_order": 15, "pdf": "2교시 시험지 원본(민법).pdf",      "qid_start": 41, "qid_end": 80},
    {"slug": "tax-2026-r63-haengjeong", "name": "행정소송법",    "subject": "행정소송법",    "phase": "2교시 (선택)",  "display_order": 16, "pdf": "2교시 시험지 원본(행정소송법).pdf", "qid_start": 41, "qid_end": 80},
]


# ── PDF 추출 ─────────────────────────────────────────────────────────────
def pdf_to_text(pdf_path: Path, txt_path: Path) -> str:
    """pdftotext -layout 으로 PDF를 텍스트로 변환. 캐시 사용."""
    if not txt_path.exists() or txt_path.stat().st_mtime < pdf_path.stat().st_mtime:
        subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
    return txt_path.read_text(encoding="utf-8")


# ── 가답안 파싱 ───────────────────────────────────────────────────────────
def parse_answer_key(text: str) -> dict:
    """가답안 텍스트 → {(과목명, 문항번호): 정답번호}.

    포맷:
        재정학
         문항 정답 ...
         1    1    2    4    ...
    """
    answers = {}
    current_subject = None
    subject_pat = re.compile(r"^\s*(재정학|세법학개론|회계학개론|상법|민법|행정소송법)\s*$")
    # "1    4    2    2    ..." 같은 (qid answer) 페어 라인. 공백·탭 혼재 허용.
    pair_pat = re.compile(r"\b(\d{1,3})\s+(\d)\b")

    for line in text.splitlines():
        line = line.rstrip()
        m = subject_pat.match(line)
        if m:
            current_subject = m.group(1)
            continue
        if not current_subject:
            continue
        # "문항 정답 문항 정답..." 헤더 스킵
        if "문항" in line and "정답" in line:
            continue
        # 모든 (qid, ans) 페어 추출
        for qid_str, ans_str in pair_pat.findall(line):
            qid = int(qid_str)
            ans = int(ans_str)
            # 합리적 범위: qid 1-100, ans 1-5
            if 1 <= qid <= 100 and 1 <= ans <= 5:
                answers[(current_subject, qid)] = ans
    return answers


# ── 시험지 파싱 ───────────────────────────────────────────────────────────
@dataclass
class ParsedQuestion:
    qid: int
    stem: str          # 질문 본문
    qtype: str         # 'opt-correct' | 'opt-wrong' | 'sub-all-correct' | 'sub-all-wrong' | 'unknown'
    options: list      # ['option1', 'option2', ...] (5개)
    sub_items: dict    # {ㄱ: '...', ㄴ: '...', ...} (Type C only)


# 동그라미 숫자 → 인덱스 (① = 1, ⑤ = 5)
CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
SUB_LETTERS = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]


def detect_question_type(stem: str) -> str:
    """질문 stem에서 OX 변환 가능 유형 판정."""
    has_correct = "옳은" in stem or "맞는" in stem or "타당한" in stem
    has_wrong = "옳지 않은" in stem or "틀린" in stem or "타당하지 않은" in stem
    has_all = "모두 고른" in stem or "모두 옳은" in stem or "모두 옳지" in stem
    # "모두 고른 것은?"인데 "옳은"이 명시 안 됐어도 보통 "옳은"
    if has_all and has_wrong:
        return "sub-all-wrong"
    if has_all:
        return "sub-all-correct"
    if has_wrong:
        return "opt-wrong"
    if has_correct:
        return "opt-correct"
    return "unknown"


def parse_exam_text(text: str, qid_range: tuple) -> dict:
    """시험지 텍스트에서 qid_range 범위의 문제 추출.

    각 문제 블록은 "N. " 으로 시작, 다음 "(N+1). " 까지가 한 문제.
    """
    qid_start, qid_end = qid_range
    qmap = {}

    # 문제 블록 분할: "\n\nN. " 또는 라인 시작 "N. "
    # qid 가 1~100 범위인 정수만 매칭
    qstart_pat = re.compile(r"^\s*(\d{1,3})\.\s+(.+)", re.MULTILINE)

    matches = list(qstart_pat.finditer(text))
    for i, m in enumerate(matches):
        qid = int(m.group(1))
        if not (qid_start <= qid <= qid_end):
            continue
        # 같은 qid 가 본문에서 또 등장할 수 있음 (페이지 헤더 등). 첫 매칭만.
        if qid in qmap:
            continue
        # 다음 문제 시작 또는 텍스트 끝까지가 이 문제 블록
        block_start = m.start()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[block_start:block_end]

        # stem: "N. " 부터 첫 ① 또는 첫 ㄱ 까지
        first_opt = re.search(r"[①ㄱ]", block)
        stem_end = first_opt.start() if first_opt else len(block)
        stem = block[:stem_end]
        # "N. " prefix 제거
        stem = re.sub(r"^\s*\d+\.\s+", "", stem).strip()
        # 줄바꿈 정리
        stem = re.sub(r"\s+", " ", stem)

        qtype = detect_question_type(stem)

        # 옵션 5개 추출 (① ~ ⑤)
        options = parse_options(block)

        # Type C: ㄱㄴㄷㄹ sub-items 추출
        sub_items = {}
        if qtype.startswith("sub-"):
            sub_items = parse_sub_items(block)

        qmap[qid] = ParsedQuestion(
            qid=qid, stem=stem, qtype=qtype, options=options, sub_items=sub_items
        )
    return qmap


def parse_options(block: str) -> list:
    """블록에서 ① ~ ⑤ 옵션 텍스트 추출."""
    options = [None, None, None, None, None]
    # 각 옵션 마커 위치 찾기
    positions = []
    for sym, idx in CIRCLED.items():
        for m in re.finditer(re.escape(sym), block):
            positions.append((m.start(), idx))
    positions.sort()
    if len(positions) < 5:
        return options
    # 옵션 1-5 만 사용 (한 문제 안의 첫 5개)
    seen_idx = set()
    selected = []
    for pos, idx in positions:
        if idx in seen_idx:
            continue
        seen_idx.add(idx)
        selected.append((pos, idx))
        if len(selected) == 5:
            break
    selected.sort()
    for i, (pos, idx) in enumerate(selected):
        end = selected[i + 1][0] if i + 1 < len(selected) else len(block)
        text = block[pos + 1 : end].strip()  # ① 자체는 1글자 = 마커 다음부터
        # 옵션 텍스트 정리 (다음 줄 문제 시작·페이지 헤더 제거)
        text = re.sub(r"\s+", " ", text)
        # 너무 길면 첫 마침표/괄호 단위로 자름 (페이지 푸터 잡혀 들어오는 경우 대비)
        text = re.sub(r"2026년도.*", "", text)
        text = text.strip()
        options[idx - 1] = text
    return options


def parse_sub_items(block: str) -> dict:
    """블록에서 ㄱ. / ㄴ. / ㄷ. / ㄹ. sub-item 텍스트 추출."""
    items = {}
    positions = []
    for letter in SUB_LETTERS:
        for m in re.finditer(rf"{letter}\.\s", block):
            positions.append((m.start(), letter))
    positions.sort()
    # 첫 ① 마커 위치 — sub-items 는 그 이전에만 존재
    first_circled = re.search(r"[①②③④⑤]", block)
    cutoff = first_circled.start() if first_circled else len(block)
    selected = [(p, l) for p, l in positions if p < cutoff]
    seen = set()
    final = []
    for pos, letter in selected:
        if letter in seen:
            continue
        seen.add(letter)
        final.append((pos, letter))
    final.sort()
    for i, (pos, letter) in enumerate(final):
        end = final[i + 1][0] if i + 1 < len(final) else cutoff
        text = block[pos + len(letter) + 1 : end].strip()  # "ㄱ." 다음부터
        text = re.sub(r"\s+", " ", text).strip()
        items[letter] = text
    return items


# ── OX 변환 ──────────────────────────────────────────────────────────────
@dataclass
class OXItem:
    statement: str
    answer: str  # 'O' | 'X'
    source_qid: int
    source_option: str   # '①', '②', ..., 'ㄱ', 'ㄴ', ...


def convert_to_ox(q: ParsedQuestion, answer_num: int) -> list:
    """문제 + 정답번호 → OX 항목 리스트.

    Type A (opt-correct): 정답 옵션 = O, 나머지 = X
    Type B (opt-wrong):   정답 옵션 = X, 나머지 = O
    Type C (sub-all-*):   정답 조합으로 ㄱㄴㄷㄹ 분해
    기타: [] (스킵)
    """
    ox_items = []

    if q.qtype in ("opt-correct", "opt-wrong"):
        if not all(q.options):
            return []  # 옵션 누락 시 스킵
        for i, opt_raw in enumerate(q.options):
            opt_text = clean_statement(opt_raw or "")
            if len(opt_text) < MIN_OX_STATEMENT_LEN:
                continue  # 옵션 너무 짧거나 빈 경우
            # opt-correct: i+1 == answer_num 이면 O, 아니면 X
            # opt-wrong:   i+1 == answer_num 이면 X (이게 틀린 답), 아니면 O
            is_target = (i + 1) == answer_num
            if q.qtype == "opt-correct":
                ox_answer = "O" if is_target else "X"
            else:  # opt-wrong
                ox_answer = "X" if is_target else "O"
            ox_items.append(
                OXItem(
                    statement=opt_text,
                    answer=ox_answer,
                    source_qid=q.qid,
                    source_option=list(CIRCLED.keys())[i],
                )
            )
        return ox_items

    if q.qtype in ("sub-all-correct", "sub-all-wrong"):
        if not q.sub_items or not all(q.options):
            return []
        # 정답 옵션 텍스트에서 ㄱ/ㄴ/ㄷ/ㄹ 추출
        if not (1 <= answer_num <= 5):
            return []
        answer_text = q.options[answer_num - 1] or ""
        chosen_letters = set(re.findall(r"[ㄱㄴㄷㄹㅁ]", answer_text))
        if not chosen_letters:
            return []
        # sub-all-correct: chosen = TRUE, 나머지 = FALSE
        # sub-all-wrong:   chosen = FALSE, 나머지 = TRUE
        for letter, item_raw in q.sub_items.items():
            item_text = clean_statement(item_raw or "")
            if len(item_text) < MIN_OX_STATEMENT_LEN:
                continue
            is_chosen = letter in chosen_letters
            if q.qtype == "sub-all-correct":
                ox_answer = "O" if is_chosen else "X"
            else:  # sub-all-wrong
                ox_answer = "X" if is_chosen else "O"
            ox_items.append(
                OXItem(
                    statement=item_text,
                    answer=ox_answer,
                    source_qid=q.qid,
                    source_option=letter,
                )
            )
        return ox_items

    return []  # unknown 유형 스킵


# ── DB 적재 ──────────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    exam_group TEXT,            -- 그룹 라벨 (e.g. "세무사 1차 · 2026년 제63회"). 없으면 단독 카테고리
    subject TEXT,               -- 과목명 (e.g. "재정학")
    phase TEXT,                 -- 교시 (e.g. "1교시", "2교시 (선택)")
    source TEXT,
    exam_year INTEGER,
    exam_round INTEGER,
    is_default INTEGER NOT NULL DEFAULT 0,  -- 1이면 인트로 디폴트 선택
    display_order INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    statement TEXT NOT NULL,
    answer TEXT NOT NULL CHECK(answer IN ('O', 'X')),
    explanation TEXT,
    source_qid INTEGER,
    source_option TEXT,
    qtype TEXT,
    difficulty TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- v2 메타 (exam-ox-pipeline) ----------------------------------------
    tags TEXT,                            -- JSON array string
    topic TEXT,                           -- 출제범위
    theory TEXT,                          -- 1-line 관련이론
    explanation_o TEXT,                   -- "왜 O" 코멘트
    explanation_x TEXT,                   -- "왜 X 아닌지" 코멘트
    meta_quality INTEGER NOT NULL DEFAULT 0,  -- 0~100 점수
    source_pdf TEXT,                      -- 원본 PDF 파일명 (저작권 표시)
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE (category_id, source_qid, source_option)
);

CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category_id);
CREATE INDEX IF NOT EXISTS idx_questions_answer   ON questions(category_id, answer);
CREATE INDEX IF NOT EXISTS idx_questions_topic    ON questions(topic);

-- v2 신규 테이블 (exam-ox-pipeline) -------------------------------------
CREATE TABLE IF NOT EXISTS related_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    youtube_id TEXT NOT NULL,
    title TEXT,
    channel TEXT,
    timestamp_start INTEGER,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_by TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS curriculum_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    chapter TEXT NOT NULL,
    source_book TEXT,
    source_url TEXT,
    notes TEXT,
    UNIQUE (subject, chapter)
);

CREATE INDEX IF NOT EXISTS idx_videos_qid ON related_videos(question_id);
"""


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def upsert_category(conn, meta: dict) -> int:
    """meta 키: slug, name, subject?, phase?, exam_group?, source?, exam_year?, exam_round?, is_default?, display_order?"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO categories
           (slug, name, exam_group, subject, phase, source, exam_year, exam_round, is_default, display_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug) DO UPDATE SET
               name=excluded.name,
               exam_group=excluded.exam_group,
               subject=excluded.subject,
               phase=excluded.phase,
               source=excluded.source,
               exam_year=excluded.exam_year,
               exam_round=excluded.exam_round,
               is_default=excluded.is_default,
               display_order=excluded.display_order""",
        (
            meta["slug"], meta["name"],
            meta.get("exam_group"), meta.get("subject"), meta.get("phase"),
            meta.get("source"), meta.get("exam_year"), meta.get("exam_round"),
            1 if meta.get("is_default") else 0,
            meta.get("display_order", 100),
        ),
    )
    cur.execute("SELECT id FROM categories WHERE slug = ?", (meta["slug"],))
    return cur.fetchone()[0]


def insert_questions(conn, category_id: int, ox_items: list, qtype: str, source_pdf: str = None):
    """v2: source_pdf 컬럼 저작권 표시용 적재. 메타 컬럼(tags/topic/theory/explanation_o/_x)은
    NULL로 들어가고 추후 extract_metadata.py 또는 enrich_session.py가 채움."""
    cur = conn.cursor()
    for ox in ox_items:
        cur.execute(
            """INSERT OR REPLACE INTO questions
               (category_id, statement, answer, source_qid, source_option, qtype, source_pdf)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (category_id, ox.statement, ox.answer, ox.source_qid, ox.source_option, qtype, source_pdf),
        )


def update_total_counts(conn):
    conn.execute(
        """UPDATE categories
           SET total_count = (
               SELECT COUNT(*) FROM questions WHERE category_id = categories.id
           )"""
    )


# ── Seed CSV 임포터 ──────────────────────────────────────────────────────
def import_seed_csv(conn, meta: dict) -> int:
    """data/seeds/{csv} → DB 적재. CSV 헤더: id,statement,answer,explanation,topic"""
    import csv
    csv_path = SEEDS_DIR / meta["csv"]
    if not csv_path.exists():
        print(f"⚠ seed CSV not found: {csv_path}")
        return 0
    category_id = upsert_category(conn, meta)
    cur = conn.cursor()
    count = 0
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stmt = (row.get("statement") or "").strip()
            ans = (row.get("answer") or "").strip().upper()
            if not stmt or ans not in ("O", "X"):
                continue
            cur.execute(
                """INSERT OR REPLACE INTO questions
                   (category_id, statement, answer, explanation, source_qid, source_option, qtype, difficulty)
                   VALUES (?, ?, ?, ?, ?, ?, 'seed', ?)""",
                (
                    category_id,
                    stmt,
                    ans,
                    (row.get("explanation") or "").strip() or None,
                    int(row.get("id") or 0) or None,
                    None,
                    (row.get("topic") or "").strip() or None,
                ),
            )
            count += 1
    return count


# ── 메인 파이프라인 ───────────────────────────────────────────────────────
def main():
    print(f"[build_quiz_db] PDF dir: {PDF_DIR}")
    print(f"[build_quiz_db] DB path: {DB_PATH}")

    if not PDF_DIR.exists():
        print(f"❌ {PDF_DIR} 없음", file=sys.stderr)
        return 1

    # PDF 텍스트 캐시 준비 (key는 NFC 정규화된 파일명)
    text_cache = {}
    for pdf in PDF_DIR.glob("*.pdf"):
        txt_path = TMP_DIR / (pdf.stem + ".txt")
        text_cache[nfc(pdf.name)] = pdf_to_text(pdf, txt_path)
    print(f"[build_quiz_db] {len(text_cache)} PDFs extracted")

    # 가답안 파싱
    answers = parse_answer_key(text_cache[nfc("가답안.pdf")])
    print(f"[build_quiz_db] answer key: {len(answers)} entries")
    # 과목별 정답 개수
    subjects_in_key = {}
    for (subj, qid), ans in answers.items():
        subjects_in_key.setdefault(subj, 0)
        subjects_in_key[subj] += 1
    for subj, count in subjects_in_key.items():
        print(f"  - {subj}: {count}개")

    # DB 초기화
    if DB_PATH.exists():
        DB_PATH.unlink()  # 매번 새로 빌드 (idempotent)
    conn = init_db(DB_PATH)

    # Seed 카테고리 먼저 (display_order 우선)
    summary = []
    for meta in SEED_CATEGORIES:
        n = import_seed_csv(conn, meta)
        summary.append({"subject": meta["name"], "ox_total": n, "type_stats": {"seed": n}, "skipped": 0})
        print(f"[seed] {meta['name']}: {n}건 적재")

    # 과목별 처리
    for meta in SUBJECT_MAP:
        pdf_text = text_cache.get(nfc(meta["pdf"]))
        if not pdf_text:
            print(f"⚠ {meta['name']} PDF 없음: {meta['pdf']}")
            continue
        # 시험지에서 해당 범위 문제 파싱
        questions = parse_exam_text(pdf_text, (meta["qid_start"], meta["qid_end"]))
        # 카테고리 메타데이터 보강
        cat_meta = {
            **meta,
            "exam_group": EXAM_GROUP_TAX,
            "source": EXAM_SOURCE,
            "exam_year": EXAM_YEAR,
            "exam_round": EXAM_ROUND,
            "is_default": False,
        }
        # OX 변환
        category_id = upsert_category(conn, cat_meta)
        ox_total = 0
        type_stats = {}
        skipped = 0
        for qid in range(meta["qid_start"], meta["qid_end"] + 1):
            q = questions.get(qid)
            if not q:
                skipped += 1
                continue
            ans = answers.get((meta["name"], qid))
            if ans is None:
                skipped += 1
                continue
            if q.qtype == "unknown":
                skipped += 1
                continue
            ox_items = convert_to_ox(q, ans)
            if not ox_items:
                skipped += 1
                continue
            insert_questions(conn, category_id, ox_items, q.qtype, source_pdf=meta["pdf"])
            ox_total += len(ox_items)
            type_stats[q.qtype] = type_stats.get(q.qtype, 0) + 1
        summary.append({
            "subject": meta["name"],
            "ox_total": ox_total,
            "type_stats": type_stats,
            "skipped": skipped,
        })

    update_total_counts(conn)
    conn.commit()

    # 요약 출력
    print("\n" + "=" * 60)
    print("[build_quiz_db] 완료. 과목별 OX 문제 수:")
    print("=" * 60)
    for s in summary:
        types_str = ", ".join(f"{k}={v}" for k, v in s["type_stats"].items())
        print(f"  {s['subject']:>10} : {s['ox_total']:>4}건  [skip {s['skipped']:>2}]  ({types_str})")
    grand_total = sum(s["ox_total"] for s in summary)
    print(f"\n  {'TOTAL':>10} : {grand_total:>4}건")

    # 샘플 확인
    print("\n=== 샘플 (각 과목 첫 OX 1건) ===")
    cur = conn.cursor()
    for cat in cur.execute("SELECT id, slug, name, total_count FROM categories ORDER BY id"):
        cur2 = conn.cursor()
        row = cur2.execute(
            "SELECT statement, answer, source_qid, source_option FROM questions WHERE category_id = ? ORDER BY id LIMIT 1",
            (cat[0],)
        ).fetchone()
        if row:
            print(f"\n[{cat[2]} · {cat[3]}건]")
            print(f"  Q.{row[2]} ({row[3]}): {row[0][:100]}{'...' if len(row[0]) > 100 else ''}")
            print(f"  Answer: {row[1]}")

    conn.close()
    print(f"\n✓ DB built at: {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
