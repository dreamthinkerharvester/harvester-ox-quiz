#!/usr/bin/env python3
"""
data/quiz.db 의 OX 진술 품질 audit.

OX로 처리되기 어려운 패턴 휴리스틱:
  [F1] 너무 짧음 (<14자)             — 독립 OX 진술 불가
  [F2] 숫자/기호 비율 ≥45%           — bare value (계산 답변 옵션)
  [F3] 한국어 술어 부재               — "이다/한다/있다/없다" 등 종결 표현 없음
  [F4] 시작이 숫자/기호               — "₩100", "5명…" 단독값
  [F5] 비교용 multi-numeric ≥3       — 비율·서수 등
  [F6] 단일 단어 (공백 0)             — 용어 단독

verdict: REJECT (자동 제외 후보) / WARN (수동 검토) / OK
"""
import re
import sqlite3
import sys
from pathlib import Path
from collections import Counter

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "quiz.db"

KO_PRED_RE = re.compile(
    r"이다|아니다|다\.|있다|없다|한다|된다|같다|옳다|틀리다|"
    r"하는|되는|수\s*있|수\s*없|한\s*것|된\s*것|"
    r"이\s*아니|가\s*아니|하여야|되어야|하지\s*않|되지\s*않|이라\s*한"
)
NUM_UNIT_RE = re.compile(r"[₩\$￦]?[\d,]+(?:\.\d+)?\s*(?:[%‰원만억]|일|시간|년|월|개|명|회|조|점|배|등)?")
LEAD_NUM_RE = re.compile(r"^\s*(?:[₩\$￦]?\d|[①②③④⑤⑥⑦⑧⑨⑩]|\([0-9]\))")


def char_ratios(s: str):
    if not s:
        return 0.0, 0.0, 0.0, 0.0, 0
    han = sum(1 for c in s if "가" <= c <= "힣")
    dig = sum(1 for c in s if c.isdigit())
    alp = sum(1 for c in s if c.isascii() and c.isalpha())
    sym = sum(1 for c in s if not (c.isalnum() or c.isspace() or "가" <= c <= "힣"))
    L = len(s)
    return han / L, dig / L, alp / L, sym / L, L


def audit(stmt: str):
    """OX로 부적합한지 판단. 한국어는 매우 짧은 진술도 valid 가능 (예: "달은 스스로 빛을 낸다." 12자).
    실제 문제 패턴: 술어 부재(=용어 나열) + 숫자/기호 dominant + 단일 단어."""
    s = stmt.strip()
    flags = []
    if len(s) < 8:
        flags.append("F1_TOO_SHORT")           # 정말로 너무 짧음
    han, dig, alp, sym, L = char_ratios(s)
    if L > 0 and (dig + sym + alp) >= 0.5 and dig >= 0.2:
        flags.append("F2_HIGH_NON_KOREAN")     # 숫자·기호 50%+ AND 숫자 20%+
    if not KO_PRED_RE.search(s):
        flags.append("F3_NO_PREDICATE")        # 종결어미·서술 부재 (용어 나열형)
    if LEAD_NUM_RE.match(s) and L < 16:
        flags.append("F4_LEADS_NUMERIC_SHORT") # 숫자로 시작 + 짧음 (bare value 의심)
    nums = NUM_UNIT_RE.findall(s)
    if len(nums) >= 4 and dig >= 0.15:
        flags.append("F5_MANY_NUMERICS")       # 숫자 4개 이상 dominant (계산 결과)
    if " " not in s and len(s) < 12:
        flags.append("F6_SINGLE_WORD")         # 공백 0 + 짧음 = 단일 용어

    # Verdict — REJECT는 진짜 부적합만, WARN은 의심
    if "F6_SINGLE_WORD" in flags:
        verdict = "REJECT"
    elif "F1_TOO_SHORT" in flags:
        verdict = "REJECT"
    elif "F3_NO_PREDICATE" in flags and ("F2_HIGH_NON_KOREAN" in flags or "F4_LEADS_NUMERIC_SHORT" in flags or len(s) < 20):
        verdict = "REJECT"
    elif "F3_NO_PREDICATE" in flags:
        verdict = "WARN"
    elif "F2_HIGH_NON_KOREAN" in flags or "F5_MANY_NUMERICS" in flags:
        verdict = "WARN"
    else:
        verdict = "OK"
    return flags, verdict


META_FIELDS = ("topic", "tags", "theory", "explanation_o", "explanation_x")
META_FIELD_WEIGHTS = {
    "topic": 25,
    "tags": 20,
    "theory": 15,
    "explanation_o": 20,
    "explanation_x": 20,
}  # 합계 = 100


def compute_meta_quality(row) -> int:
    """0~100 점수 계산. 채워진 메타 필드의 가중합."""
    score = 0
    for f, w in META_FIELD_WEIGHTS.items():
        try:
            val = row[f]
        except (KeyError, IndexError):
            val = None
        if val and str(val).strip():
            score += w
    return score


def report_meta_coverage(conn):
    """v2 메타 완성도 분포 + 카테고리별 ≥80% 충족 여부 보고."""
    # 메타 컬럼 존재 확인 (v2 마이그레이션 안 된 DB 보호)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    missing = [c for c in META_FIELDS if c not in cols]
    if missing:
        print(f"⚠ v2 메타 컬럼 누락: {missing}", file=sys.stderr)
        print("   → python3 scripts/migrate_db_v2.py 실행 후 재시도", file=sys.stderr)
        return 1
    rows = conn.execute(
        """SELECT q.id, q.topic, q.tags, q.theory, q.explanation_o, q.explanation_x,
                  q.explanation AS pdf_explanation, c.name AS cat, c.slug
           FROM questions q JOIN categories c ON q.category_id=c.id
           ORDER BY c.id, q.id"""
    ).fetchall()
    if not rows:
        print("문항 0건", file=sys.stderr)
        return 0

    total = len(rows)
    field_filled = {f: 0 for f in META_FIELDS}
    field_filled["pdf_explanation"] = 0
    score_dist = {"0": 0, "1-39": 0, "40-79": 0, "80-100": 0}
    per_cat = {}
    score_sum = 0

    for r in rows:
        cat = r["cat"]
        per_cat.setdefault(cat, {"total": 0, "above_80": 0, "scores": []})
        s = compute_meta_quality(r)
        score_sum += s
        per_cat[cat]["total"] += 1
        per_cat[cat]["scores"].append(s)
        if s >= 80:
            per_cat[cat]["above_80"] += 1
        if s == 0:
            score_dist["0"] += 1
        elif s < 40:
            score_dist["1-39"] += 1
        elif s < 80:
            score_dist["40-79"] += 1
        else:
            score_dist["80-100"] += 1
        for f in META_FIELDS:
            if r[f] and str(r[f]).strip():
                field_filled[f] += 1
        if r["pdf_explanation"] and r["pdf_explanation"].strip():
            field_filled["pdf_explanation"] += 1

    print("=" * 70)
    print(f"v2 메타데이터 완성도 — 총 {total}건")
    print("=" * 70)
    print(f"\n[필드별 채움률]")
    for f in META_FIELDS + ("pdf_explanation",):
        n = field_filled[f]
        pct = 100 * n / total
        bar = "█" * int(pct / 5)
        print(f"  {f:>18} : {n:>5} ({pct:5.1f}%)  {bar}")

    print(f"\n[meta_quality 점수 분포]")
    for k, n in score_dist.items():
        pct = 100 * n / total
        print(f"  {k:>8} : {n:>5} ({pct:5.1f}%)")
    avg = score_sum / total if total else 0
    print(f"  {'avg':>8} : {avg:5.1f}")

    print(f"\n[카테고리별 ≥80% 충족]")
    print(f"  {'카테고리':>22}  {'total':>5}  {'≥80':>5}  {'pct':>5}  {'avg':>5}  {'pass?':>5}")
    overall_pass = True
    for cat, d in per_cat.items():
        pct = 100 * d["above_80"] / d["total"] if d["total"] else 0
        avg_cat = sum(d["scores"]) / d["total"] if d["total"] else 0
        passed = pct >= 80
        if not passed:
            overall_pass = False
        mark = "✓" if passed else "✗"
        print(f"  {cat:>22}  {d['total']:>5}  {d['above_80']:>5}  {pct:>4.1f}%  {avg_cat:>4.1f}  {mark:>5}")

    print()
    if overall_pass:
        print("✓ 모든 카테고리 메타 완성도 ≥80%")
        return 0
    else:
        print("⚠ 일부 카테고리 메타 완성도 < 80%")
        print("  → 보강: python3 scripts/enrich_session.py export --limit 50")
        return 0  # 경고일 뿐, exit code는 정상


def main():
    apply_reject = "--apply-reject" in sys.argv
    meta_coverage = "--meta-coverage" in sys.argv

    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if meta_coverage:
        return report_meta_coverage(conn)

    rows = conn.execute(
        """SELECT q.id, q.statement, q.answer, q.source_qid, q.source_option, c.name AS cat
           FROM questions q JOIN categories c ON q.category_id=c.id ORDER BY c.id, q.id"""
    ).fetchall()
    total = len(rows)
    by_v = Counter()
    by_f = Counter()
    by_cv = {}
    samples = {"REJECT": [], "WARN": []}
    reject_ids = []

    for r in rows:
        flags, v = audit(r["statement"])
        by_v[v] += 1
        for f in flags:
            by_f[f] += 1
        by_cv.setdefault(r["cat"], Counter())[v] += 1
        if v == "REJECT":
            reject_ids.append(r["id"])
        if v in samples and len(samples[v]) < 8:
            samples[v].append((r["cat"], r["source_qid"], r["source_option"], r["answer"], r["statement"], flags))

    print("=" * 70)
    print(f"OX 품질 Audit — 총 {total}건")
    print("=" * 70)
    print("\n[전체]")
    for v in ("OK", "WARN", "REJECT"):
        n = by_v[v]
        pct = 100 * n / total if total else 0
        print(f"  {v:>6}: {n:>4}건 ({pct:5.1f}%)")
    print("\n[Flag 빈도]")
    for f, n in by_f.most_common():
        print(f"  {f:<25} {n:>4}")
    print("\n[카테고리별]")
    print(f"  {'카테고리':>12}  {'OK':>4} {'WARN':>5} {'REJECT':>7}   OK%")
    for cat, c in by_cv.items():
        ok, w, rj = c.get("OK", 0), c.get("WARN", 0), c.get("REJECT", 0)
        t = ok + w + rj
        ok_pct = 100 * ok / t if t else 0
        print(f"  {cat:>12}  {ok:>4} {w:>5} {rj:>7}   {ok_pct:5.1f}%")

    for label in ("REJECT", "WARN"):
        print(f"\n[{label} 샘플 (최대 8건)]")
        for cat, qid, opt, ans, stmt, flags in samples[label]:
            preview = stmt if len(stmt) <= 100 else stmt[:97] + "..."
            print(f"  · [{cat}] Q.{qid} ({opt}) {ans}")
            print(f"    \"{preview}\"")
            print(f"    flags: {', '.join(flags)}")

    # --apply-reject: REJECT 항목 DB에서 삭제 + total_count 갱신 + JSON 재생성 안내
    if apply_reject and reject_ids:
        print(f"\n=== --apply-reject : {len(reject_ids)}건 삭제 ===")
        cur = conn.cursor()
        cur.executemany("DELETE FROM questions WHERE id = ?", [(i,) for i in reject_ids])
        conn.execute(
            """UPDATE categories SET total_count = (
                SELECT COUNT(*) FROM questions WHERE category_id = categories.id)"""
        )
        conn.commit()
        print(f"  ✓ {cur.rowcount}건 삭제 + total_count 갱신")
        print("  → JSON 재생성: python3 scripts/export_quiz_json.py")
    elif reject_ids:
        print(f"\n💡 REJECT {len(reject_ids)}건 자동 삭제 가능: python3 scripts/audit_quiz_quality.py --apply-reject")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
