# exam-ox-pipeline Design Document

> **Summary**: 하베스터 PDF → Rule-based 메타 추출 + Claude Code 세션 보강 → SQLite v2 → 정적 JSON → `/exam/` 학습 페이지. **선택 아키텍처: Option C (Pragmatic Balance)**.
>
> **Project**: OX퀴즈게임
> **Version**: 0.2.0
> **Author**: kakaiuina@gmail.com
> **Date**: 2026-05-14
> **Status**: Draft (Design Phase, PDCA Cycle 1)
> **Planning Doc**: [exam-ox-pipeline.plan.md](../../01-plan/features/exam-ox-pipeline.plan.md)
> **PRD**: [exam-ox-pipeline.prd.md](../../00-pm/exam-ox-pipeline.prd.md)

---

## Context Anchor

> Copied from Plan document. Ensures strategic context survives Design→Do handoff.

| Key | Value |
|-----|-------|
| **WHY** | 검증된 OX 변환 파이프라인 + 1,700+ PDF 위에 "풀이→학습 이동 비용 0" 메타·UI 레이어를 얹어 5년 비전의 문제DB 트랙을 실체화 |
| **WHO** | 1차: 세무사 1차 경제학·재정학 약점자 (Persona 정현우, 28세, 자투리 110분/일) / 2차: 회계사 / 3차: 9급/7급 공무원 |
| **RISK** | Rule-based 메타 정밀도 한계 / 깨진 PDF / 세션 작업 일관성 / 하베스터 저작권 / 학습 페이지 정보 과다 |
| **SUCCESS** | 6주 내 — 누적 400~600문항(세무사·회계사 경제학·재정학 2026~2024), 메타 완성도 ≥80%, "더 학습하기" 클릭율 ≥35%, inbound ≥500세션 |
| **SCOPE** | **In**: DB v2, rule-based 메타, 세션 보강 워크플로우, 학습 페이지, 카테고리 트리, 오답노트, GitHub Pages `/exam/` / **Out**: 외부 LLM API, 회원·마일리지, YouTube 자동 매칭(슬롯만), 멀티플레이 |

---

## 1. Overview

### 1.1 Design Goals

1. **외부 API 의존 0** — 모든 LLM 작업은 Claude Code 세션(Opus) 내에서 수행 (사용자 명시 결정)
2. **기존 자산 무손실** — `data/quiz.db` 기존 행 보존, ALTER TABLE 방식 마이그레이션
3. **세션 협업 표준화** — 빈 메타 → 마크다운 export → 세션 작업 → 마크다운 import → DB 적재의 명확한 4단계
4. **학습 페이지 = 즉시 학습 도구** — 풀이↔학습 0클릭, 5개 메타 영역 토글 펼침
5. **nonsense 자매 라인과 충돌 없음** — `/exam/` 서브패스 격리, GA4 이벤트 prefix 분리

### 1.2 Design Principles

- **Single Responsibility per Script**: 1 스크립트 = 1 단계 (build·extract·enrich·migrate·audit·export)
- **Rule-based first, Session second**: 정규식·키워드로 채울 수 있는 건 자동, 부족분만 세션
- **Fail-safe meta**: 빈 메타는 null로 두고 UI에서 "준비 중" 뱃지 → 거짓 메타 노출 방지
- **Static-first frontend**: fetch + JSON, 서버 없음. LocalStorage는 오답노트만
- **저작권 명시 강제**: 모든 문항 카드에 원본 PDF 파일명 표시

---

## 2. Architecture Options

### 2.0 Architecture Comparison

| Criteria | Option A: Minimal | Option B: Clean | **Option C: Pragmatic** |
|----------|:-:|:-:|:-:|
| **Approach** | 기존 build_quiz_db.py 인라인 확장 | scripts/pipeline/ 패키지 분리 + ES module | 신규 스크립트 3개 분리 + 학습 페이지 독립 폴더 |
| **New Files** | 3 | 15+ | **8** |
| **Modified Files** | 3 | 5+ | **3** |
| **Complexity** | Low | High | **Medium** |
| **Maintainability** | Medium (커진 단일 파일) | High | **High** |
| **Effort** | Low | High | **Medium** |
| **Risk** | 다음 확장(한능검·9급) 시 의존성 高 | 오버스펙·구축 시간 증가 | **균형** |
| **Recommendation** | 단일회성 변환 | 다인 협업 대형 프로젝트 | **MVP + 확장 양립** |

**Selected**: **Option C (Pragmatic Balance)** — **Rationale**:

- Karpathy "단순함 우선·외과적 변경" 원칙 부합
- Plan §7.3 폴더 구조와 정확히 일치
- 1인(사용자) + AI 협업이 주된 운영 형태 → ES module 분할 같은 다인용 추상화 불필요
- 신규 직렬(한능검·9급) 확장 시에도 각 스크립트 단위로 점진 진화 가능
- nonsense 라인 코드 스타일과 일관성 유지

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAW DATA (read-only)                        │
│  /Users/harvester/Library/CloudStorage/GoogleDrive-.../공기출/  │
│  └── {연도}/{직렬}/{과목}/*.pdf  (크롤러가 적재)                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ pdftotext -layout
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BUILD PIPELINE                             │
│  scripts/build_quiz_db.py    ─ Type A/B/C → questions (기존)     │
│  scripts/extract_metadata.py ─ rule-based 메타 채움 (신규)        │
│  scripts/enrich_session.py   ─ 빈 메타 ⇄ 세션 마크다운 (신규)      │
│  scripts/audit_quiz_quality.py ─ 메타 완성도 검사 (확장)          │
│  scripts/export_quiz_json.py   ─ data/exam/*.json (확장)         │
│  scripts/migrate_db_v2.py    ─ v1→v2 (신규)                     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────┐
│   PRIMARY STORE      data/quiz.db (SQLite)   │
│   STATIC EXPORT      data/exam/*.json        │
└──────────────────────────────┬───────────────┘
                               │ fetch (HTTP)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (/exam/)                           │
│  exam/index.html  exam/exam.js  exam/exam.css                   │
│  Components A~G (§5.2 참조)                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
[1] PDF 적재 (크롤러)
       ↓ pdftotext -layout
[2] 텍스트 추출
       ↓ build_quiz_db.py (Type A/B/C 변환)
[3] questions 행 생성 (메타 NULL)
       ↓ extract_metadata.py (정규식·키워드 매칭)
[4] 메타 일부 채움 (topic·tags 자동 가능한 것)
       ↓ enrich_session.py export
[5] 빈 메타 행 → data/_session/{date}_enrich.md
       ↓ ★ Claude Code 세션 (Opus) — 사람-에이전트 협업
[6] 마크다운 내 메타 작성 (explanation_o/x, theory)
       ↓ enrich_session.py import
[7] DB 업데이트 (meta_quality 재계산)
       ↓ audit_quiz_quality.py
[8] 완성도 검사 (≥80% → pass)
       ↓ export_quiz_json.py
[9] data/exam/{category}.json 생성
       ↓ git commit + push
[10] GitHub Pages 배포 → /exam/ 사용자 접근
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `build_quiz_db.py` | `pdftotext` (poppler), 입력 PDF | OX 변환 |
| `extract_metadata.py` | `data/dict/{과목}.json`, sqlite3 | 메타 자동 채움 |
| `enrich_session.py` | sqlite3, 마크다운 파서(자체 정규식) | 세션 IO |
| `audit_quiz_quality.py` | sqlite3 | 품질 검사 |
| `export_quiz_json.py` | sqlite3 | 정적 JSON export |
| `exam/exam.js` | `data/exam/*.json` (fetch), LocalStorage | 학습 페이지 |
| `migrate_db_v2.py` | sqlite3, 기존 `quiz.db` | 스키마 마이그레이션 |

---

## 3. Data Model

### 3.1 Entity Definition

**SQLite (data/quiz.db) — Schema v2**

```sql
-- 기존 (v1, 유지)
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,            -- e.g. "tax-2026-r63-economics"
    name TEXT NOT NULL,                   -- e.g. "재정학"
    exam_group TEXT,                      -- e.g. "세무사 1차 · 2026년 제63회"
    subject TEXT,                         -- e.g. "재정학"
    phase TEXT,                           -- e.g. "1교시"
    source TEXT,
    exam_year INTEGER,
    exam_round INTEGER,
    is_default INTEGER NOT NULL DEFAULT 0,
    display_order INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 기존 (v1) + 신규 6개 컬럼 (v2)
CREATE TABLE questions (
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

    -- ★ v2 신규 ★
    tags TEXT,                            -- JSON array string, e.g. '["외부효과","코즈정리"]'
    topic TEXT,                           -- e.g. "재정학 §3.2 외부효과"
    theory TEXT,                          -- 1-line related theory
    explanation_o TEXT,                   -- "왜 O인지" 1-3줄 (세션 보강)
    explanation_x TEXT,                   -- "왜 X가 아닌지" 1-3줄 (세션 보강)
    meta_quality INTEGER NOT NULL DEFAULT 0,  -- 0~100 점수 (internal use)
    source_pdf TEXT,                      -- 원본 PDF 파일명 (저작권 표시용)

    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE (category_id, source_qid, source_option)
);

-- ★ 신규 (v2) ★
CREATE TABLE related_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    youtube_id TEXT NOT NULL,             -- e.g. "dQw4w9WgXcQ"
    title TEXT,
    channel TEXT,
    timestamp_start INTEGER,              -- seconds (옵션)
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_by TEXT,                        -- "manual"|"session"|"auto"
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE curriculum_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,                -- e.g. "재정학"
    chapter TEXT NOT NULL,                -- e.g. "§3.2 외부효과"
    source_book TEXT,                     -- e.g. "재정학원론 (홍길동, 5판)"
    source_url TEXT,                      -- 무료 자료 링크 (옵션)
    notes TEXT,
    UNIQUE (subject, chapter)
);

-- 인덱스
CREATE INDEX idx_questions_category ON questions(category_id);
CREATE INDEX idx_questions_answer ON questions(category_id, answer);
CREATE INDEX idx_questions_topic ON questions(topic);       -- v2
CREATE INDEX idx_videos_qid ON related_videos(question_id); -- v2
```

### 3.2 Entity Relationships

```
[categories] 1 ──── N [questions] 1 ──── N [related_videos]
                            │
                            └── M:N (via tags JSON) ── [tags] (no table, JSON in-row)
                            │
                            └── via topic ──────── [curriculum_map] (lookup table)
```

### 3.3 JSON Export Schema (data/exam/*.json)

각 카테고리는 분할 JSON 1개:

```json
{
  "category": {
    "slug": "tax-2026-r63-economics",
    "name": "재정학",
    "exam_group": "세무사 1차 · 2026년 제63회",
    "subject": "재정학",
    "phase": "1교시",
    "exam_year": 2026,
    "exam_round": 63
  },
  "questions": [
    {
      "id": 12345,
      "statement": "외부효과가 존재하면 시장이 자원을 효율적으로 배분한다.",
      "answer": "X",
      "explanation": "...(PDF에서 추출된 해설, 있으면)",
      "qtype": "Type_B",
      "topic": "재정학 §3.2 외부효과",
      "tags": ["외부효과", "시장실패", "후생경제학"],
      "theory": "후생경제학 제1정리 — 완전경쟁시장은 파레토 효율적이나, 외부효과 존재 시 정리의 가정이 깨짐",
      "explanation_o": null,
      "explanation_x": "외부효과는 시장가격에 반영되지 않아 사회적 최적 수준과 시장균형이 일치하지 않음 → 자원배분 비효율",
      "meta_quality": 85,
      "source_pdf": "2026-r63-tax-economics.pdf",
      "related_videos": []
    }
  ],
  "_meta": {
    "exported_at": "2026-05-15T03:00:00Z",
    "total": 32,
    "with_full_meta": 26,
    "source": "0gichul.com"
  }
}
```

`data/exam/_index.json` — 카테고리 트리 메타:

```json
{
  "tree": [
    {
      "exam": "세무사",
      "rounds": [
        {
          "year": 2026, "round": 63,
          "categories": [
            { "slug": "tax-2026-r63-economics", "name": "재정학", "total": 32 },
            { "slug": "tax-2026-r63-finance",   "name": "재정학", "total": 28 }
          ]
        }
      ]
    },
    { "exam": "회계사", "rounds": [...] }
  ],
  "_meta": { "total_questions": 480, "categories_count": 12, "updated_at": "..." }
}
```

---

## 4. API Specification

**해당 없음** — 정적 사이트. fetch는 동일 origin GET /exam/data/*.json만.

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/exam/data/_index.json` | 카테고리 트리 | 없음 |
| GET | `/exam/data/{slug}.json` | 특정 카테고리 문항 | 없음 |

---

## 5. UI/UX Design

### 5.1 Wireframe (모바일 세로 우선)

```
화면 1 — 카테고리 선택 (initial)
┌──────────────────────────┐
│  ☰  하베스터 OX 학습       │  ← 헤더 (햄버거)
├──────────────────────────┤
│  세무사 ▼                │
│    └ 2026년 제63회 ▼     │
│        ├ 재정학 (32)     │  ← 클릭 시 풀이 시작
│        ├ 경제학 (28)     │
│        └ 세법학 (40)     │
│    └ 2025년 제62회 ▶     │
│  회계사 ▶                │
├──────────────────────────┤
│  📌 내 오답노트 (12)     │  ← 클릭 시 오답만 풀기
├──────────────────────────┤
│  푸터: 출처 하베스터 · ...  │
└──────────────────────────┘

화면 2 — 풀이 모드 (문항 표시)
┌──────────────────────────┐
│  ← 재정학 · 32중 5번      │  ← 헤더 뒤로/진척
├──────────────────────────┤
│                          │
│   외부효과가 존재하면     │
│   시장이 자원을 효율적    │
│   으로 배분한다.          │
│                          │
│   [출제: 2026-r63 재정학] │  ← 작은 글씨, 출처
├──────────────────────────┤
│   [  O  ]    [  X  ]     │  ← 큰 둥근 버튼
│   (청록)     (빨강)       │     ✓/✗ 아이콘 동시 노출
├──────────────────────────┤

화면 3 — 결과 (O/X 클릭 직후)
┌──────────────────────────┐
│  ❌ 오답  (정답: X)        │
├──────────────────────────┤
│   📝 외부효과는 시장가격에 │
│   반영되지 않아 사회적 최  │
│   적과 시장균형이 다름     │
│                          │
│   [ 더 학습하기 ▼ ]       │  ← 토글 (접힘이 기본)
├──────────────────────────┤
│   [ 다음 문제 → ]         │
└──────────────────────────┘

화면 4 — "더 학습하기" 펼침
┌──────────────────────────┐
│   [ 더 학습하기 ▲ ]       │
├──────────────────────────┤
│   📚 출제범위             │
│   재정학 §3.2 외부효과    │
├──────────────────────────┤
│   🏷  태그                │
│   #외부효과 #시장실패     │
├──────────────────────────┤
│   💡 관련 이론            │
│   후생경제학 제1정리 ...  │
├──────────────────────────┤
│   📖 교과서 챕터          │
│   재정학원론 5판 §3.2     │
├──────────────────────────┤
│   ▶ 관련 영상 (준비 중)   │  ← 빈 슬롯 — 뱃지 노출
└──────────────────────────┘

화면 5 — 오답노트 (별도 모드)
같은 풀이 UI지만 카테고리 = "내 오답 12건" pseudo-category

화면 6 — 카테고리 완료
┌──────────────────────────┐
│   🎉 재정학 32문항 완료!  │
│                          │
│   정답률 24/32 (75%)     │
│                          │
│   [ 다른 카테고리 ]      │
│   [ 오답만 다시 풀기 ]   │
└──────────────────────────┘
```

### 5.2 Components A~G

| ID | Component | File | Role |
|----|-----------|------|------|
| A | CategoryTree | `exam/exam.js::renderTree()` | 자격증·회차·과목 트리 + 오답노트 노드 |
| B | QuizCard | `exam/exam.js::renderQuiz()` | 문항·O/X 버튼·진척 표시·출처 표시 |
| C | ResultPane | `exam/exam.js::renderResult()` | 정/오답 즉시 표시·짧은 해설 |
| D | LearnDrawer | `exam/exam.js::renderLearnDrawer()` | "더 학습하기" 토글 + 5섹션 펼침 |
| E | WrongNoteStore | `exam/exam.js::wrongStore` | LocalStorage CRUD (오답 추가·제거·조회) |
| F | Footer | `exam/index.html` 정적 | 저작권·출처·nonsense 상호 링크 |
| G | CompletionScreen | `exam/exam.js::renderComplete()` | 카테고리 완료 시 정답률·다음 옵션 |

### 5.3 Design Tokens (nonsense 재사용)

| Token | Value | Source |
|-------|-------|--------|
| `--color-o` | `#00C2A8` | nonsense `style.css` |
| `--color-x` | `#FF5454` | nonsense `style.css` |
| `--color-bg` | `#FFFEF8` | nonsense (베이지) |
| `--color-text` | `#1a1a1a` | nonsense |
| `--font-display` | `'Black Han Sans'` | nonsense (Google Fonts) |
| `--font-body` | `'Jua'` | nonsense |
| `--radius-btn` | `999px` (둥근) | nonsense O/X 버튼 |
| `--space-base` | `16px` | nonsense 8px grid |

학습 페이지 추가 토큰:
| Token | Value | Use |
|-------|-------|-----|
| `--color-correct` | `#10b981` (green) | 정답 표시 |
| `--color-wrong` | `#ef4444` (red) | 오답 표시 |
| `--color-tag-bg` | `#eef2ff` | 태그 칩 배경 |
| `--color-badge-pending` | `#fbbf24` | "준비 중" 뱃지 |

---

## 6. Error Handling

| 상황 | 동작 | UX |
|------|------|----|
| `data/exam/*.json` fetch 실패 | 재시도 3회 (1s, 2s, 4s) → 실패 시 친화적 메시지 | "잠시 후 다시 시도해주세요" + 새로고침 버튼 |
| `data/exam/_index.json` 누락 | 카테고리 트리 빈 메시지 | "준비 중인 카테고리입니다" |
| LocalStorage 접근 실패 (사파리 시크릿 등) | wrongStore = 메모리만 | 푸터 상단에 toast: "이 브라우저는 오답노트를 저장하지 않습니다" |
| 빈 메타 (`topic`/`tags`/`theory`/`explanation_o`/`explanation_x` 모두 null) | 해당 섹션 "준비 중" 뱃지 | 학습 페이지 정보 부족 안내 |
| PDF 변환 실패 (build_quiz_db.py) | `data/pdf_errors.json` 기록, 스킵 | (사용자가 audit 보고 확인) |
| `enrich_session.py` 마크다운 파싱 실패 | 해당 Q는 스킵, stderr 로그 | (개발 단계) |

---

## 7. Security Considerations

### 7.1 XSS

- 문항·해설 본문 — `element.textContent` 주입, `innerHTML` 금지
- 태그 칩은 `textContent` + `class` 처리, 사용자 입력 없음 → low risk
- 카테고리명·과목명도 동일

### 7.2 CSP (Content Security Policy)

nonsense `index.html`의 CSP 동일 재사용 + 신규 외부 도메인 추가 없음:

```
default-src 'self';
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src https://fonts.gstatic.com;
img-src 'self' data: https://www.google-analytics.com;
connect-src 'self' https://www.google-analytics.com;
```

(향후 YouTube iframe 도입 시 `frame-src https://www.youtube.com` 추가 필요 — 별도 Phase)

### 7.3 저작권 표시 강제

- 푸터: "문항·해설 출처: [0gichul.com](https://0gichul.com/) · 학습 메타데이터: harvester 자체 분석"
- 카드 우측 하단: `2026-r63-tax-economics.pdf` 같이 원본 PDF 파일명 표시
- `source_pdf` 컬럼이 NULL이면 카드 표시 X (저작권 위험 회피)

### 7.4 LocalStorage 데이터

- `oxquiz.exam.wrong_notes` — 문항 ID 배열만 (개인정보 없음)
- 단일 키, 50KB 미만 예상

---

## 8. Test Plan

### 8.1 L1 — Script Unit Tests (Python)

| ID | Target | Test | Expected |
|----|--------|------|----------|
| L1-01 | `extract_metadata.parse_topic("민법 제390조에 따라...")` | 정규식 매칭 | `{"topic": "민법 §390"}` |
| L1-02 | `extract_metadata.match_tags("외부효과는 시장가격에...", dict_econ)` | 키워드 매칭 | `["외부효과", "시장가격"]` |
| L1-03 | `enrich_session.export(limit=10)` | 빈 메타 10건 마크다운 | 파일 생성, 10개 섹션 |
| L1-04 | `enrich_session.import_md(path)` | 사용자 작성 마크다운 → DB | meta_quality 점수 갱신 |
| L1-05 | `migrate_db_v2.run()` | v1 DB → v2 ALTER TABLE | 기존 행 무손실 + 신규 컬럼 null |
| L1-06 | `audit_quiz_quality.check_meta_completeness()` | meta_quality 분포 | ≥80% 충족 여부 보고 |
| L1-07 | `export_quiz_json.export_exam()` | DB → data/exam/*.json | 카테고리별 JSON + _index.json |

### 8.2 L2 — Frontend UI Tests (수동)

| ID | Scenario | Expected |
|----|----------|----------|
| L2-01 | 학습 페이지 진입 → 카테고리 트리 노출 | 자격증·회차·과목 3단 트리 렌더 |
| L2-02 | 카테고리 클릭 → 풀이 화면 | 문항 표시, O/X 버튼 활성 |
| L2-03 | O 클릭 (정답) → 결과 화면 | "정답" 뱃지 + 짧은 해설 + "더 학습" 버튼 |
| L2-04 | X 클릭 (오답) → 결과 화면 | "오답" 뱃지 + 정답 표시 + 짧은 해설 |
| L2-05 | "더 학습하기" 클릭 → 5섹션 펼침 | 출제범위·태그·이론·교과서·영상 슬롯 모두 노출 |
| L2-06 | 메타 빈 섹션 | "준비 중" 뱃지 |
| L2-07 | 다음 문제 → 진척 표시 갱신 | "5/32" → "6/32" |
| L2-08 | 카테고리 완료 → 완료 화면 | 정답률 + 다음 옵션 |
| L2-09 | 오답 발생 → 오답노트 자동 추가 | LocalStorage에 ID 저장 |
| L2-10 | 카테고리 트리에 "오답 N건" 노드 | 정확한 카운트 |
| L2-11 | 오답만 풀기 모드 → 오답만 출제 | 오답 외 문항 없음 |

### 8.3 L3 — E2E Scenario Tests

| ID | Scenario | Expected |
|----|----------|----------|
| L3-01 | 첫 방문 → 트리 → 30문항 완주 → 결과 확인 → 새로고침 → 오답노트 유지 | LocalStorage 영속 |
| L3-02 | iOS Safari + Android Chrome 모두 정상 풀이 | 모바일 호환 |
| L3-03 | 네트워크 끊김 (200문항 fetch 후 오프라인) → 풀이 가능 | JSON in-memory 후 진행 |
| L3-04 | 다른 카테고리로 전환 → 진척 초기화·오답노트는 유지 | 카테고리 격리 + 오답 누적 |

### 8.4 L4 — Performance / L5 — Security

| ID | Target | Method |
|----|--------|--------|
| L4-01 | Lighthouse Mobile Performance | ≥ 90 |
| L4-02 | LCP < 2.5s, FID < 100ms, CLS < 0.1 | Lighthouse |
| L5-01 | CSP 위반 0 | DevTools console |
| L5-02 | XSS 시도 ("`<script>alert(1)</script>`"를 statement에 주입 시) | textContent 처리 → 무력화 |

---

## 9. Clean Architecture (Simplified for Static Site)

```
┌─────────────────────────────────────────────────────────────┐
│ PRESENTATION (Frontend)                                     │
│   exam/index.html  exam/exam.js  exam/exam.css              │
│   ├─ A. CategoryTree                                        │
│   ├─ B. QuizCard                                            │
│   ├─ C. ResultPane                                          │
│   ├─ D. LearnDrawer                                         │
│   ├─ E. WrongNoteStore (LocalStorage)                       │
│   ├─ F. Footer                                              │
│   └─ G. CompletionScreen                                    │
├─────────────────────────────────────────────────────────────┤
│ DATA INTERFACE (Static JSON)                                │
│   /exam/data/_index.json                                    │
│   /exam/data/{category-slug}.json                           │
├─────────────────────────────────────────────────────────────┤
│ BUILD / ENRICH PIPELINE (Python scripts)                    │
│   build_quiz_db.py    extract_metadata.py                   │
│   enrich_session.py   audit_quiz_quality.py                 │
│   export_quiz_json.py migrate_db_v2.py                      │
├─────────────────────────────────────────────────────────────┤
│ STORAGE                                                     │
│   data/quiz.db (SQLite, source of truth)                    │
│   data/dict/{과목}.json (keyword dictionaries)               │
│   data/exam/*.json (static export, git tracked)             │
├─────────────────────────────────────────────────────────────┤
│ SOURCE (read-only)                                          │
│   GoogleDrive/공기출/{연도}/{직렬}/{과목}/*.pdf              │
└─────────────────────────────────────────────────────────────┘
```

각 레이어는 위/아래만 의존. 동일 레이어 내 횡적 의존 X.

---

## 10. Coding Convention Reference

### 10.1 Python (scripts)

- snake_case 함수·변수
- 1 스크립트 = 1 entry point (`if __name__ == "__main__":`)
- 인자: `argparse`, `--help` 기본
- 예외: 단계별 명시적 catch + `data/pdf_errors.json` 누적 기록 (변환 실패 패턴)
- 의존성 최소: 표준 라이브러리 + `pdftotext` CLI (poppler) — pip 패키지 0개 목표

### 10.2 Frontend (JS/CSS)

- ES2020+ 가능 (모듈 X, 단일 파일)
- `const` 우선, `let` 필요 시만, `var` 금지
- 함수 prefix: `render*`(UI 빌드), `store*`(상태), `handle*`(이벤트), `compute*`(계산)
- DOM 조작: `textContent` 우선, `innerHTML` 금지
- CSS: 토큰은 `:root` 변수, BEM lite (block__element--modifier)

### 10.3 SQL

- 컬럼명 snake_case
- 마이그레이션 SQL은 `scripts/migrate_db_v2.py` 내 인라인 (단일 파일 단순성)

### 10.4 JSON

- 키 camelCase는 금지, **snake_case 통일** (Python/SQL과 일관)
- 모든 export에 `_meta` 필드 (생성 시각·총 수·출처)

---

## 11. Implementation Guide

### 11.1 Module Map (Session Guide)

| Module | Files | Responsibility | Est. LOC |
|--------|-------|----------------|----------|
| M1: DB Migration | `scripts/migrate_db_v2.py` | v1 quiz.db → v2 ALTER TABLE + 신규 테이블 | 80 |
| M2: Build Pipeline 확장 | `scripts/build_quiz_db.py` (수정) | 신규 컬럼 NULL로 적재, source_pdf 채움 | +30 |
| M3: Metadata Extractor | `scripts/extract_metadata.py` (신규) | 정규식 + 키워드 매칭으로 topic·tags 채움 | 180 |
| M4: Session Enricher | `scripts/enrich_session.py` (신규) | export/import 마크다운 | 200 |
| M5: Dict Files | `data/dict/economics.json` + `finance.json` | 도메인 키워드 사전 (각 50~100개) | 200 (JSON) |
| M6: Audit 확장 | `scripts/audit_quiz_quality.py` (수정) | meta_quality 분포·완성도 검사 | +50 |
| M7: JSON Export 확장 | `scripts/export_quiz_json.py` (수정) | data/exam/*.json + _index.json | +80 |
| M8: Frontend Skeleton | `exam/index.html`, `exam/exam.css` | HTML 구조 + 토큰 적용 | 250 |
| M9: Frontend Logic | `exam/exam.js` (Components A~G) | 카테고리 트리·풀이·결과·더학습·오답·완료 | 450 |
| M10: MVP Data Load | (운영) | 세무사·회계사 경제학·재정학 2026~2024 12 PDF 처리 | (세션 작업) |
| M11: Audit + Deploy | `git push` → GitHub Pages | 라이브 검증·LightHouse·GA4 | (운영) |

### 11.2 Build/Run Commands

```bash
# 1. DB v2 마이그레이션 (1회만)
python3 scripts/migrate_db_v2.py

# 2. PDF → questions 변환 (특정 PDF 묶음)
python3 scripts/build_quiz_db.py --input "하베스터/2026/전문직-세무사/재정학/" --category-slug tax-2026-r63-finance

# 3. Rule-based 메타 추출 (방금 추가된 행만)
python3 scripts/extract_metadata.py --category tax-2026-r63-finance

# 4. 세션 보강 export (빈 메타 50개)
python3 scripts/enrich_session.py export --limit 50 --out data/_session/2026-05-14_enrich.md

# 5. ★ Claude Code 세션 (사용자가 마크다운 열고 보강 요청) ★
#    예: "@data/_session/2026-05-14_enrich.md 메타 채워줘"

# 6. 세션 보강 import
python3 scripts/enrich_session.py import data/_session/2026-05-14_enrich.md

# 7. 품질 audit
python3 scripts/audit_quiz_quality.py --meta-coverage

# 8. 정적 JSON export
python3 scripts/export_quiz_json.py --exam

# 9. 로컬 미리보기
python3 -m http.server 8000  # http://localhost:8000/exam/

# 10. 배포
git add . && git commit -m "exam-ox-pipeline: 세무사 재정학 2026 r63" && git push
```

### 11.3 Session Guide (추천 세션 분할)

3개 세션 분할 권장:

**Session 1 — Backend Pipeline (DB·스크립트)** — Module M1·M2·M6·M7
- DB v2 마이그레이션·`build_quiz_db.py` 확장·`audit` 확장·`export` 확장
- 산출 검증: 기존 nonsense는 깨지지 않고 `data/quiz.db` v2 정상 운영

**Session 2 — Metadata Pipeline (자동·세션)** — Module M3·M4·M5
- `extract_metadata.py` + `enrich_session.py` + `data/dict/*.json`
- 산출 검증: 12 PDF 중 첫 1개 카테고리(예: 재정학 2026)에서 메타 완성도 ≥80%

**Session 3 — Frontend (UI/UX)** — Module M8·M9
- `exam/index.html`·`exam/exam.css`·`exam/exam.js` Components A~G
- 산출 검증: 로컬에서 1 카테고리 풀이 완주 + 오답노트·"더 학습하기" 정상 동작

**Session 4 — MVP Data Load + Deploy** — Module M10·M11
- 세무사·회계사 경제학·재정학 2026~2024 12 PDF 전수 적재 + 메타 보강 + audit pass + 배포

`/pdca do exam-ox-pipeline --scope module-1,module-2,module-6,module-7` 같이 부분 호출 가능 (각 세션에 대응).

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-14 | Initial draft — Option C 선택, 11 모듈 세션 가이드 포함 | kakaiuina@gmail.com (with Claude Code Opus) |
