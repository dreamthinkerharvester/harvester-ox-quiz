#!/usr/bin/env python3
"""
세션 보강 IO — 외부 LLM API 없이 Claude Code 세션(Opus)에서 메타데이터 보강.

워크플로우:
  1. export: meta_quality < threshold 행을 골라 마크다운 파일 생성
  2. (사용자) Claude Code 세션에서 마크다운 열고 @path 첨부 → 메타 채우기 요청
  3. import: 수정된 마크다운에서 메타 파싱 → DB UPDATE

사용법:
  python3 scripts/enrich_session.py export --limit 30 --threshold 80
                                   [--category SLUG] [--out PATH]
  python3 scripts/enrich_session.py import data/_session/2026-05-14_enrich.md
                                   [--dry-run]

마크다운 포맷 (블록 단위):
  ## Q{id} [{slug}] — {subject} / {qtype}
  **Statement**: ...
  **Answer**: O|X
  **PDF Explanation**: ...
  **Current Topic**: ...
  **Current Tags**: ...

  ### Metadata (please fill)
  - **Topic**:
  - **Tags**:
  - **Theory**:
  - **Explanation O**:
  - **Explanation X**:

  ---
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "quiz.db"
SESSION_DIR = PROJECT_ROOT / "data" / "_session"
DICT_DIR = PROJECT_ROOT / "data" / "dict"

META_WEIGHTS = {
    "topic": 25,
    "tags": 20,
    "theory": 15,
    "explanation_o": 20,
    "explanation_x": 20,
}


def compute_meta_quality(topic, tags, theory, ex_o, ex_x) -> int:
    score = 0
    if topic and str(topic).strip():
        score += META_WEIGHTS["topic"]
    if tags and (isinstance(tags, list) and tags or isinstance(tags, str) and tags.strip()):
        score += META_WEIGHTS["tags"]
    if theory and str(theory).strip():
        score += META_WEIGHTS["theory"]
    if ex_o and str(ex_o).strip():
        score += META_WEIGHTS["explanation_o"]
    if ex_x and str(ex_x).strip():
        score += META_WEIGHTS["explanation_x"]
    return score


def load_subject_dict_keywords(subject: str) -> list:
    """theory_hint 제공용 — 매칭된 키워드의 theory_hint를 마크다운에 노출."""
    name_map = {"경제학": "economics.json", "재정학": "finance.json"}
    fname = name_map.get(subject)
    if not fname:
        return []
    path = DICT_DIR / fname
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("keywords", [])


def find_theory_hints(statement: str, keywords: list) -> list:
    hints = []
    if not statement:
        return hints
    stmt_norm = re.sub(r"\s+", "", statement.lower())
    for kw in keywords:
        if not kw.get("theory_hint"):
            continue
        candidates = [kw["term"]] + kw.get("aliases", [])
        for cand in candidates:
            if not cand:
                continue
            if re.sub(r"\s+", "", cand.lower()) in stmt_norm:
                hints.append(f"{kw['term']}: {kw['theory_hint']}")
                break
    return hints[:3]


# ── Export ───────────────────────────────────────────────────────────────
def cmd_export(args):
    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where = ["q.meta_quality < ?"]
    params = [args.threshold]
    if args.category:
        where.append("c.slug = ?")
        params.append(args.category)
    if args.subject:
        where.append("c.subject = ?")
        params.append(args.subject)

    sql = f"""SELECT q.id AS qid, q.statement, q.answer, q.explanation AS pdf_expl,
                     q.qtype, q.topic, q.tags, q.theory,
                     q.explanation_o, q.explanation_x, q.meta_quality,
                     q.source_pdf,
                     c.slug, c.name AS cat_name, c.subject
              FROM questions q JOIN categories c ON q.category_id = c.id
              WHERE {' AND '.join(where)}
              ORDER BY q.meta_quality, c.id, q.id
              LIMIT {int(args.limit)}"""
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("처리 대상 0건 (모두 meta_quality >= threshold)")
        return 0

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else SESSION_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_enrich.md"

    # 카테고리별 사전 캐시
    dict_cache = {}
    for r in rows:
        if r["subject"] not in dict_cache:
            dict_cache[r["subject"]] = load_subject_dict_keywords(r["subject"])

    lines = []
    lines.append(f"# Enrich Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"> 총 {len(rows)}건 (meta_quality < {args.threshold}).")
    lines.append("> 작성법: 각 Q 블록 `### Metadata (please fill)` 아래 항목을 채우세요.")
    lines.append("> 비워두면 미적용. 채운 행만 import 됩니다.")
    lines.append("> Current 값은 유지하려면 비워두세요. 새 값 입력 시 덮어쓰기.")
    lines.append("> Tags는 CSV 또는 줄당 1개 (- 접두사). 5개 이하 권장.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in rows:
        cur_tags = []
        if r["tags"]:
            try:
                cur_tags = json.loads(r["tags"])
                if not isinstance(cur_tags, list):
                    cur_tags = []
            except (json.JSONDecodeError, TypeError):
                cur_tags = []
        cur_tags_csv = ", ".join(cur_tags) if cur_tags else ""

        hints = find_theory_hints(r["statement"], dict_cache[r["subject"]])

        lines.append(f"## Q{r['qid']} [{r['slug']}] — {r['cat_name']} ({r['qtype'] or '-'})")
        lines.append("")
        lines.append(f"**Statement**: {r['statement']}")
        lines.append(f"**Answer**: {r['answer']}")
        if r["pdf_expl"] and r["pdf_expl"].strip():
            lines.append(f"**PDF Explanation**: {r['pdf_expl']}")
        if r["topic"]:
            lines.append(f"**Current Topic**: {r['topic']}")
        if cur_tags_csv:
            lines.append(f"**Current Tags**: {cur_tags_csv}")
        if r["theory"]:
            lines.append(f"**Current Theory**: {r['theory']}")
        if r["explanation_o"]:
            lines.append(f"**Current Explanation O**: {r['explanation_o']}")
        if r["explanation_x"]:
            lines.append(f"**Current Explanation X**: {r['explanation_x']}")
        lines.append(f"**Source PDF**: {r['source_pdf'] or '(시드)'}")
        lines.append(f"**meta_quality**: {r['meta_quality']} / 100")
        if hints:
            lines.append("")
            lines.append("> 참고 (사전 hint):")
            for h in hints:
                lines.append(f"> - {h}")
        lines.append("")
        lines.append("### Metadata (please fill)")
        lines.append("")
        lines.append("- **Topic**: ")
        lines.append("- **Tags**: ")
        lines.append("- **Theory**: ")
        lines.append("- **Explanation O**: ")
        lines.append("- **Explanation X**: ")
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    # gitignore 보강
    gi = PROJECT_ROOT / ".gitignore"
    if gi.exists():
        gi_text = gi.read_text(encoding="utf-8")
        if "data/_session/" not in gi_text:
            gi.write_text(gi_text.rstrip() + "\n# enrich session work files\ndata/_session/\n", encoding="utf-8")
            print("  + .gitignore 에 data/_session/ 추가")

    print(f"✓ {len(rows)}건 export → {out_path}")
    print("")
    print("다음 단계:")
    print("  1. 위 파일을 Claude Code 세션에서 열어 메타를 채워주세요.")
    print("  2. 채운 후 import 명령:")
    try:
        rel = out_path.relative_to(PROJECT_ROOT)
        print(f"     python3 scripts/enrich_session.py import {rel}")
    except ValueError:
        print(f"     python3 scripts/enrich_session.py import {out_path}")
    return 0


# ── Import ───────────────────────────────────────────────────────────────
QID_HEADER_RE = re.compile(r"^## Q(\d+) \[([^\]]+)\]")
FIELD_RE = re.compile(r"^- \*\*(Topic|Tags|Theory|Explanation O|Explanation X)\*\*\s*:\s*(.*)$")


def parse_markdown(text: str) -> list:
    """마크다운 → [{qid, topic, tags, theory, explanation_o, explanation_x}, ...]"""
    blocks = []
    current = None
    in_meta_section = False

    for raw in text.splitlines():
        line = raw.rstrip()
        m = QID_HEADER_RE.match(line)
        if m:
            if current and any(current.get(k) for k in ("topic", "tags", "theory", "explanation_o", "explanation_x")):
                blocks.append(current)
            current = {
                "qid": int(m.group(1)),
                "slug": m.group(2),
                "topic": None, "tags": None,
                "theory": None, "explanation_o": None, "explanation_x": None,
            }
            in_meta_section = False
            continue

        if current is None:
            continue

        if "### Metadata" in line:
            in_meta_section = True
            continue

        if not in_meta_section:
            continue

        fm = FIELD_RE.match(line)
        if not fm:
            continue
        key = fm.group(1)
        val = fm.group(2).strip()
        if not val:
            continue

        if key == "Topic":
            current["topic"] = val
        elif key == "Tags":
            # CSV or "- tag" 형태
            tags = [t.strip() for t in re.split(r"[,，]", val) if t.strip()]
            current["tags"] = tags[:5] if tags else None
        elif key == "Theory":
            current["theory"] = val
        elif key == "Explanation O":
            current["explanation_o"] = val
        elif key == "Explanation X":
            current["explanation_x"] = val

    if current and any(current.get(k) for k in ("topic", "tags", "theory", "explanation_o", "explanation_x")):
        blocks.append(current)

    return blocks


def cmd_import(args):
    md_path = Path(args.file)
    if not md_path.exists():
        print(f"❌ 파일 없음: {md_path}", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음", file=sys.stderr)
        return 1

    text = md_path.read_text(encoding="utf-8")
    blocks = parse_markdown(text)
    if not blocks:
        print("⚠ 채워진 메타 0건 — 모든 항목이 빈 상태입니다.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    stats = {"total": len(blocks), "updated": 0, "skipped": 0,
             "topic": 0, "tags": 0, "theory": 0, "ex_o": 0, "ex_x": 0,
             "answer_validations": {"o_only": 0, "x_only": 0, "both": 0, "neither": 0}}

    for b in blocks:
        row = cur.execute(
            """SELECT q.id, q.answer, q.topic, q.tags, q.theory,
                      q.explanation_o, q.explanation_x
               FROM questions q WHERE q.id = ?""",
            (b["qid"],),
        ).fetchone()
        if not row:
            stats["skipped"] += 1
            continue

        # 기존 값 우선 유지 (Topic, Tags는 비어있을 때만 신규 채택, 나머지는 항상 덮어쓰기 — 사용자가 명시 작성)
        new_topic = b["topic"] if b["topic"] else row["topic"]
        new_tags_json = row["tags"]
        if b["tags"]:
            new_tags_json = json.dumps(b["tags"], ensure_ascii=False)
        new_theory = b["theory"] if b["theory"] else row["theory"]
        new_ex_o = b["explanation_o"] if b["explanation_o"] else row["explanation_o"]
        new_ex_x = b["explanation_x"] if b["explanation_x"] else row["explanation_x"]

        # 정답 검증 (있으면 좋음, 없어도 OK)
        has_o = bool(new_ex_o)
        has_x = bool(new_ex_x)
        if has_o and has_x:
            stats["answer_validations"]["both"] += 1
        elif has_o:
            stats["answer_validations"]["o_only"] += 1
        elif has_x:
            stats["answer_validations"]["x_only"] += 1
        else:
            stats["answer_validations"]["neither"] += 1

        # tags JSON list 형태 확보 (점수 계산용)
        tags_list = []
        if new_tags_json:
            try:
                tags_list = json.loads(new_tags_json)
            except (json.JSONDecodeError, TypeError):
                tags_list = []

        new_quality = compute_meta_quality(new_topic, tags_list, new_theory, new_ex_o, new_ex_x)

        # 변경 사항 통계
        if b["topic"]:
            stats["topic"] += 1
        if b["tags"]:
            stats["tags"] += 1
        if b["theory"]:
            stats["theory"] += 1
        if b["explanation_o"]:
            stats["ex_o"] += 1
        if b["explanation_x"]:
            stats["ex_x"] += 1

        if not args.dry_run:
            cur.execute(
                """UPDATE questions
                   SET topic = ?, tags = ?, theory = ?,
                       explanation_o = ?, explanation_x = ?, meta_quality = ?
                   WHERE id = ?""",
                (new_topic, new_tags_json, new_theory, new_ex_o, new_ex_x, new_quality, b["qid"]),
            )
            stats["updated"] += 1

    if not args.dry_run:
        conn.commit()

    print("=" * 60)
    print(f"세션 보강 import {'(DRY RUN)' if args.dry_run else '완료'}")
    print("=" * 60)
    print(f"  마크다운       : {md_path}")
    print(f"  파싱 블록      : {stats['total']}건")
    print(f"  DB 업데이트    : {stats['updated']}건")
    print(f"  스킵           : {stats['skipped']}건")
    print()
    print(f"  필드 채움      :")
    print(f"    topic        : {stats['topic']}")
    print(f"    tags         : {stats['tags']}")
    print(f"    theory       : {stats['theory']}")
    print(f"    explanation_o: {stats['ex_o']}")
    print(f"    explanation_x: {stats['ex_x']}")
    print()
    print(f"  Explanation 분포:")
    av = stats["answer_validations"]
    print(f"    O+X 둘 다     : {av['both']}")
    print(f"    O만           : {av['o_only']}")
    print(f"    X만           : {av['x_only']}")
    print(f"    둘 다 없음    : {av['neither']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="세션 보강 IO (Claude Code Opus용)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export", help="빈 메타 → 마크다운 export")
    e.add_argument("--limit", type=int, default=30)
    e.add_argument("--threshold", type=int, default=80, help="meta_quality 임계 (이 미만만 export)")
    e.add_argument("--category", help="카테고리 slug")
    e.add_argument("--subject", help="과목명 (e.g. 재정학)")
    e.add_argument("--out", help="출력 경로 (기본: data/_session/{datetime}_enrich.md)")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import", help="마크다운 → DB UPDATE")
    i.add_argument("file", help="마크다운 경로")
    i.add_argument("--dry-run", action="store_true")
    i.set_defaults(func=cmd_import)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
