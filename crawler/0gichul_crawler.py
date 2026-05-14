#!/usr/bin/env python3
"""
0gichul.com 크롤러
- 연도/직렬/과목 3단 분류로 PDF 일괄 다운로드
- SQLite 상태 DB로 resumable
- robots.txt 준수: Crawl-delay 3s
"""
import os
import re
import sys
import time
import json
import sqlite3
import signal
import logging
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import argparse
from pathlib import Path
from datetime import datetime

# ---------- 경로 ----------
PROJ = Path("/Users/harvester/Library/Mobile Documents/com~apple~CloudDocs/1. 프로젝트/0. 클로드코드/OX퀴즈게임")
DRIVE_BASE = Path("/Users/harvester/Library/CloudStorage/GoogleDrive-kakaiuina@gmail.com/내 드라이브/공기출")
STATE_DB = PROJ / "crawler" / "state" / "crawler.db"
LOG_DIR = PROJ / "crawler" / "logs"

# ---------- 설정 ----------
BASE = "https://0gichul.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 0gichul-archive-bot/1.0"
CRAWL_DELAY = 3.0          # robots.txt 명시 (3초)
DOWNLOAD_DELAY = 1.0       # PDF 다운로드 사이 추가 텀
PAGE_TIMEOUT = 30
PDF_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_BACKOFF = 5

# ---------- 로깅 ----------
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("0gichul")

# ---------- 종료 시그널 ----------
HALT = False
def _halt(sig, frame):
    global HALT
    log.warning(f"SIGNAL {sig} 받음 → 현재 작업 완료 후 종료")
    HALT = True
signal.signal(signal.SIGTERM, _halt)
signal.signal(signal.SIGINT, _halt)

# ---------- HTTP ----------
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [("User-Agent", UA), ("Accept-Language", "ko-KR,ko;q=0.9")]

_last_request_ts = 0.0
def _rate_limit():
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < CRAWL_DELAY:
        time.sleep(CRAWL_DELAY - elapsed)
    _last_request_ts = time.time()

def fetch(url, timeout=PAGE_TIMEOUT, binary=False):
    for attempt in range(MAX_RETRIES):
        _rate_limit()
        try:
            with opener.open(url, timeout=timeout) as r:
                data = r.read()
                if binary:
                    cd = r.headers.get("Content-Disposition", "")
                    ct = r.headers.get("Content-Type", "")
                    final_url = r.geturl()
                    return data, cd, ct, final_url
                return data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = RETRY_BACKOFF * (attempt + 1) * 2
                log.warning(f"HTTP {e.code} on {url} → {wait}s 후 재시도")
                time.sleep(wait)
                continue
            if e.code == 404:
                log.warning(f"404 {url}")
                return None if not binary else (None, "", "", url)
            log.error(f"HTTP {e.code} {url}: {e}")
            if attempt == MAX_RETRIES - 1:
                return None if not binary else (None, "", "", url)
            time.sleep(RETRY_BACKOFF * (attempt + 1))
        except Exception as e:
            log.error(f"fetch error {url}: {e}")
            if attempt == MAX_RETRIES - 1:
                return None if not binary else (None, "", "", url)
            time.sleep(RETRY_BACKOFF * (attempt + 1))
    return None if not binary else (None, "", "", url)

# ---------- 상태 DB ----------
def db_connect():
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STATE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            url TEXT PRIMARY KEY,
            year INTEGER,
            post_id TEXT,
            title TEXT,
            jikryeol TEXT,
            gwamok TEXT,
            status TEXT,        -- pending|fetched|done|failed
            pdf_count INTEGER DEFAULT 0,
            error TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            file_url TEXT PRIMARY KEY,
            post_url TEXT,
            file_srl TEXT,
            local_path TEXT,
            size INTEGER,
            status TEXT,        -- pending|done|failed
            error TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            page_key TEXT PRIMARY KEY,  -- y2024:1
            year INTEGER,
            page_no INTEGER,
            post_count INTEGER,
            status TEXT,        -- done|failed
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn

# ---------- 제목 파서 ----------
# 제목 패턴 예: "2024 국가직 9급 한국사 문제 정답"
#               "2024 경영지도사 기업진단론 문제 정답"
#               "2024 9급 공채 전과목 문제 정답 - 2024.4.6."
#               "2024 해경 간부후보 헌법 문제 정답"
#               "2024 소방 승진시험 소방법령1 문제 정답"
JIKRYEOL_MAP = [
    # 순서 중요: 더 긴 매칭이 먼저
    (r"국가직\s*5급|5급\s*공채|행정고시|기술고시", "국가직-5급"),
    (r"국가직\s*7급|7급\s*공채(?!.*지방)", "국가직-7급"),
    (r"국가직\s*9급|9급\s*공채(?!.*지방)", "국가직-9급"),
    (r"지방직\s*7급|지방\s*7급", "지방직-7급"),
    (r"지방직\s*9급|지방\s*9급", "지방직-9급"),
    (r"서울시\s*7급", "서울시-7급"),
    (r"서울시\s*9급|서울시(?!.*7급)", "서울시-9급"),
    (r"국회직\s*5급", "국회직-5급"),
    (r"국회직\s*8급", "국회직-8급"),
    (r"국회직\s*9급", "국회직-9급"),
    (r"법원직\s*5급", "법원직-5급"),
    (r"법원직\s*9급|법원직(?!.*5급)", "법원직-9급"),
    (r"경찰\s*간부|간부후보(?=.*경찰)", "경찰-간부"),
    (r"경찰\s*승진", "경찰-승진"),
    (r"경찰\s*특공대", "경찰-특공대"),
    (r"경찰\s*공채|순경", "경찰-공채"),
    (r"경찰", "경찰-기타"),
    (r"소방\s*간부", "소방-간부"),
    (r"소방\s*승진", "소방-승진"),
    (r"소방\s*공채", "소방-공채"),
    (r"소방", "소방-기타"),
    (r"해경\s*간부", "해경-간부"),
    (r"해경\s*승진", "해경-승진"),
    (r"해경\s*공채", "해경-공채"),
    (r"해경", "해경-기타"),
    (r"군무원\s*5급", "군무원-5급"),
    (r"군무원\s*7급", "군무원-7급"),
    (r"군무원\s*9급", "군무원-9급"),
    (r"군무원", "군무원-기타"),
    (r"기상직\s*7급", "기상직-7급"),
    (r"기상직\s*9급", "기상직-9급"),
    (r"외무영사직|외교관후보자", "외교-외무영사직"),
    (r"감정평가사", "전문직-감정평가사"),
    (r"관세사", "전문직-관세사"),
    (r"노무사", "전문직-노무사"),
    (r"법무사", "전문직-법무사"),
    (r"변리사", "전문직-변리사"),
    (r"변호사시험|변호사", "전문직-변호사"),
    (r"세무사", "전문직-세무사"),
    (r"행정사", "전문직-행정사"),
    (r"회계사", "전문직-회계사"),
    (r"경영지도사", "전문직-경영지도사"),
    (r"가맹거래사", "전문직-가맹거래사"),
    (r"사법시험", "전문직-사법시험"),
    (r"한국사능력검정|한능검", "한능검"),
    (r"PSAT|피셋", "PSAT"),
    (r"비상대비", "기타-비상대비"),
    (r"NCS", "NCS"),
]

YEAR_RE = re.compile(r"^(\d{4})\s+")

def parse_title(title):
    """제목 → (직렬, 과목)"""
    if not title:
        return ("미분류", "미분류")
    # 연도 제거
    t = YEAR_RE.sub("", title.strip())
    # 직렬 매칭
    jikryeol = "기타"
    j_match_end = 0
    for pat, name in JIKRYEOL_MAP:
        m = re.search(pat, t)
        if m:
            jikryeol = name
            j_match_end = m.end()
            break
    # 과목 = 직렬 뒤부터 "문제 정답" 앞까지
    remainder = t[j_match_end:].strip() if j_match_end else t
    remainder = re.sub(r"\s*-\s*\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}.*$", "", remainder)  # 날짜 제거
    remainder = re.sub(r"\s*(문제\s*정답|전과목|해설).*$", "", remainder).strip()
    # 직렬 매칭 후 잔류 보조어 제거 (간부후보→후보, 승진시험→시험, 업무담당자, 시험 심화, 등)
    remainder = re.sub(
        r"^(후보(자)?|시험|공채|특공|업무담당자|담당자|시험\s*심화|시험\s*기본|간부|승진|순경|채용)\s+",
        "", remainder).strip()
    remainder = re.sub(r"\s+", " ", remainder).strip()
    if not remainder:
        remainder = "전과목" if "전과목" in t else "기타"
    return (jikryeol, remainder)

# ---------- 파일명 안전화 ----------
SAFE_RE = re.compile(r'[/\\:\*\?"<>\|\x00-\x1f]')
def safe_name(name, maxlen=120):
    name = SAFE_RE.sub("_", name).strip().strip(".")
    if len(name) > maxlen:
        # 확장자 보존
        if "." in name[-10:]:
            base, ext = name.rsplit(".", 1)
            name = base[:maxlen - len(ext) - 1] + "." + ext
        else:
            name = name[:maxlen]
    return name or "_"

# ---------- 게시물 목록 수집 ----------
POST_LINK_RE = re.compile(
    r'<a\s+href="(/y(\d{4})/(\d+))(?:\?[^"]*)?"[^>]*class="h3t"[^>]*>([^<]+)',
    re.IGNORECASE,
)

def list_posts_on_page(year, page_no):
    if page_no == 1:
        url = f"{BASE}/y{year}"
    else:
        url = f"{BASE}/y{year}?page={page_no}"
    html = fetch(url)
    if html is None:
        return None
    posts = []
    seen = set()
    for m in POST_LINK_RE.finditer(html):
        url_path, y, pid, title = m.group(1), int(m.group(2)), m.group(3), m.group(4).strip()
        if y != year:
            continue
        if url_path in seen:
            continue
        # 댓글 링크/숨김 미세 텍스트 제외
        if len(title) < 5:
            continue
        seen.add(url_path)
        posts.append({"url": url_path, "post_id": pid, "title": title})
    return posts

def detect_max_page(year):
    """첫 페이지의 페이지네이션에서 마지막 페이지 찾기"""
    html = fetch(f"{BASE}/y{year}")
    if html is None:
        return 0
    pages = re.findall(r"\?page=(\d+)", html)
    if not pages:
        # 1페이지로 끝나는지 확인 (다음 페이지 표기 없음)
        return 1 if re.search(rf'/y{year}/\d+', html) else 0
    return max(int(p) for p in pages)

# ---------- 게시물 상세 → PDF URL ----------
PDF_DOWNLOAD_RE = re.compile(
    r'href="(/?\?module=file(?:&amp;|&)act=procFileDownload(?:&amp;|&)file_srl=(\d+)[^"]*?force_download=Y[^"]*)"'
)

def list_pdfs_on_post(post_url):
    html = fetch(f"{BASE}{post_url}")
    if html is None:
        return None
    pdfs = []
    seen = set()
    for m in PDF_DOWNLOAD_RE.finditer(html):
        raw_href = m.group(1).replace("&amp;", "&")
        file_srl = m.group(2)
        if file_srl in seen:
            continue
        seen.add(file_srl)
        if not raw_href.startswith("/"):
            raw_href = "/" + raw_href.lstrip("?")
            raw_href = "/" + raw_href if not raw_href.startswith("/?") else raw_href
        full_url = f"{BASE}{raw_href}" if raw_href.startswith("/") else raw_href
        pdfs.append({"file_url": full_url, "file_srl": file_srl})
    # 파일명 힌트 (해설/문제 구분용) - 가능하면 페이지에서 추출
    # XE/Rhymix는 보통 <a class="xefu-filename">파일명.pdf</a> 형태로 표시
    filename_hints = re.findall(
        r'file_srl=(\d+)[^"]*?"[^>]*>[^<]*</a>\s*<[^>]*>([^<]+\.(?:pdf|hwp|zip|docx?))',
        html,
        re.IGNORECASE,
    )
    hints_map = {srl: name.strip() for srl, name in filename_hints}
    for p in pdfs:
        if p["file_srl"] in hints_map:
            p["hint_name"] = hints_map[p["file_srl"]]
    # 더 간단한 패턴: 파일명이 다른 a 태그에 들어가는 경우
    if not any("hint_name" in p for p in pdfs):
        # 파일명을 다른 위치에서 찾기
        # 파일 박스 안에 srl과 함께 파일명 텍스트
        for p in pdfs:
            srl = p["file_srl"]
            # file_srl 근처 200자 안에서 .pdf 파일명 찾기
            idx = html.find(f"file_srl={srl}")
            if idx > 0:
                window = html[max(0, idx-300):idx+500]
                fname_m = re.search(r'([^>"\'\s][^>"\'\s\<]{1,100}\.(?:pdf|hwp|zip|docx?))', window, re.IGNORECASE)
                if fname_m:
                    p["hint_name"] = fname_m.group(1).strip()
    return pdfs

# ---------- 다운로드 ----------
def parse_cd_filename(cd_header):
    """Content-Disposition에서 파일명 추출"""
    if not cd_header:
        return None
    # filename*=UTF-8''xxx
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd_header, re.IGNORECASE)
    if m:
        try:
            return urllib.parse.unquote(m.group(1).strip().strip('"\''))
        except Exception:
            pass
    # filename="xxx"
    m = re.search(r'filename="?([^";]+)"?', cd_header, re.IGNORECASE)
    if m:
        name = m.group(1).strip().strip('"\'')
        # 일부는 이미 UTF-8, 일부는 latin-1로 잘못 인코딩됨
        try:
            return name.encode("latin-1").decode("utf-8")
        except Exception:
            return name
    return None

def download_pdf(file_url, target_dir, hint_name=None):
    target_dir.mkdir(parents=True, exist_ok=True)
    data, cd, ct, final_url = fetch(file_url, timeout=PDF_TIMEOUT, binary=True)
    if data is None:
        return None, "fetch_failed"
    # 파일명 결정: (1) final URL path → (2) Content-Disposition → (3) hint_name → (4) file_srl
    filename = None
    if final_url:
        try:
            parsed = urllib.parse.urlparse(final_url)
            base = os.path.basename(parsed.path)
            if base and "." in base:
                filename = urllib.parse.unquote(base)
        except Exception:
            pass
    if not filename:
        filename = parse_cd_filename(cd) or hint_name
    if not filename:
        srl_m = re.search(r"file_srl=(\d+)", file_url)
        filename = f"file_{srl_m.group(1) if srl_m else 'unknown'}.bin"
    # 확장자 보강: PDF magic 우선
    if data[:5] == b"%PDF-" and not filename.lower().endswith(".pdf"):
        filename = re.sub(r"\.(bin|tmp)$", "", filename, flags=re.IGNORECASE) + ".pdf"
    elif "." not in filename:
        ext = ".pdf" if "pdf" in (ct or "").lower() else ".bin"
        filename += ext
    filename = safe_name(filename)
    target = target_dir / filename
    # 중복 방지
    i = 1
    base_target = target
    while target.exists():
        stem = base_target.stem
        suff = base_target.suffix
        target = target_dir / f"{stem}_{i}{suff}"
        i += 1
    with open(target, "wb") as f:
        f.write(data)
    time.sleep(DOWNLOAD_DELAY)
    return str(target), None

# ---------- 메인 워커 ----------
def process_year(year, conn):
    log.info(f"=== 연도 {year} 시작 ===")
    max_page = detect_max_page(year)
    if max_page == 0:
        log.warning(f"y{year}: 페이지 없음")
        return
    log.info(f"y{year}: 총 {max_page}페이지")
    # 1단계: 모든 페이지에서 게시물 수집 (DB 등록)
    for page_no in range(1, max_page + 1):
        if HALT:
            log.warning("HALT 감지 → 종료")
            return
        page_key = f"y{year}:{page_no}"
        cur = conn.execute("SELECT status FROM pages WHERE page_key=?", (page_key,))
        row = cur.fetchone()
        if row and row[0] == "done":
            log.info(f"  [{page_key}] 이미 수집됨, 스킵")
            continue
        posts = list_posts_on_page(year, page_no)
        if posts is None:
            log.error(f"  [{page_key}] 페이지 로드 실패")
            conn.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?)",
                         (page_key, year, page_no, 0, "failed", datetime.now().isoformat()))
            conn.commit()
            continue
        log.info(f"  [{page_key}] {len(posts)}개 게시물")
        for p in posts:
            jik, gwa = parse_title(p["title"])
            conn.execute("""INSERT OR IGNORE INTO posts
                (url, year, post_id, title, jikryeol, gwamok, status, updated_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (p["url"], year, p["post_id"], p["title"], jik, gwa, "pending",
                 datetime.now().isoformat()))
        conn.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?)",
                     (page_key, year, page_no, len(posts), "done", datetime.now().isoformat()))
        conn.commit()
    # 2단계: 이 연도의 미처리 게시물 일괄 처리
    while True:
        if HALT:
            return
        cur = conn.execute(
            "SELECT url, title, jikryeol, gwamok FROM posts WHERE year=? AND status IN ('pending','fetched','failed') LIMIT 50",
            (year,))
        rows = cur.fetchall()
        if not rows:
            break
        for (url, title, jik, gwa) in rows:
            if HALT:
                return
            process_post(url, year, title, jik, gwa, conn)

def process_post(url, year, title, jik, gwa, conn):
    log.info(f"    [{year}] {title}")
    pdfs = list_pdfs_on_post(url)
    if pdfs is None:
        conn.execute("UPDATE posts SET status='failed', error='post_fetch_failed', updated_at=? WHERE url=?",
                     (datetime.now().isoformat(), url))
        conn.commit()
        return
    if not pdfs:
        log.info(f"      PDF 없음")
        conn.execute("UPDATE posts SET status='done', pdf_count=0, updated_at=? WHERE url=?",
                     (datetime.now().isoformat(), url))
        conn.commit()
        return
    # 저장 폴더 = 공기출/{year}/{jikryeol}/{gwamok}/
    jik_safe = safe_name(jik, 60)
    gwa_safe = safe_name(gwa, 60)
    target_dir = DRIVE_BASE / str(year) / jik_safe / gwa_safe
    # 게시물 제목을 파일명 prefix에 (해설/문제 구분 위해)
    title_prefix = safe_name(title, 80)
    success = 0
    for pdf in pdfs:
        if HALT:
            return
        file_url = pdf["file_url"]
        # 이미 받았는지 확인
        cur = conn.execute("SELECT status, local_path FROM pdfs WHERE file_url=?", (file_url,))
        existing = cur.fetchone()
        if existing and existing[0] == "done" and existing[1] and Path(existing[1]).exists():
            success += 1
            continue
        hint = pdf.get("hint_name")
        # hint_name이 있으면 그것 사용, 없으면 게시물 제목 + file_srl
        if hint:
            preferred = f"{title_prefix} - {safe_name(hint)}"
        else:
            preferred = None
        local_path, err = download_pdf(file_url, target_dir, hint_name=preferred)
        if local_path:
            try:
                size = Path(local_path).stat().st_size
            except Exception:
                size = 0
            conn.execute("INSERT OR REPLACE INTO pdfs VALUES (?,?,?,?,?,?,?,?)",
                         (file_url, url, pdf["file_srl"], local_path, size, "done", None,
                          datetime.now().isoformat()))
            success += 1
        else:
            conn.execute("INSERT OR REPLACE INTO pdfs VALUES (?,?,?,?,?,?,?,?)",
                         (file_url, url, pdf["file_srl"], None, 0, "failed", err,
                          datetime.now().isoformat()))
        conn.commit()
    log.info(f"      → {success}/{len(pdfs)}개 다운로드")
    final_status = "done" if success == len(pdfs) else ("fetched" if success > 0 else "failed")
    conn.execute("UPDATE posts SET status=?, pdf_count=?, updated_at=? WHERE url=?",
                 (final_status, success, datetime.now().isoformat(), url))
    conn.commit()

# ---------- 진입점 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2000-2026", help="예: 2024 또는 2020-2026")
    ap.add_argument("--reverse", action="store_true", help="최신 연도부터")
    args = ap.parse_args()

    if "-" in args.years:
        a, b = args.years.split("-")
        years = list(range(int(a), int(b) + 1))
    else:
        years = [int(args.years)]
    if args.reverse:
        years = list(reversed(years))

    DRIVE_BASE.mkdir(parents=True, exist_ok=True)
    conn = db_connect()
    log.info(f"=== 시작: 연도={years} 저장={DRIVE_BASE}")
    log.info(f"로그파일: {log_file}")

    for year in years:
        if HALT:
            break
        try:
            process_year(year, conn)
        except Exception as e:
            log.exception(f"y{year} 예외: {e}")
            continue

    # 통계
    cur = conn.execute("SELECT COUNT(*), SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) FROM posts")
    total_posts, done_posts = cur.fetchone()
    cur = conn.execute("SELECT COUNT(*), SUM(CASE WHEN status='done' THEN 1 ELSE 0 END), SUM(size) FROM pdfs")
    total_pdfs, done_pdfs, total_size = cur.fetchone()
    log.info(f"=== 완료 ===")
    log.info(f"게시물: {done_posts}/{total_posts}")
    log.info(f"PDF: {done_pdfs}/{total_pdfs} ({(total_size or 0)/1024/1024:.1f} MB)")

if __name__ == "__main__":
    main()
