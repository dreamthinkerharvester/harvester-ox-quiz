#!/usr/bin/env python3
"""
Rule-based 메타데이터 추출 (data/quiz.db의 questions 행).

처리 단계:
  1. 카테고리 subject → data/dict/{subject}.json 매핑
  2. 각 빈 메타 행에 대해:
     a. 법조문 정규식 매칭 ("법 제N조", "§N") → topic 후보
     b. 키워드 사전 매칭 (term + aliases) → topic·tags 후보
     c. topic 최종 결정: 사전 매칭 우선, 없으면 정규식 매칭 결과
     d. tags 합집합 (max 5, 빈도순)
     e. meta_quality 점수 재계산
  3. DB UPDATE

사용법:
  python3 scripts/extract_metadata.py                          # 전체
  python3 scripts/extract_metadata.py --category tax-2026-r63-jaejeong
  python3 scripts/extract_metadata.py --subject 재정학
  python3 scripts/extract_metadata.py --dry-run                # 미적용
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
DICT_DIR = PROJECT_ROOT / "data" / "dict"

# 과목명 → 사전 파일 매핑
SUBJECT_DICT_MAP = {
    "경제학": "economics.json",
    "재정학": "finance.json",
    # 법학·회계학은 정규식 fallback 사용 (사전 부재 OK)
}

# 법조문 정규식 — "민법 제390조", "민법 §390", "행정소송법 제18조 제1항" 등
LAW_PAT = re.compile(
    r"(민법|상법|헌법|형법|행정소송법|행정심판법|행정절차법|국가공무원법|지방세법|국세기본법|소득세법|법인세법|부가가치세법|상속세법|증여세법)"
    r"\s*(제\s*(\d+)\s*조(?:\s*제\s*\d+\s*항)?|\§\s*(\d+))"
)

# 메타 점수 가중 (audit_quiz_quality.py와 일치)
META_WEIGHTS = {
    "topic": 25,
    "tags": 20,
    "theory": 15,
    "explanation_o": 20,
    "explanation_x": 20,
}


def load_dict(subject: str) -> list:
    fname = SUBJECT_DICT_MAP.get(subject)
    if not fname:
        return []
    path = DICT_DIR / fname
    if not path.exists():
        print(f"⚠ 사전 파일 없음: {path}", file=sys.stderr)
        return []
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("keywords", [])


def normalize(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


def match_keywords(statement: str, keywords: list) -> list:
    """statement 에 매칭되는 keyword 항목 리스트 반환 (term, topic, tags 포함)."""
    if not statement or not keywords:
        return []
    stmt_norm = normalize(statement)
    matched = []
    for kw in keywords:
        candidates = [kw["term"]] + kw.get("aliases", [])
        for cand in candidates:
            if not cand:
                continue
            if normalize(cand) in stmt_norm:
                matched.append(kw)
                break  # 같은 keyword 중복 매칭 방지
    return matched


def match_law_articles(statement: str) -> list:
    """법조문 매칭 → topic candidates 리스트."""
    if not statement:
        return []
    out = []
    for m in LAW_PAT.finditer(statement):
        law = m.group(1)
        article_num = m.group(3) or m.group(4)
        if article_num:
            out.append(f"{law} §{article_num}")
    return out


def derive_meta(statement: str, keywords: list) -> dict:
    """statement → {topic, tags, n_matches} dict.

    Rule-based 만으로는 theory·explanation_o/x 채울 수 없음 (LLM 세션 보강 필요).
    """
    matched_kws = match_keywords(statement, keywords)
    law_topics = match_law_articles(statement)

    # tags 합집합 (빈도 가중 max 5)
    tag_counter = Counter()
    for kw in matched_kws:
        for t in kw.get("tags", []):
            tag_counter[t] += 1
    tags = [t for t, _ in tag_counter.most_common(5)]

    # topic 결정 우선순위:
    #  (1) 법조문 매칭 있으면 그것 (최초 발견)
    #  (2) 사전 매칭 keyword 중 topic 가진 항목 (최초 발견)
    topic = None
    if law_topics:
        topic = law_topics[0]
    if not topic:
        for kw in matched_kws:
            if kw.get("topic"):
                topic = kw["topic"]
                break

    return {
        "topic": topic,
        "tags": tags,
        "n_kw_matches": len(matched_kws),
        "n_law_matches": len(law_topics),
    }


def compute_meta_quality(topic, tags, theory, explanation_o, explanation_x) -> int:
    score = 0
    if topic and str(topic).strip():
        score += META_WEIGHTS["topic"]
    if tags and (isinstance(tags, list) and tags or isinstance(tags, str) and tags.strip()):
        score += META_WEIGHTS["tags"]
    if theory and str(theory).strip():
        score += META_WEIGHTS["theory"]
    if explanation_o and str(explanation_o).strip():
        score += META_WEIGHTS["explanation_o"]
    if explanation_x and str(explanation_x).strip():
        score += META_WEIGHTS["explanation_x"]
    return score


def process_categories(conn, where_clauses: list, params: list, dry_run: bool = False) -> dict:
    """카테고리별로 처리 + 통계 반환."""
    # 메타 컬럼 존재 확인
    cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    if "tags" not in cols:
        print("⚠ v2 메타 컬럼 누락 — migrate_db_v2.py 먼저 실행", file=sys.stderr)
        return None

    base_q = """SELECT c.id AS cid, c.slug, c.name, c.subject,
                       q.id AS qid, q.statement, q.tags, q.topic,
                       q.theory, q.explanation_o, q.explanation_x
                FROM questions q JOIN categories c ON q.category_id = c.id"""
    if where_clauses:
        base_q += " WHERE " + " AND ".join(where_clauses)
    base_q += " ORDER BY c.id, q.id"

    rows = conn.execute(base_q, params).fetchall()
    if not rows:
        print("처리 대상 0건")
        return {"total": 0}

    # 카테고리별로 사전 로드 캐시
    dict_cache = {}
    stats = {"total": len(rows), "by_cat": {}, "updates": 0, "kw_matched": 0, "law_matched": 0}
    update_rows = []  # (qid, tags_json, topic, meta_quality)

    for r in rows:
        subject = r["subject"]
        if subject not in dict_cache:
            dict_cache[subject] = load_dict(subject)
        keywords = dict_cache[subject]

        meta = derive_meta(r["statement"], keywords)
        if meta["n_kw_matches"] > 0:
            stats["kw_matched"] += 1
        if meta["n_law_matches"] > 0:
            stats["law_matched"] += 1

        # 기존 채워진 메타는 보존 (rule-based로 덮어쓰지 않음)
        new_topic = r["topic"] or meta["topic"]
        existing_tags = []
        if r["tags"]:
            try:
                existing_tags = json.loads(r["tags"])
                if not isinstance(existing_tags, list):
                    existing_tags = []
            except (json.JSONDecodeError, TypeError):
                existing_tags = []
        # 신규 tags를 기존에 합치되 중복 제거 (순서 유지)
        seen_tags = set(existing_tags)
        merged_tags = list(existing_tags)
        for t in meta["tags"]:
            if t not in seen_tags:
                seen_tags.add(t)
                merged_tags.append(t)
        merged_tags = merged_tags[:5]
        new_tags_json = json.dumps(merged_tags, ensure_ascii=False) if merged_tags else None

        # meta_quality 재계산
        new_quality = compute_meta_quality(
            new_topic, merged_tags, r["theory"], r["explanation_o"], r["explanation_x"]
        )

        # 카테고리 통계
        cat_key = r["slug"]
        s = stats["by_cat"].setdefault(cat_key, {
            "name": r["name"], "total": 0, "topic_filled": 0, "tags_filled": 0
        })
        s["total"] += 1
        if new_topic:
            s["topic_filled"] += 1
        if merged_tags:
            s["tags_filled"] += 1

        # 변경된 행만 update 큐에 넣기 (효율)
        if (new_topic != r["topic"]) or (new_tags_json != r["tags"]) or True:
            update_rows.append((new_tags_json, new_topic, new_quality, r["qid"]))

    if not dry_run and update_rows:
        cur = conn.cursor()
        cur.executemany(
            "UPDATE questions SET tags = ?, topic = ?, meta_quality = ? WHERE id = ?",
            update_rows,
        )
        conn.commit()
        stats["updates"] = cur.rowcount

    return stats


def main():
    ap = argparse.ArgumentParser(description="Rule-based 메타데이터 추출 → quiz.db UPDATE")
    ap.add_argument("--category", help="카테고리 slug 한정 (예: tax-2026-r63-jaejeong)")
    ap.add_argument("--subject", help="과목명 한정 (예: 재정학)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where = []
    params = []
    if args.category:
        where.append("c.slug = ?")
        params.append(args.category)
    if args.subject:
        where.append("c.subject = ?")
        params.append(args.subject)

    stats = process_categories(conn, where, params, dry_run=args.dry_run)
    if stats is None:
        return 1

    print("=" * 70)
    print(f"메타데이터 추출 {'(DRY RUN)' if args.dry_run else '완료'}")
    print("=" * 70)
    print(f"  처리 대상     : {stats['total']}건")
    print(f"  키워드 매칭   : {stats['kw_matched']}건")
    print(f"  법조문 매칭   : {stats['law_matched']}건")
    print(f"  DB 업데이트   : {stats['updates']}건")
    print()
    print(f"  {'카테고리':>22}  {'total':>5}  {'topic':>5}  {'tags':>5}  {'topic%':>6}  {'tags%':>6}")
    for slug, s in stats["by_cat"].items():
        tp = 100 * s["topic_filled"] / s["total"] if s["total"] else 0
        tg = 100 * s["tags_filled"] / s["total"] if s["total"] else 0
        print(f"  {slug:>22}  {s['total']:>5}  {s['topic_filled']:>5}  {s['tags_filled']:>5}  {tp:>5.1f}%  {tg:>5.1f}%")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
