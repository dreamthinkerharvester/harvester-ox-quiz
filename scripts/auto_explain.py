#!/usr/bin/env python3
"""
해설이 없는 OX 문항에 자동 해설 1~2문장 생성.

전략:
  - 같은 (category_id, source_qid) 그룹에서 정답 위치(answer='O' 또는 'X') 추출
  - qtype(opt-correct / opt-wrong / sub-all-correct / sub-all-wrong)에 따라
    "이 진술은 옳다 / 옳지 않다 + 정답은 N번" 형식의 자동 해설 작성
  - explanation 또는 explanation_o/explanation_x 모두 비어있는 경우만 채움
  - 원본 해설(PDF 추출본 등) 있으면 유지

사용법:
  python3 scripts/auto_explain.py            # 통계만
  python3 scripts/auto_explain.py --apply    # DB 갱신
  python3 scripts/auto_explain.py --overwrite-blank-only  # 기본 (블랭크만)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "quiz.db"

CIRCLED = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
SUB_LABELS = {"ㄱ": "ㄱ", "ㄴ": "ㄴ", "ㄷ": "ㄷ", "ㄹ": "ㄹ", "ㅁ": "ㅁ",
              "a": "a", "b": "b", "c": "c", "d": "d", "e": "e"}


def opt_label(source_option: str | None) -> str:
    """source_option → 표시용 라벨. ①②③ 같으면 그대로, 숫자면 _N → N번."""
    if not source_option:
        return ""
    s = source_option.strip()
    if s.startswith("_") and s[1:].isdigit():
        return f"{s[1:]}번"
    return s


def generate_explanation(answer: str, qtype: str | None,
                         group_info: dict,
                         self_option: str | None) -> str:
    """단일 OX 항목 자동 해설.

    group_info: {"O": [opt, ...], "X": [opt, ...], "qtype": str}
    """
    is_correct = answer == "O"
    base = "이 진술은 옳다." if is_correct else "이 진술은 옳지 않다."

    if qtype == "opt-correct":
        # "옳은 것은?" → 정답 = O 옵션 (보통 1개)
        ans_opts = group_info.get("O", [])
    elif qtype == "opt-wrong":
        # "옳지 않은 것은?" → 정답 = X 옵션 (보통 1개)
        ans_opts = group_info.get("X", [])
    elif qtype == "sub-all-correct":
        # "옳은 것을 모두 고른 것은?" → 정답 조합 = O 항목들
        ans_opts = group_info.get("O", [])
    elif qtype == "sub-all-wrong":
        # "옳지 않은 것을 모두 고른 것은?" → 정답 조합 = X 항목들
        ans_opts = group_info.get("X", [])
    else:
        return base

    ans_labels = [opt_label(o) for o in ans_opts if o]
    ans_str = ", ".join(filter(None, ans_labels))

    if not ans_str:
        return base

    if qtype in ("opt-correct", "opt-wrong"):
        # 본인이 정답인 경우 vs 아닌 경우
        if self_option in ans_opts:
            return f"{base} (이 문제의 정답)"
        # 본인은 오답, 정답은 다른 옵션
        if len(ans_opts) == 1:
            return f"{base} 같은 문제의 정답은 {ans_str}이다."
        return f"{base} 같은 문제의 정답은 {ans_str} 중 하나이다."

    # sub-all-*
    if self_option in ans_opts:
        return f"{base} 정답 조합({ans_str})에 포함되는 항목이다."
    return f"{base} 정답 조합({ans_str})에 포함되지 않는 항목이다."


def needs_fill(row) -> bool:
    """해설이 모두 비어있는 경우만 자동 생성 대상."""
    return not (row["explanation"] or "").strip() \
        and not (row["explanation_o"] or "").strip() \
        and not (row["explanation_x"] or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="DB 갱신")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ DB 없음: {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 정답 위치 집계: (category_id, source_qid) → {O: [...], X: [...], qtype: str}
    # opt-correct → 정답은 O 옵션 1개
    # opt-wrong → 정답은 X 옵션 1개 (이 문항이 "옳지 않은 것"이므로)
    # sub-all-correct → 정답 조합은 O 옵션들 (sub-items)
    # sub-all-wrong → 정답 조합은 X 옵션들 (sub-items)
    answer_map: dict[tuple, dict] = defaultdict(lambda: {"O": [], "X": [], "qtype": None})
    for r in conn.execute(
        "SELECT category_id, source_qid, source_option, answer, qtype "
        "FROM questions WHERE ox_valid=1 AND source_qid IS NOT NULL"
    ):
        if not r["source_option"]:
            continue
        key = (r["category_id"], r["source_qid"])
        answer_map[key][r["answer"]].append(r["source_option"])
        if r["qtype"]:
            answer_map[key]["qtype"] = r["qtype"]

    # 대상 행
    rows = conn.execute(
        """SELECT id, category_id, source_qid, source_option, answer, qtype,
                  explanation, explanation_o, explanation_x
           FROM questions WHERE ox_valid=1"""
    ).fetchall()

    filled = 0
    skipped_existing = 0
    skipped_invalid = 0
    samples: list = []
    updates: list[tuple[str, int]] = []

    for r in rows:
        if not needs_fill(r):
            skipped_existing += 1
            continue
        key = (r["category_id"], r["source_qid"])
        group_info = answer_map.get(key, {"O": [], "X": [], "qtype": None})
        expl = generate_explanation(r["answer"], r["qtype"], group_info, r["source_option"])
        if not expl:
            skipped_invalid += 1
            continue
        updates.append((expl, r["id"]))
        filled += 1
        if len(samples) < 8:
            samples.append((r["id"], r["answer"], r["source_option"], expl))

    print("=" * 70)
    print(f"자동 해설 생성 — 대상 {len(rows)}건")
    print("=" * 70)
    print(f"  생성: {filled}건")
    print(f"  기존 해설 유지: {skipped_existing}건")
    print(f"  생성 실패: {skipped_invalid}건")
    print(f"\n[샘플]")
    for qid, ans, opt, expl in samples:
        print(f"  #{qid} [{ans}, opt={opt}] → {expl}")

    if args.apply and updates:
        conn.executemany("UPDATE questions SET explanation=? WHERE id=?", updates)
        conn.commit()
        print(f"\n  ✓ DB 갱신: {len(updates)}건")
        print(f"  → JSON 재생성: python3 scripts/export_quiz_json.py --both")
    elif updates:
        print(f"\n💡 DB 갱신: python3 scripts/auto_explain.py --apply")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
