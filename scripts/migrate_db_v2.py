#!/usr/bin/env python3
"""
data/quiz.db v1 → v2 마이그레이션 (idempotent).

v2 추가 항목:
  questions 테이블 신규 컬럼 7개:
    - tags TEXT             — JSON array string
    - topic TEXT            — 출제범위 (e.g. "재정학 §3.2 외부효과")
    - theory TEXT           — 1-line 관련이론
    - explanation_o TEXT    — "왜 O인지" 코멘트
    - explanation_x TEXT    — "왜 X가 아닌지" 코멘트
    - meta_quality INTEGER  — 0~100 메타 완성도 점수
    - source_pdf TEXT       — 원본 PDF 파일명 (저작권 표시)

  신규 테이블:
    - related_videos        — YouTube 슬롯 (MVP는 비어있음)
    - curriculum_map        — 교과서·교과과정 매핑

사용법:
    python3 scripts/migrate_db_v2.py [--db PATH] [--dry-run]

build_quiz_db.py는 매번 DB를 unlink·재생성하므로 v2 스키마를 직접 포함.
이 스크립트는 기존 v1 DB를 보존하면서 v2로 끌어올릴 때만 필요.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "quiz.db"

V2_COLUMNS = [
    ("tags",           "TEXT"),
    ("topic",          "TEXT"),
    ("theory",         "TEXT"),
    ("explanation_o",  "TEXT"),
    ("explanation_x",  "TEXT"),
    ("meta_quality",   "INTEGER NOT NULL DEFAULT 0"),
    ("source_pdf",     "TEXT"),
]

V2_TABLES_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic);
CREATE INDEX IF NOT EXISTS idx_videos_qid ON related_videos(question_id);
"""


def existing_columns(conn, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def existing_tables(conn) -> set:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def migrate(db_path: Path, dry_run: bool = False) -> int:
    if not db_path.exists():
        print(f"❌ DB 없음: {db_path}", file=sys.stderr)
        print("   build_quiz_db.py를 먼저 실행하세요.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    try:
        tables = existing_tables(conn)
        if "questions" not in tables:
            print(f"❌ questions 테이블 없음 — quiz.db가 손상되었거나 v0", file=sys.stderr)
            return 2

        before_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        cols = existing_columns(conn, "questions")

        # questions 컬럼 추가
        added_cols = []
        for col_name, col_def in V2_COLUMNS:
            if col_name in cols:
                continue
            if dry_run:
                added_cols.append(col_name)
                continue
            conn.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_def}")
            added_cols.append(col_name)

        # 신규 테이블·인덱스
        new_tables = []
        for t in ("related_videos", "curriculum_map"):
            if t not in tables:
                new_tables.append(t)
        if not dry_run:
            conn.executescript(V2_TABLES_SQL)
            conn.commit()

        after_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]

        print("=" * 60)
        print(f"DB v2 마이그레이션 {'(DRY RUN)' if dry_run else '완료'}")
        print("=" * 60)
        print(f"  DB         : {db_path}")
        print(f"  questions  : {before_count}건 → {after_count}건 (무손실 검증)")
        print(f"  추가 컬럼  : {added_cols if added_cols else '없음 (이미 v2)'}")
        print(f"  신규 테이블: {new_tables if new_tables else '없음 (이미 v2)'}")

        # v2 확인 검증
        new_cols = existing_columns(conn, "questions")
        missing = [c for c, _ in V2_COLUMNS if c not in new_cols]
        if missing and not dry_run:
            print(f"  ⚠ 누락 컬럼: {missing}", file=sys.stderr)
            return 3
        new_tables_after = existing_tables(conn)
        if not dry_run:
            if "related_videos" not in new_tables_after or "curriculum_map" not in new_tables_after:
                print(f"  ⚠ 누락 테이블", file=sys.stderr)
                return 4

        print(f"\n✓ v2 스키마 적용 완료")
        return 0
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="quiz.db v1→v2 마이그레이션")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true", help="실제 ALTER 없이 점검만")
    args = ap.parse_args()
    return migrate(args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
