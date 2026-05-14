#!/usr/bin/env python3
"""크롤러 진행 상황 모니터링"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

DB = Path(__file__).parent / "state" / "crawler.db"
LOG_DIR = Path(__file__).parent / "logs"

if not DB.exists():
    print("아직 크롤러가 시작되지 않았습니다.")
    sys.exit(0)

conn = sqlite3.connect(DB)
print("=" * 70)
print(f"공기출 크롤러 상태  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# 연도별 페이지 진행
print("\n[연도별 페이지 수집]")
print(f"  {'연도':>6} {'페이지':>8} {'게시물':>8}")
for row in conn.execute("""
    SELECT year, COUNT(*) as pages, SUM(post_count) as posts
    FROM pages WHERE status='done' GROUP BY year ORDER BY year DESC
"""):
    print(f"  {row[0]:>6} {row[1]:>8} {row[2]:>8}")

# 게시물 상태
print("\n[게시물 처리 상태]")
for row in conn.execute("""
    SELECT status, COUNT(*) FROM posts GROUP BY status ORDER BY status
"""):
    print(f"  {row[0]:>12}: {row[1]}")
total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
done = conn.execute("SELECT COUNT(*) FROM posts WHERE status='done'").fetchone()[0]
pct = (done / total * 100) if total else 0
print(f"  진행률: {done}/{total} ({pct:.1f}%)")

# PDF 통계
print("\n[PDF 다운로드]")
cur = conn.execute("""
    SELECT COUNT(*), SUM(CASE WHEN status='done' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='done' THEN size ELSE 0 END),
           SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)
    FROM pdfs
""")
total_pdfs, done_pdfs, total_size, failed_pdfs = cur.fetchone()
total_size = total_size or 0
print(f"  총 발견: {total_pdfs}")
print(f"  완료: {done_pdfs} ({(done_pdfs/total_pdfs*100) if total_pdfs else 0:.1f}%)")
print(f"  실패: {failed_pdfs}")
print(f"  총 용량: {total_size / 1024 / 1024:.1f} MB ({total_size / 1024 / 1024 / 1024:.2f} GB)")

# 직렬별 분포
print("\n[직렬별 분포 (Top 15)]")
print(f"  {'직렬':<24} {'게시물':>6} {'PDF':>6}")
for row in conn.execute("""
    SELECT p.jikryeol, COUNT(DISTINCT p.url) as posts, COUNT(f.file_url) as pdfs
    FROM posts p
    LEFT JOIN pdfs f ON p.url = f.post_url AND f.status='done'
    WHERE p.status='done'
    GROUP BY p.jikryeol ORDER BY pdfs DESC LIMIT 15
"""):
    print(f"  {row[0]:<24} {row[1]:>6} {row[2]:>6}")

# 최근 로그
print("\n[최근 로그 마지막 10줄]")
logs = sorted(LOG_DIR.glob("crawl_*.log"))
if logs:
    last_log = logs[-1]
    with open(last_log, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-10:]:
        print(f"  {line.rstrip()}")
    print(f"\n  (로그파일: {last_log})")

# 속도 추정
print("\n[처리 속도]")
cur = conn.execute("""
    SELECT MIN(updated_at), MAX(updated_at), COUNT(*) FROM pdfs WHERE status='done'
""")
mi, ma, cnt = cur.fetchone()
if mi and ma and cnt > 1:
    try:
        t0 = datetime.fromisoformat(mi)
        t1 = datetime.fromisoformat(ma)
        elapsed = (t1 - t0).total_seconds()
        rate = cnt / elapsed if elapsed > 0 else 0
        print(f"  PDF/초: {rate:.2f}  /  PDF/시간: {rate * 3600:.0f}")
        # 남은 추정
        pending = conn.execute("SELECT COUNT(*) FROM posts WHERE status NOT IN ('done','failed')").fetchone()[0]
        print(f"  남은 게시물: {pending}")
    except Exception:
        pass
print("=" * 70)
