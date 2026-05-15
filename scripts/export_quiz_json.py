#!/usr/bin/env python3
"""
SQLite quiz.db → 런타임 JSON 파일들로 export.

기본 (nonsense-quiz-mvp 호환):
    data/quiz/_index.json       — 카테고리 메타 (인트로 selector)
    data/quiz/{slug}.json       — 카테고리별 OX 문제 배열

--exam 옵션 (exam-ox-pipeline 학습 페이지):
    data/exam/_index.json       — 자격증>회차>과목 트리 메타
    data/exam/{slug}.json       — v2 메타 포함 (topic·tags·theory·explanation_o/x)

사용법:
    python3 scripts/export_quiz_json.py            # 기존 (data/quiz/)
    python3 scripts/export_quiz_json.py --exam     # v2 학습 페이지 (data/exam/)
    python3 scripts/export_quiz_json.py --both     # 둘 다
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
OUT_DIR = PROJECT_ROOT / "data" / "quiz"
EXAM_OUT_DIR = PROJECT_ROOT / "data" / "exam"


def export_default(conn) -> int:
    """기존 동작 — data/quiz/*.json (nonsense-quiz-mvp 호환)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cats = conn.execute(
        """SELECT id, slug, name, exam_group, subject, phase,
                  source, exam_year, exam_round,
                  is_default, display_order, total_count
           FROM categories
           WHERE total_count > 0
           ORDER BY display_order, id"""
    ).fetchall()

    index = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "default_slug": None,
        "categories": [],
    }

    for c in cats:
        cat_meta = {
            "slug": c["slug"],
            "name": c["name"],
            "exam_group": c["exam_group"],
            "subject": c["subject"],
            "phase": c["phase"],
            "source": c["source"],
            "exam_year": c["exam_year"],
            "exam_round": c["exam_round"],
            "is_default": bool(c["is_default"]),
            "display_order": c["display_order"],
            "count": c["total_count"],
        }
        if c["is_default"]:
            index["default_slug"] = c["slug"]
        index["categories"].append(cat_meta)

        rows = conn.execute(
            """SELECT id, statement, answer, explanation,
                      source_qid, source_option, qtype, difficulty
               FROM questions WHERE category_id = ? ORDER BY id""",
            (c["id"],),
        ).fetchall()
        questions = [
            {
                "id": r["id"],
                "question": r["statement"],
                "answer": r["answer"],
                "explanation": r["explanation"] or "",
                "source": {
                    "qid": r["source_qid"],
                    "option": r["source_option"],
                    "qtype": r["qtype"],
                    "difficulty": r["difficulty"],
                },
            }
            for r in rows
        ]
        cat_data = {
            "slug": c["slug"],
            "name": c["name"],
            "exam_group": c["exam_group"],
            "subject": c["subject"],
            "phase": c["phase"],
            "source": c["source"],
            "exam_year": c["exam_year"],
            "exam_round": c["exam_round"],
            "count": len(questions),
            "questions": questions,
        }
        out_path = OUT_DIR / f"{c['slug']}.json"
        out_path.write_text(json.dumps(cat_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {c['slug']}.json — {len(questions)}건")

    if index["default_slug"] is None and index["categories"]:
        index["default_slug"] = index["categories"][0]["slug"]

    index_path = OUT_DIR / "_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  ✓ _index.json — {len(cats)} categories, default = '{index['default_slug']}'")
    print(f"  ✓ Exported to: {OUT_DIR}")
    return 0


def detect_exam_label(cat) -> str:
    """카테고리 slug/source/exam_group 에서 자격증 라벨 추출.
    예: slug='tax-2026-r63-economics' → '세무사'
        source='세무사 1차' → '세무사'
    """
    src = (cat["source"] or "").strip()
    slug = (cat["slug"] or "").strip()
    if "세무사" in src or slug.startswith("tax-"):
        return "세무사"
    if "회계사" in src or slug.startswith("cpa-") or slug.startswith("acc-"):
        return "회계사"
    if "감정평가" in src or slug.startswith("appraiser-"):
        return "감정평가사"
    if "공무원" in src or slug.startswith("g9-") or slug.startswith("g7-") or slug.startswith("g5-"):
        return "공무원"
    if "한능검" in src or "한국사능력" in src:
        return "한국사능력검정"
    return src or "기타"


def export_exam(conn) -> int:
    """v2 학습 페이지용 — data/exam/*.json + _index.json (Design §3.3 schema)."""
    EXAM_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 메타 컬럼 존재 확인 (v2 마이그레이션 안 된 DB 보호)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    required = ("topic", "tags", "theory", "explanation_o", "explanation_x", "meta_quality", "source_pdf", "star_rating", "frequency")
    missing = [c for c in required if c not in cols]
    if missing:
        print(f"⚠ v2 메타 컬럼 누락: {missing}", file=sys.stderr)
        print("   → python3 scripts/migrate_db_v2.py 실행", file=sys.stderr)
        return 1

    # 시드(general-knowledge 같은 단독 카테고리)는 exam 트리에서 제외 — 자격증 트리 위주
    cats = conn.execute(
        """SELECT id, slug, name, exam_group, subject, phase,
                  source, exam_year, exam_round,
                  is_default, display_order, total_count
           FROM categories
           WHERE total_count > 0 AND exam_group IS NOT NULL
           ORDER BY exam_year DESC, exam_round DESC, display_order, id"""
    ).fetchall()

    tree = {}  # {exam_label: {(year, round): [cat_meta...]}}
    total_questions = 0
    total_with_full_meta = 0

    for c in cats:
        rows = conn.execute(
            """SELECT id, statement, answer, explanation,
                      source_qid, source_option, qtype, difficulty,
                      tags, topic, theory, explanation_o, explanation_x, meta_quality, source_pdf, star_rating, frequency
               FROM questions WHERE category_id = ? ORDER BY id""",
            (c["id"],),
        ).fetchall()

        # 카테고리별 영상 슬롯 일괄 fetch
        videos_by_qid = {}
        if "related_videos" in {r[1] for r in conn.execute("PRAGMA table_info(related_videos)").fetchall()} or True:
            # 안전: 테이블이 있다고 가정 (v2 마이그레이션 후)
            try:
                vrows = conn.execute(
                    """SELECT rv.question_id, rv.youtube_id, rv.title, rv.channel, rv.timestamp_start
                       FROM related_videos rv
                       JOIN questions q ON rv.question_id = q.id
                       WHERE q.category_id = ?""",
                    (c["id"],),
                ).fetchall()
                for v in vrows:
                    videos_by_qid.setdefault(v["question_id"], []).append({
                        "youtube_id": v["youtube_id"],
                        "title": v["title"],
                        "channel": v["channel"],
                        "timestamp_start": v["timestamp_start"],
                    })
            except sqlite3.OperationalError:
                pass

        questions = []
        with_full_meta = 0
        for r in rows:
            # tags JSON 파싱 (저장은 JSON string)
            tags_val = None
            if r["tags"]:
                try:
                    tags_val = json.loads(r["tags"])
                    if not isinstance(tags_val, list):
                        tags_val = None
                except (json.JSONDecodeError, TypeError):
                    tags_val = None
            meta_q = r["meta_quality"] or 0
            if meta_q >= 80:
                with_full_meta += 1
            questions.append({
                "id": r["id"],
                "statement": r["statement"],
                "answer": r["answer"],
                "explanation": r["explanation"] or "",
                "qtype": r["qtype"],
                "topic": r["topic"],
                "tags": tags_val,
                "theory": r["theory"],
                "explanation_o": r["explanation_o"],
                "explanation_x": r["explanation_x"],
                "meta_quality": meta_q,
                "star_rating": r["star_rating"] or 0,
                "frequency": r["frequency"] or 1,
                "source_pdf": r["source_pdf"],
                "source": {
                    "qid": r["source_qid"],
                    "option": r["source_option"],
                },
                "related_videos": videos_by_qid.get(r["id"], []),
            })

        cat_data = {
            "category": {
                "slug": c["slug"],
                "name": c["name"],
                "exam_group": c["exam_group"],
                "subject": c["subject"],
                "phase": c["phase"],
                "exam_year": c["exam_year"],
                "exam_round": c["exam_round"],
            },
            "questions": questions,
            "_meta": {
                "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "total": len(questions),
                "with_full_meta": with_full_meta,
                "source": "0gichul.com",
            },
        }
        out_path = EXAM_OUT_DIR / f"{c['slug']}.json"
        out_path.write_text(json.dumps(cat_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ exam/{c['slug']}.json — {len(questions)}건 (full meta {with_full_meta})")

        # 트리 적재
        exam_label = detect_exam_label(c)
        year = c["exam_year"]
        rnd = c["exam_round"]
        tree.setdefault(exam_label, {}).setdefault((year, rnd), []).append({
            "slug": c["slug"],
            "name": c["name"],
            "subject": c["subject"],
            "phase": c["phase"],
            "total": c["total_count"],
            "with_full_meta": with_full_meta,
        })
        total_questions += len(questions)
        total_with_full_meta += with_full_meta

    # 트리 JSON 변환
    tree_arr = []
    for exam_label, rounds_map in tree.items():
        rounds_arr = []
        for (year, rnd), cat_list in sorted(rounds_map.items(), key=lambda x: (-(x[0][0] or 0), -(x[0][1] or 0))):
            rounds_arr.append({
                "year": year,
                "round": rnd,
                "categories": cat_list,
            })
        tree_arr.append({
            "exam": exam_label,
            "rounds": rounds_arr,
        })

    index = {
        "tree": tree_arr,
        "_meta": {
            "total_questions": total_questions,
            "categories_count": len(cats),
            "with_full_meta": total_with_full_meta,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "0gichul.com",
        },
    }
    index_path = EXAM_OUT_DIR / "_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  ✓ exam/_index.json — {len(cats)} categories, {total_questions} questions, full meta {total_with_full_meta}")
    print(f"  ✓ Exported to: {EXAM_OUT_DIR}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="quiz.db → JSON export")
    ap.add_argument("--exam", action="store_true", help="v2 학습 페이지용 data/exam/ 만 export")
    ap.add_argument("--both", action="store_true", help="기존 + exam 둘 다")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음. 먼저 build_quiz_db.py 실행", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rc = 0
    if args.exam and not args.both:
        rc = export_exam(conn)
    elif args.both:
        rc = export_default(conn)
        if rc == 0:
            print()
            rc = export_exam(conn)
    else:
        rc = export_default(conn)

    conn.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
