# exam-ox-pipeline Planning Document

> **Summary**: 하베스터 PDF(현 1,700+, 최종 50,000+) → 자동 메타데이터·해설 보강 → 학습형 OX 웹페이지. **LLM은 외부 API 호출 없이 Claude Code 세션에서 직접 처리** (사람-에이전트 협업 워크플로우).
>
> **Project**: OX퀴즈게임
> **Version**: 0.2.0 (exam-ox-pipeline initial)
> **Author**: kakaiuina@gmail.com
> **Date**: 2026-05-14
> **Status**: Draft (Plan Phase, PDCA Cycle 1)
> **Upstream**: [PRD](../../00-pm/exam-ox-pipeline.prd.md)
> **Related**: [nonsense-quiz-mvp Plan](./nonsense-quiz-mvp.plan.md) (자매 라인, 같은 사이트 다른 서브패스)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 1,700+ PDF 자산이 단순 OX 변환에만 머물러 있고, 수험생은 OX 풀다 모르는 부분에서 풀이→학습 이동 비용이 너무 큼. |
| **Solution** | 기존 `scripts/build_quiz_db.py` Type A/B/C 코어 + **메타데이터 추출 레이어** + **해설 보강 레이어** + **학습 페이지 레이어**. LLM 호출은 외부 API 없이 **Claude Code 세션(Opus)에서 사람-에이전트 협업**으로 처리. |
| **Function/UX Effect** | 한 화면에 문항·즉시 해설·출제범위·태그·관련이론·교과서 챕터(+영상 슬롯). 카테고리 트리(자격증>회차>과목), 오답노트(LocalStorage). 모바일 세로 우선. GitHub Pages 기존 사이트 `/exam/` 서브패스. |
| **Core Value** | 사용자: "OX 풀면 학습 흐름이 안 끊김". 사업: 세무사·회계사 경제학·재정학 Beachhead → Bowling Pin 확장 + 1,700+ PDF 자산 활성화 + 5년 비전 문제DB 트랙. |

---

## Context Anchor

> Auto-generated from Executive Summary + PRD §2. Propagated to Design/Do documents.

| Key | Value |
|-----|-------|
| **WHY** | 검증된 OX 변환 파이프라인 + 1,700+ PDF 위에 "풀이→학습 이동 비용 0" 메타·UI 레이어를 얹어 5년 비전의 문제DB 트랙을 실체화. |
| **WHO** | 1차: 세무사 1차 경제학·재정학 약점자(Persona 정현우, 28세, 자투리 110분/일). 2차: 회계사 1차. 3차: 9급/7급 공무원. |
| **RISK** | (1) Rule-based 메타 추출 정밀도 한계, (2) 깨진 PDF 텍스트, (3) 세션 기반 작업 누적 시 일관성 유지, (4) 하베스터 저작권 명시 누락, (5) 학습 페이지 정보 과다 → UX 무거워짐. |
| **SUCCESS** | 6주 내 — (a) 세무사·회계사 경제학·재정학 OX **누적 400~600문항**(2026~2024 회차 12 PDF 기준), (b) 메타 완성도 ≥80% (출제범위·태그·해설 채워짐), (c) "더 학습하기" 클릭율 ≥35%, (d) inbound 세션 ≥500 (카페·블로그). |
| **SCOPE** | **포함**: 기존 `build_quiz_db.py` 확장, 메타데이터(rule-based + 세션 LLM), 해설 보강(PDF 있으면 그대로 / 없으면 세션 코멘트), 학습 페이지 1종, 카테고리 트리, 오답노트, 모바일 세로, GitHub Pages. **불포함**: 외부 LLM API 자동 호출, 회원·로그인, 마일리지, UGC 문항 제출, YouTube 자동 매칭(슬롯만), 멀티플레이, 강사 영상. |

---

## 1. Overview

### 1.1 Purpose

하베스터 PDF(현 1,700+, 최종 50,000+ 예상)와 검증 완료된 OX 변환 파이프라인 위에, **풀이↔학습 이동 비용을 0에 가깝게** 만드는 학습 메타데이터 + 학습 페이지를 추가한다. MVP는 세무사·회계사 경제학·재정학 2026~2024 회차 12개 PDF로 시작.

### 1.2 Background

상세 컨텍스트는 [PRD §3-§16 참조](../../00-pm/exam-ox-pipeline.prd.md). 핵심:

- **자산**: `data/quiz.db`(192KB SQLite)·`data/quiz/*.json` 으로 세무사 2026 r63 OX 변환 검증 완료
- **파이프라인**: `scripts/build_quiz_db.py` (PDF→OX Type A/B/C 변환, 700줄), `audit_quiz_quality.py`, `export_quiz_json.py`
- **수집**: 크롤러 백그라운드 가동, 구글드라이브에 1,700+ PDF 분류 적재
- **자매 라인**: `nonsense-quiz-mvp` 200문항 정적 게임 완료 (같은 사이트의 메인 페이지)
- **5년 비전**: README의 "문제DB 트랙"과 직결

### 1.3 Related Documents

- PRD: [docs/00-pm/exam-ox-pipeline.prd.md](../../00-pm/exam-ox-pipeline.prd.md)
- 자매 PRD/Plan: [nonsense-quiz-mvp PRD](../../00-pm/nonsense-quiz-mvp.prd.md), [Plan](./nonsense-quiz-mvp.plan.md)
- 5년 비전 인덱스: [../../../README.md](../../../README.md), [01_타임라인_전체.md](../../../01_타임라인_전체.md), [03_군집분석.md](../../../03_군집분석.md)
- 영상 분석 (v2/v3 통찰): [docs/00-pm/reference-video-analysis-2026-05-10.report.md](../../00-pm/reference-video-analysis-2026-05-10.report.md)
- 기존 코드: [scripts/build_quiz_db.py](../../../scripts/build_quiz_db.py)
- 크롤러: [crawler/0gichul_crawler.py](../../../crawler/0gichul_crawler.py)

---

## 2. Scope

### 2.1 In Scope

- [ ] **DB 스키마 v2**: 기존 `questions` 테이블 + 메타 필드(tags JSON, topic, theory, explanation_o, explanation_x, meta_quality) + 신규 `related_videos` 슬롯 테이블 + 신규 `curriculum_map` 테이블
- [ ] **메타데이터 추출 (`scripts/extract_metadata.py` 또는 build_quiz_db.py 통합)** — Rule-based 우선, 세션 LLM은 부족분만 보강
- [ ] **해설 보강 워크플로우** — PDF에 해설 있으면 그대로, 없으면 Claude Code 세션 작업으로 "왜 O / 왜 X" 코멘트 생성
- [ ] **MVP 데이터셋 적재** — 세무사·회계사 경제학·재정학 2026~2024 (~12 PDF, 400~600 문항 예상)
- [ ] **학습 페이지** — `/exam/` 서브패스, 정적 HTML/CSS/JS, 모바일 세로 우선
- [ ] **카테고리 트리 UI** — 자격증(세무사·회계사) → 회차(2026·2025·2024) → 과목(경제학·재정학)
- [ ] **풀이 모드** — O/X → 즉시 정오 + 짧은 해설 + "더 학습하기" 토글
- [ ] **"더 학습하기" 펼침** — 출제범위 / 태그 / 관련 이론 / 교과서 챕터 / 관련 영상(슬롯, MVP는 비어있음)
- [ ] **오답노트** — LocalStorage 기반, 카테고리 트리에 "오답 N건" 노드 표시
- [ ] **GA4 / UTM 추적** — nonsense-quiz-mvp와 동일 측정 ID 재사용
- [ ] **GitHub Pages 배포** — 기존 저장소 동일, `/exam/` 라우트
- [ ] **저작권 명시** — 푸터 "출처: 0gichul.com" + 문항 카드에 원본 PDF 파일명

### 2.2 Out of Scope

- 외부 LLM API 자동 호출 (모든 LLM 작업은 Claude Code 세션 직접 진행)
- 회원가입·로그인·마일리지 적립·결제 (Phase 2+)
- UGC 문항 제출·강사 영상 첨부 (Phase 3+)
- YouTube 영상 자동 매칭 (스키마 슬롯만 마련, 실제 채움은 별도 작업)
- 멀티플레이·50인 OX 서바이벌 (자매 라인 nonsense-quiz-mvp 담당)
- 회계 계산 문제 OX 변환 (기존 build_quiz_db.py 정책대로 스킵)
- 영문 i18n, 다크모드, 데스크톱 전용 레이아웃 (best-effort)
- 자동 크롤러 신규 기능 추가 (현 크롤러 그대로 사용)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 기존 `build_quiz_db.py` Type A/B/C 변환 로직을 그대로 유지하면서 메타 필드 추가 적재 | High | Pending |
| FR-02 | 문항 텍스트에서 출제범위(법조문·교과 챕터) 자동 추출 — Rule-based 정규식 (예: "법 제\d+조", "§\d+") | High | Pending |
| FR-03 | 문항 텍스트에서 태그 추출 — 도메인 키워드 사전(KW) 기반 매칭 (예: "외부효과·코즈정리·시장실패") | High | Pending |
| FR-04 | PDF에 해설 있으면 그대로 적재, 없으면 빈 슬롯으로 두고 `meta_quality` 점수 차감 | High | Pending |
| FR-05 | 빈 해설/메타는 Claude Code 세션 작업으로 보강 — 별도 스크립트 `enrich_session.py` (사용자가 N개 묶어서 요청 가능) | High | Pending |
| FR-06 | DB 스키마 마이그레이션 — 기존 quiz.db 데이터 보존하면서 신규 필드·테이블 추가 | High | Pending |
| FR-07 | 카테고리 트리 UI (자격증 > 회차 > 과목) — 모바일 세로 햄버거 / 데스크톱 사이드바 | High | Pending |
| FR-08 | 풀이 모드 — O/X 클릭 후 즉시 정오 + 짧은 해설 (1~2줄) + "더 학습하기" 토글 | High | Pending |
| FR-09 | "더 학습하기" 펼침 — 출제범위·태그·이론·교과서·관련 영상(빈 슬롯) 5개 영역, 빈 영역은 "준비 중" 뱃지 | High | Pending |
| FR-10 | 오답노트 — LocalStorage 저장, 카테고리 트리에 "오답 N건" 노드, 별도 "오답만 풀기" 모드 | Medium | Pending |
| FR-11 | 학습 페이지 빌드 — `scripts/export_quiz_json.py` 확장하여 `data/exam/*.json` 으로 분할 export | High | Pending |
| FR-12 | 푸터 + 문항 카드에 저작권 표기 (출처: 하베스터, 원본 파일명) | High | Pending |
| FR-13 | GA4 이벤트 — `quiz_answer`, `learn_expand`, `category_select`, `wrong_note_open` | Medium | Pending |
| FR-14 | YouTube 영상 슬롯 — DB에 빈 테이블 + 학습 페이지에 "관련 영상 (준비 중)" 자리 노출 (실제 매칭은 다음 작업) | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 학습 페이지 초기 로드 ≤ 2.5s (3G fast) | Lighthouse Mobile / GA4 LCP |
| Performance | 풀이 → 결과 표시 < 100ms | DevTools Performance |
| Accessibility | 키보드 탭 풀이 가능(O=←, X=→ 또는 1/2) | 수동 검증 |
| Accessibility | 색약 대비 — O(청록 #00C2A8)/X(빨강 #FF5454) 외에 ✓/✗ 아이콘 동시 노출 | 수동 검증 |
| Data Quality | 메타 완성도 ≥80% (출제범위·태그·해설 채워진 문항 비율) | `audit_quiz_quality.py` 확장 |
| Security | XSS 방지 — 문항 본문 textContent 주입, innerHTML 금지 | 코드 리뷰 + CSP |
| Compatibility | iOS Safari 16+ / Android Chrome 110+ / Desktop Chrome·Safari·Firefox 최신 | 수동 검증 |
| Cost | LLM API 호출 0건 (모든 보강은 Claude Code 세션) | API key 미사용 강제 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] DB v2 마이그레이션 스크립트 완성 + 기존 데이터 무손실 검증
- [ ] MVP 데이터셋(세무사·회계사 경제학·재정학 2026~2024) 적재 완료 — 누적 400~600 문항
- [ ] 메타 완성도 ≥80% (audit 스크립트 통과)
- [ ] 학습 페이지 6개 화면 모두 구현(카테고리 트리·풀이·결과·더학습·오답노트·푸터)
- [ ] Lighthouse Mobile Performance ≥ 90
- [ ] GA4 4개 커스텀 이벤트 송출 검증
- [ ] GitHub Pages `/exam/` 라우트 배포 + nonsense `/` 라우트와 충돌 없음
- [ ] 푸터·카드 저작권 표기 검증

### 4.2 Quality Criteria

- [ ] `scripts/audit_quiz_quality.py` 0 critical 오류 (중복·빈 해설은 warning)
- [ ] JS 콘솔 에러 0
- [ ] index.html·script.js 린트 통과 (`scripts/` 디렉토리에 `lint.sh` 신규 또는 nonsense 라인 재사용)
- [ ] 모든 PR 본인 리뷰 (체크리스트: 메타필드 누락·CSP 위반·저작권 누락)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Rule-based 메타 추출 정밀도 부족 | High | High | 1) 도메인 키워드 사전(KW) 과목별 분리 작성 / 2) 빈 메타는 명시적 뱃지 노출 / 3) Claude Code 세션 보강 워크플로우 명확화 |
| 깨진 PDF 텍스트 (OCR 부족·인코딩) | High | Medium | 1) 텍스트 추출 실패 시 스킵 + 별도 `data/pdf_errors.json` 기록 / 2) build_quiz_db.py의 `clean_statement` 보강 보강 |
| 세션 기반 작업 누적 시 일관성 약화 (다른 시점·다른 세션) | Medium | Medium | 1) 메타 작성 가이드 1페이지 (`docs/02-design/features/exam-ox-pipeline.design.md`에 포함) / 2) audit 스크립트에 일관성 검사 룰 추가 |
| 하베스터 저작권 fair use 가정 깨짐 | High | Low | 1) 푸터 + 카드에 출처 명시 / 2) 본문 외 이미지·도표 미사용 / 3) 사이트에 "원본 사이트 방문" 링크 |
| 학습 페이지 정보 과다로 UX 무거움 | Medium | High | 1) 5개 영역 모두 접힌 채 시작 / 2) "더 학습하기" 토글이 1차 펼침 / 3) Lighthouse + 모바일 자체 사용 검증 |
| nonsense-quiz-mvp 라우트 충돌 | Medium | Low | 1) `/exam/` 서브패스 격리 / 2) GA4 measurement ID 동일하되 이벤트 prefix 분리(`exam_*`) / 3) 푸터 상호 링크 |
| MVP 12 PDF로는 데이터셋 너무 작음 | Medium | Medium | 1) MVP 후 즉시 회계사·경영지도사 경제학 추가 (Phase 2 trigger) / 2) PRD success criteria 6주 평가 기준 |
| 크롤러 가동 중이라 작업 충돌 | Low | Low | 1) 크롤러 SQLite는 `crawler/state/crawler.db`, 본 프로젝트 DB는 `data/quiz.db` (분리됨) / 2) Drive 파일 read-only 사용 |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `data/quiz.db` SQLite | DB Schema | `questions` 테이블에 6개 메타 필드 추가, 신규 `related_videos`·`curriculum_map` 테이블 |
| `scripts/build_quiz_db.py` | Script | 메타 추출 로직 통합 (Type A/B/C 변환 후 메타 채움 단계 추가) |
| `scripts/export_quiz_json.py` | Script | 학습 페이지용 JSON export 추가 (`data/exam/*.json`) |
| `index.html` / `script.js` / `style.css` | Frontend | 분리 — nonsense는 `/index.html` 유지, 신규 `/exam/index.html` + 자체 `script.js`·`style.css` |
| `.bkit-memory.json` / `.bkit/state/pdca-status.json` | Config | exam-ox-pipeline 추적 정보 추가 |
| 신규 `scripts/extract_metadata.py` | Script | 메타 추출 룰셋 (정규식 사전·키워드 사전·도메인 사전) |
| 신규 `scripts/enrich_session.py` | Script | 세션 LLM 작업 위한 입출력 헬퍼 (빈 메타 문항 추출 → 마크다운 → 사용자 응답 후 DB 적재) |
| 신규 `data/dict/` | Data | 과목별 키워드 사전 JSON (경제학·재정학 등) |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| `data/quiz.db` | READ | `scripts/audit_quiz_quality.py` | Needs verification — 신규 필드 nullable로 추가하면 무손상 |
| `data/quiz.db` | READ | `scripts/export_quiz_json.py` | Needs verification — 동일 |
| `data/quiz/*.json` | READ | (현재는 미사용, nonsense는 자체 questions_v1.csv 사용) | None |
| `index.html` | (browser) | nonsense-quiz-mvp main page | None — 분리된 서브패스 |
| GitHub Pages 빌드 | DEPLOY | (디폴트 정적) | Needs verification — `_config.yml` 없으면 모든 폴더 deploy되므로 OK |
| GA4 measurement ID | EVENT | nonsense `script.js` | None — 이벤트 prefix 분리 |

### 6.3 Verification

- [ ] 마이그레이션 후 기존 questions 행 수 유지 + 신규 필드 null로 채워짐
- [ ] `audit_quiz_quality.py` 신규 필드에 graceful 처리(없으면 warning, 있으면 검사)
- [ ] nonsense 라우트(`/`)와 exam 라우트(`/exam/`) 충돌 없음
- [ ] CSP 정책 — 신규 외부 도메인 추가 없음 (YouTube embed는 MVP에 미포함, slot만)

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure (`scripts/`, `data/`, `index.html`) | Static sites, content sites | ☑ |
| **Dynamic** | Feature-based modules, BaaS integration | Web apps with backend | ☐ |
| **Enterprise** | Strict layer separation, DI | High-traffic systems | ☐ |

**Selected**: **Starter** — nonsense-quiz-mvp와 동일. 정적 사이트, BaaS·서버 미사용.

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | Vanilla JS / React / Vue / Astro | **Vanilla JS** | nonsense와 동일 스택, 학습 곡선 0, GitHub Pages 호환 |
| State Management | Module 객체 / LocalStorage | **Module 객체 + LocalStorage(오답노트만)** | 회원·DB 없음, 진척률은 세션 내 |
| API Client | fetch | **fetch + 정적 JSON** | `data/exam/*.json` 정적 fetch, CDN 캐시 |
| Form Handling | (해당 없음) | — | 회원·검색 입력 없음 |
| Styling | Vanilla CSS / Tailwind | **Vanilla CSS** | nonsense 라인과 동일, 동일 토큰 재사용(`style.css` import 분리) |
| Testing | Jest / Vitest / 수동 | **수동 + audit 스크립트** | MVP는 수동 + `audit_quiz_quality.py` |
| Backend | BaaS / Server / 없음 | **없음** | 정적 사이트 |
| DB | SQLite (빌드시) → JSON | **SQLite 빌드 + 정적 JSON 배포** | `data/quiz.db`는 git LFS X (작음), JSON만 정적 배포 |
| LLM | Claude API / 외부 모델 / **세션** | **Claude Code 세션 (Opus)** | 사용자 명시: API 비용 0, 새 PDF 들어오면 새 작업 요청 |
| Meta 추출 | Rule-based / LLM / 하이브리드 | **Rule-based 우선, 세션 보강** | 비용 0 + 정밀도, 빈 곳만 세션 작업 |

### 7.3 Clean Architecture Approach

```
Selected Level: Starter (정적 사이트, BaaS 없음)

Folder Structure (proposed):
OX퀴즈게임/
├── index.html              ← nonsense-quiz-mvp 메인 (기존 유지)
├── script.js               ← nonsense 게임 로직 (기존 유지)
├── style.css               ← nonsense 스타일 (기존 유지)
├── exam/                   ★ 신규 — exam-ox-pipeline 서브패스
│   ├── index.html          학습 페이지 (카테고리 트리 + 풀이 + 더학습)
│   ├── exam.js             학습 페이지 로직 (state·라우팅·LocalStorage)
│   └── exam.css            학습 페이지 스타일 (nonsense 토큰 재사용)
├── data/
│   ├── quiz.db             SQLite (빌드 시, git 제외 가능)
│   ├── quiz/               nonsense JSON (기존 유지)
│   ├── exam/               ★ 신규 — 학습 페이지용 JSON (카테고리별 분할)
│   │   ├── _index.json     카테고리 트리 메타
│   │   ├── tax-2026-r63-economics.json
│   │   ├── tax-2026-r63-finance.json
│   │   └── ...
│   ├── dict/               ★ 신규 — 과목별 키워드 사전 JSON
│   │   ├── economics.json
│   │   ├── finance.json
│   │   └── ...
│   └── seeds/              (기존 유지)
├── scripts/
│   ├── build_quiz_db.py    (확장 — 메타 추출 통합)
│   ├── extract_metadata.py ★ 신규 (rule-based 메타 추출)
│   ├── enrich_session.py   ★ 신규 (빈 메타 → 마크다운 → 세션 응답 → DB 적재)
│   ├── audit_quiz_quality.py (확장 — 메타 완성도 검사)
│   ├── export_quiz_json.py (확장 — exam 카테고리별 분할)
│   └── migrate_db_v2.py    ★ 신규 (v1 → v2 스키마 마이그레이션)
└── docs/                   (PDCA 문서)
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] `CLAUDE.md` (글로벌 user-scope) 사용 중
- [x] `README.md` 5년 인덱스
- [ ] `docs/01-plan/conventions.md` 없음 (Plan Phase Phase 2 도입 검토)
- [ ] `.eslintrc.*` 없음 — Vanilla JS 단순 코드라 ESLint 도입 후순위
- [ ] `.prettierrc` 없음 — 수동 포맷팅 (MVP)
- [ ] `tsconfig.json` 없음 — JS only

### 8.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | nonsense 라인 kebab-case + snake_case 혼용 | exam/ 폴더는 kebab-case 통일, scripts/는 snake_case 유지 | High |
| **Folder structure** | nonsense 라인 정의됨 | `exam/`·`data/exam/`·`data/dict/` 신규 표준 명시 (§7.3 참조) | High |
| **DB column 명명** | snake_case | 신규 메타 필드도 snake_case 통일 (tags / topic / theory / explanation_o / explanation_x / meta_quality) | High |
| **JSON 구조** | nonsense는 단일 JSON | exam은 카테고리별 분할 + `_index.json` 메타 | High |
| **저작권 표기** | nonsense에 없음 | 푸터 + 카드 저작권 표기 표준 (PDF 원본 파일명 추적) | High |
| **GA4 이벤트 prefix** | nonsense는 prefix 없음 | exam 이벤트는 `exam_` prefix (예: `exam_quiz_answer`) | Medium |

### 8.3 Environment Variables Needed

| Variable | Purpose | Scope | To Be Created |
|----------|---------|-------|:-------------:|
| (없음) | 외부 API 미사용, 모든 자산 정적 | — | — |

> **참고**: GA4 measurement ID는 nonsense `script.js`에 인라인 — exam에서도 동일 ID 재사용, 이벤트 prefix로 분리.

### 8.4 Pipeline Integration

9-phase Development Pipeline의 일부만 적용 (Starter):

| Phase | Status | Document Location | Note |
|-------|:------:|-------------------|------|
| Phase 1 (Schema) | ☑ inline | `docs/02-design/features/exam-ox-pipeline.design.md` §3 (예정) | DB schema v2를 Design에 포함 |
| Phase 2 (Convention) | ☐ skip | — | MVP는 §8.2의 인라인 컨벤션으로 충분 |
| Phase 3 (Mockup) | ☐ skip | — | 학습 페이지는 nonsense 토큰 재사용, 별도 모킹 불필요 |
| Phase 4 (API) | n/a | — | 정적 사이트, API 없음 |
| Phase 5 (Design System) | ☑ reuse | — | nonsense `style.css` 토큰 재사용 |
| Phase 6 (UI Integration) | ☑ inline | Design §5 | 학습 페이지 컴포넌트 A~G |
| Phase 7 (SEO + Security) | ☑ inline | Design §7 | CSP 동일, meta tags + sitemap |
| Phase 8 (Review) | ☑ Check phase | `docs/03-analysis/exam-ox-pipeline.analysis.md` | PDCA Check phase |
| Phase 9 (Deploy) | ☑ GitHub Pages | (자동) | 기존 워크플로우 재사용 |

---

## 9. Confirmed Decisions (Plan Phase Checkpoint 답변 정리)

### 사용자 확정 사항 (2026-05-14)

| Q | 사용자 결정 | Plan 반영 |
|---|---|---|
| Q1 프런트·배포 | **정적 HTML/CSS/JS + GitHub Pages** (`/exam/` 서브패스) | §7.2·§7.3 반영 |
| Q3 LLM 전략 | **외부 API 호출 0, Claude Code 세션(Opus) 직접 작업**. 새 PDF 들어오면 새 작업 요청 | §3.2 Cost·§2.2·§7.2 LLM 반영. 신규 `enrich_session.py`로 마크다운 IO 정형화 |
| Q4 MVP 소재 | **세무사·회계사 경제학·재정학 2026~2024 회차** (~12 PDF, 400~600 문항 예상) | §2.1·§4.1·§5 반영 |
| Q5 YouTube | MVP 미구현. **분류 슬롯만 미리 마련** | §2.1 FR-14·§7.3 `related_videos` 테이블·§2.2 |

### 합리적 디폴트 (Plan 진행하면서 자동 결정 — Design에서 미세조정 가능)

| Open Q | 디폴트 | 이유 |
|---|---|---|
| Q2 도메인 | GitHub Pages 기본 도메인 (저장소 URL) | 비용 0, 추후 커스텀 가능 |
| Q6 메타 빈칸 | "준비 중" 뱃지 노출 + `meta_quality` 점수 노출 X(내부만) | 신뢰 확보 + 단순성 |
| Q7 메타 검수 빈도 | 즉시 (audit 스크립트 = 빌드 직전 1회) | 세션 기반이라 batch 개념 불필요 |
| Q8 오답노트 UI | 카테고리 트리에 "오답 N건" 노드 + "오답만 풀기" 모드 | 한 화면 일관성 + 별도 페이지 없이 단순 |
| Q9 저작권 | 푸터 "출처: 0gichul.com" + 카드 우측 하단 "원본: 2024-r62-경제학.pdf" | 명확한 fair use 표시 |
| Q10 Beachhead 확장 | 6주 후 §4 success criteria 충족 시 회계사·경영지도사 경제학으로 확장 trigger | PRD 명시 기준 준수 |

---

## 10. Next Steps

1. [ ] `/pdca design exam-ox-pipeline` — Design 문서 작성 (DB schema v2 ER + 학습 페이지 컴포넌트 A~G + 데이터 흐름 + 3 Architecture Options 비교 후 선택)
2. [ ] Design에서 메타 추출 룰셋 명세 (정규식·키워드 사전 구조)
3. [ ] Design에서 학습 페이지 와이어프레임 (모바일 세로 6화면)
4. [ ] Design에서 `enrich_session.py` 입출력 마크다운 포맷 정의
5. [ ] Plan/Design 통과 후 → `/pdca do exam-ox-pipeline`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-14 | Initial draft — PRD §17 Open Questions 중 핵심 4개 사용자 확정 + 6개 합리적 디폴트 | kakaiuina@gmail.com (with Claude Code Opus) |
