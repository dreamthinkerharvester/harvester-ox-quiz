# nonsense-quiz-mvp Planning Document

> **Summary**: 정적 HTML/CSS/JS 1페이지로 구현하는 200문항 넌센스 OX 퀴즈 웹게임 — SNS funnel 종착 랜딩
>
> **Project**: OX퀴즈게임
> **Version**: 0.1.0 (initial)
> **Author**: kakaiuina@gmail.com
> **Date**: 2026-05-09
> **Status**: Draft (Plan Phase, PDCA Cycle 1)
> **Upstream**: [PRD](../../00-pm/nonsense-quiz-mvp.prd.md)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 5년 누적 OX 비전이 시장 검증된 적 없고, 운영 중인 SNS(유튜브숏츠/틱톡/릴스) OX 콘텐츠가 랜딩 종착지 부재로 이탈. |
| **Solution** | 정적 1페이지 HTML/CSS/JS 웹게임. 200문항 풀에서 라운드당 30문항 셔플. 큰 둥근 O(청록)/X(빨강) + 라이프 3 + 이모지 군중 분할 연출 + "내가 짱!" 종료 화면. GitHub Pages 배포. |
| **Function/UX Effect** | 모바일 세로 우선 1분 도파민 게임. GA4로 SNS UTM 추적 + 종료 시 캐주얼 자취생 톤 공유 문구 자동 복사. 무회원·무계정·무DB. |
| **Core Value** | 사용자: "1분 만에 풀고 카톡 공유". 사업: SNS funnel 첫 종착지 + 카테고리 확장 전 메커니즘 검증 + 5년 비전 시장 진입점. |

---

## Context Anchor

> Auto-generated from Executive Summary + PRD §2. Propagated to Design/Do documents.

| Key | Value |
|-----|-------|
| **WHY** | 5년 누적 OX 비전의 시장검증 진입점 + SNS funnel 랜딩 종착지 부재 해결 |
| **WHO** | 1차: SNS에서 OX 콘텐츠 본 자취생/20대 (페르소나 박지원, 24세). 2차/3차: 자격증 준비생, 대학교수 |
| **RISK** | (1) 200문항 자체제작 품질 불균질, (2) MVP 단순성 vs 재방문 동기 부족, (3) 정적 사이트 분석 데이터 제약, (4) 디자인 자산 저작권 |
| **SUCCESS** | 4주 내 — (a) 평균 세션 ≥3분, (b) 완주율 ≥40%, (c) 공유 ≥50건, (d) UTM 3채널(YT/IG/TikTok) 추적 가능, (e) 모바일 비중 ≥70% |
| **SCOPE** | **포함**: OX 200문항(30개 셔플), 라이프 3, Q.번호, 정답·오답 즉시 피드백, "내가 짱!" 종료 화면, 공유(WebShare API + 카톡 fallback), 다시풀기, GA4. **불포함**: 회원·로그인·DB·마일리지·카테고리 UI·UGC·멀티·결제·다국어·다크모드·자취생카페 링크 |

---

## 1. Overview

### 1.1 Purpose

5년간(2021-2025) 축적된 OX 게임 비전(마일리지 경제·UGC·강사 참여·멀티플레이 등)을 시장에 처음 던져 검증하는 **최소 단위 진입점** 구현.

부수적으로, 이미 운영 중인 유튜브숏츠/틱톡/인스타릴스 OX 콘텐츠가 자취생 네이버카페 외 다른 종착지가 없어 트래픽이 새는 funnel 결손을 채움.

### 1.2 Background

상세 컨텍스트는 [PRD §3-§10 참조](../../00-pm/nonsense-quiz-mvp.prd.md). 핵심:
- **Beachhead**: SNS에서 OX 콘텐츠 본 자취생/20대 (4-criteria 16/20)
- **차별점**: 퀴즈스틱맨식 시각적 군중심리 연출을 단순화 형태(이모지·CSS 애니)로 1차 구현
- **장기 비전**: 카테고리 확장(자격증·고시·교양) → 회원/마일리지 → UGC → 멀티플레이

### 1.3 Related Documents

- **PRD**: `docs/00-pm/nonsense-quiz-mvp.prd.md` (321 lines, 14 sections)
- **디자인 레퍼런스**: `_refs/screenshots-description.md` (퀴즈스틱맨 5장 스크린샷 텍스트 명세 + 디자인 토큰)
- **회의자료**: `01_타임라인_전체.md` (5년 누적), `02_원본전문/2025-08-22_정책회의.md` (마일리지 경제 전체 비전)
- **데이터**: `data/questions_v1.csv` (헤더 + 예시 3행, 200문항은 사용자가 추가 예정)

---

## 2. Scope

### 2.1 In Scope (1차 MVP)

- [ ] 200문항 CSV 로드 + 클라이언트 사이드 파싱 (`fetch('data/questions_v1.csv')`)
- [ ] 라운드 시작 시 200문항 풀에서 **무작위 30문항 셔플** 후 출제
- [ ] 인트로 화면 ("준비하시고~" 모티프 — 이모지 군중 + 큰 외곽선 타이포)
- [ ] 게임 진행 화면:
  - 상단 HUD: Q.번호 (1/30) · 라이프 ❤️×3 · 점수
  - 문제 텍스트 영역
  - 좌/우 2분할 캐릭터 군중 (이모지 ~5개씩)
  - 큰 둥근 O(청록 `#29b6f6`) / X(빨강 `#ef5350`) 버튼 (지름 35vw)
- [ ] 답변 인터랙션:
  - 정답 시: 반대편 이모지 추락 애니메이션 (CSS `transform: translateY(100vh)` 0.5s)
  - 오답 시: 자기 이모지 흔들림 (`shake` keyframes) + 라이프 -1
  - 다음 문제 자동 이동 (1초 후) + 해설 토스트 1초 노출
- [ ] 라이프 0 또는 30문항 완주 시 종료
- [ ] 종료 화면 ("내가 짱!"):
  - 노란 방사형 배경 (CSS radial-gradient)
  - 점수 표시 (예: "30문제 중 28개 맞춤 / 라이프 3개 남음")
  - **공유 버튼** (WebShare API + 카톡 링크 복사 fallback) — 캐주얼 자취생 톤 자동 문구
  - **다시 풀기 버튼** (라운드 재시작)
- [ ] **GA4 + UTM** 통합:
  - 측정 ID 환경변수 (HTML `<meta>` 또는 인라인 `<script>`)
  - 5개 이벤트: `game_start`, `answer_o`, `answer_x`, `game_end` (점수 dimension), `share_click`
  - UTM 파라미터 자동 인식 (`utm_source`, `utm_medium`, `utm_campaign`)
- [ ] **만화체 한글 폰트**: Google Fonts CDN — `Black Han Sans` (제목용) + `Jua` (본문용)
- [ ] 모바일 세로 9:16 우선. 데스크톱은 best-effort (vmin 기반 반응형)
- [ ] **단일 라이트 테마**만 (다크모드 비대응)
- [ ] GitHub Pages 배포 (커스텀 도메인 미사용 — `{user}.github.io/ox-quiz` 형태)

### 2.2 Out of Scope (Phase 2+로 명확히 분리)

- 회원가입, 로그인, OTP 인증 (Phase 2B)
- 마일리지 경제 — 적립/사용/소멸 (Phase 2B)
- 카테고리 선택 UI — 자격증·고시·교양 분기 (Phase 2A)
- UGC 문제 제출·검토 (Phase 3)
- 멀티플레이어·실시간 대전 (Phase 4)
- 강사 참여형 OX 챌린지 (Phase 3)
- 백엔드 DB·서버 (Phase 2B 마이그레이션 시 Next.js + bkend/Postgres)
- 결제·인앱결제·광고 (Phase 4)
- 다국어 (모든 Phase 보류)
- 다크 모드 테마 (필요 시 별도 검토)
- 자취생 네이버카페 외부 링크 노출 (사용자 명시 제외)
- BGM·SFX 사운드 (1차 무음 정책)
- 캐릭터 선택·커스터마이즈 (Phase 2A 이후 가능)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | CSV 200문항 비동기 로드 + 파싱 (id/question/answer/explanation 4필드) | High | Pending |
| FR-02 | 라운드 시작 시 200문항에서 무작위 30문항 셔플 (Fisher-Yates) | High | Pending |
| FR-03 | OX 이지선다 입력 (탭/클릭 한 번) | High | Pending |
| FR-04 | 정답 시 반대편 이모지 추락 + 자기편 만세 애니메이션 (CSS only) | High | Pending |
| FR-05 | 오답 시 자기 이모지 흔들림 + 라이프 -1 + 해설 토스트 1초 | High | Pending |
| FR-06 | 라이프 0 또는 30문항 완주 시 종료 화면 전이 | High | Pending |
| FR-07 | 종료 화면: 점수 표시 + WebShare API 공유 + 다시풀기 버튼 | High | Pending |
| FR-08 | WebShare 미지원 브라우저는 카톡 링크 복사 fallback (clipboard.writeText) | High | Pending |
| FR-09 | GA4 측정 통합 + 5개 이벤트 발화 | High | Pending |
| FR-10 | UTM 파라미터 자동 인식 후 GA4 dimension에 매핑 | High | Pending |
| FR-11 | 인트로 화면 → 게임 → 종료 화면 라우팅 (해시 또는 단순 view 토글) | Medium | Pending |
| FR-12 | 일시정지(‖) 버튼: 타이머·게임 정지 (단, 타이머 1차 미적용 시 보류) | Low | Pending |
| FR-13 | 모바일 세로 9:16 반응형 레이아웃 (CSS vmin 기반) | High | Pending |
| FR-14 | 만화체 한글 폰트 적용 (Black Han Sans / Jua) | Medium | Pending |
| FR-15 | 게임 진행률 시각화 (Q.X / 30 또는 progress bar) | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| **Performance** | 첫 페인트(FCP) < 2초 (3G 시뮬, GitHub Pages) | Lighthouse + WebPageTest |
| **Performance** | CSV 200문항(~30KB) 로드 후 게임 시작 < 1초 | DevTools Performance |
| **Compatibility** | 모바일 5종 패스: iPhone SE, iPhone 12/14, Galaxy S20/S23 | 수동 테스트 |
| **Compatibility** | 데스크톱 best-effort: Chrome/Safari/Firefox 최신 | 수동 테스트 |
| **Accessibility** | OX 버튼 키보드 접근 가능 (Tab + Enter) | 수동 키보드 테스트 |
| **Accessibility** | WCAG 2.1 AA 컬러 대비 (청록/빨강 버튼 + 흰 텍스트) | Chrome DevTools 색상 대비 |
| **SEO/Sharing** | OG meta 태그 (og:title, og:image, og:description) — SNS 미리보기 | Facebook Sharing Debugger |
| **Privacy** | 쿠키·개인정보 수집 없음 명시 (GA4 anonymizeIp 활성) | 수동 검수 |
| **Legal** | 퀴즈스틱맨 자산 직접 복제 금지 — 컬러/메커니즘 컨셉만 | 코드 리뷰 시 자체 인증 자산만 사용 확인 |

---

## 4. Success Criteria

### 4.1 Definition of Done (코드 완성 기준)

- [ ] FR-01~FR-15 중 High 12개 모두 구현 (Medium 2개·Low 1개는 best-effort)
- [ ] `index.html`, `style.css`, `script.js`, `data/questions_v1.csv` 4개 파일 + `_refs`·`docs` 보조
- [ ] GitHub Pages에 정상 배포 (HTTPS, 모바일에서 게임 가능)
- [ ] CSV 200문항 사용자가 채워둠 + 초기 5명 샘플 풀이 검수 통과
- [ ] GA4 5개 이벤트 모두 실시간 보고서에 기록되는 것 검증
- [ ] 모바일 5종에서 수동 게임 1회 완주 (Critical 호환성)
- [ ] OG 미리보기 카톡 공유 시 정상 노출

### 4.2 Quality Criteria (품질 기준)

- [ ] 코드: HTML/CSS/JS 합쳐 < 1500 LOC (단순성 강제)
- [ ] Lint: HTML W3C 검증 0 에러, CSS 검증 0 에러, JS Strict mode + ESLint 추천 룰 0 에러
- [ ] Lighthouse 모바일: Performance ≥ 85, Accessibility ≥ 90, Best Practices ≥ 90, SEO ≥ 90
- [ ] 의존성: 외부 npm 패키지 0개 (Google Fonts CDN만 허용)

### 4.3 Business Success (PRD §7과 일치)

- [ ] **SC1**: 출시 4주 누적 평균 세션 ≥ 3분
- [ ] **SC2**: 게임 완주율(시작→종료) ≥ 40%
- [ ] **SC3**: 공유 발생 ≥ 50건
- [ ] **SC4**: UTM 3채널(youtube/instagram/tiktok) 트래픽 분리 추적 가능
- [ ] **SC5**: 모바일 트래픽 비중 ≥ 70%

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| 200문항 자체제작 품질 불균질 | High | Medium | 출시 전 5명에게 50문항 샘플 풀이 시켜 명확한 오류·애매한 답 식별 후 사용자 수정. CSV에 `id` 보존해 추후 교체 추적. |
| 정적 사이트 분석 데이터 한계 | Medium | High | GA4 5개 이벤트 + UTM dimension으로 SC1~5 모두 측정 가능 설계. 추후 부족 시 Plausible 추가 가능. |
| 퀴즈스틱맨 디자인 자산 복제 의혹 | Very High | Low | 일러스트 일체 사용 금지, 이모지(유니코드)와 자체 SVG만. 컬러 토큰·레이아웃 컨셉만 차용. 코드 리뷰 시 명시적 자체 인증. |
| MVP 너무 단순해 재방문 동기 부족 | Medium | Medium | 매번 30문항 셔플로 풀이 경험 차별화. 종료 화면 공유 문구가 캐주얼해 재공유 유발. SC2 < 40% 시 iteration. |
| 모바일 다양 기기 호환성 | Medium | Medium | iPhone SE/12/14, Galaxy S20/S23 5종 사전 테스트 필수. CSS vmin 기반 절대 의존 회피. |
| OG 미리보기 카톡 노출 실패 | Medium | Medium | 1080×1080 OG 이미지 자체 제작 + Facebook Sharing Debugger 사전 검증. |
| GitHub Pages 배포 단절 | Low | Low | `gh-pages` 브랜치 자동 배포, push 후 5분 내 반영. 백업으로 Netlify drop도 대안. |
| 200문항 작성 지연으로 출시 지연 | Medium | Medium | 사용자가 30~50문항 분할 작업 가능하게 CSV 구조 분리. 코드는 200개 미만에서도 동작 (단, < 30개일 때 경고). |

---

## 6. Impact Analysis

> **Greenfield 프로젝트** — 기존 코드/리소스 없음. 본 섹션은 **N/A** 처리하되, 향후 Phase 2A 카테고리 확장 시 본 Plan에 영향 항목을 역참조하기 위한 기준점으로 보존.

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| (Greenfield) | — | 본 PDCA 사이클은 신규 생성만 발생. 기존 변경 없음. |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| (N/A) | — | — | None — Greenfield |

### 6.3 Verification

- [x] N/A — Greenfield 확인 완료
- [ ] 향후 Phase 2A에서 본 1차 코드를 변경할 때 이 섹션 다시 채울 것

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure (`index.html`, `style.css`, `script.js`) | Static sites, portfolios, landing pages | ☑ **(1차 MVP)** |
| **Dynamic** | Feature-based modules, BaaS integration (bkend.ai) | Web apps with backend, SaaS MVPs | ☐ (Phase 2B+) |
| **Enterprise** | Strict layer separation, DI, microservices | High-traffic systems | ☐ |

> **레벨 사용 메모**: bkit 프로젝트 메타데이터는 `Dynamic`으로 설정되어 있으나, 1차 MVP는 의도적으로 Starter-급 단순 구조로 구현. Phase 2B 마이그레이션 시 Dynamic 구조(`src/features/`, `src/services/`, `bkend.ts`)로 재편 예정.

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | Next.js / React / Vue / Vanilla | **Vanilla HTML/CSS/JS** | 사용자 지정 A안. 외부 의존성 0, GitHub Pages 직배포, 학습·디버깅 가장 단순 |
| State Management | Context / Zustand / Redux / 메모리 | **단일 in-memory `state` 객체** | 페이지 전환 없는 SPA-라이트. localStorage는 미사용(개인정보 회피) |
| API Client | fetch / axios / react-query | **fetch (네이티브)** | CSV 1회 로드 외 API 없음 |
| Form Handling | react-hook-form / formik / native | **N/A** | 폼 없음 (OX 클릭만) |
| Styling | Tailwind / CSS Modules / styled-components / **Vanilla CSS** | **Vanilla CSS + CSS Variables** | 외부 의존성 0. 디자인 토큰은 `:root` CSS 변수로 |
| Testing | Jest / Vitest / Playwright / Manual | **Manual (모바일 5종 + 데스크톱 3종)** | 1차 MVP 단순성 우선. Phase 2A부터 Playwright 도입 |
| Backend | BaaS (bkend.ai) / Custom Server / Serverless / **None** | **None (정적)** | 200문항 CSV 클라이언트 로드만 |
| 분석 | GA4 / Plausible / 없음 | **GA4 + UTM** | 사용자 확정. SC4 채널 추적 충족 |
| 폰트 | 시스템 / Google Fonts / 자체 | **Google Fonts CDN (Black Han Sans + Jua)** | 만화체 한글 무료 라이선스 |
| 호스팅 | GitHub Pages / Netlify / Vercel / 자체 | **GitHub Pages** | 사용자 확정. 무료 + HTTPS 자동 |

### 7.3 Clean Architecture Approach

```
Selected Level: Starter (1차 MVP)

Folder Structure (이번 PDCA 사이클 생성 예정):
OX퀴즈게임/
├── index.html              # 진입점 (인트로 + 게임 + 종료 view 토글)
├── style.css               # 디자인 토큰 + 레이아웃 + 애니메이션
├── script.js               # 게임 로직 (load → shuffle → loop → end)
├── data/
│   └── questions_v1.csv    # 200문항 데이터 (사용자 작성)
├── assets/
│   ├── og-image.png        # 1080×1080 SNS 미리보기 (자체 제작)
│   └── favicon.svg         # 파비콘
├── _refs/                  # 디자인 레퍼런스 (이미 존재)
│   └── screenshots-description.md
└── docs/                   # PDCA 문서
    ├── 00-pm/nonsense-quiz-mvp.prd.md
    ├── 01-plan/features/nonsense-quiz-mvp.plan.md  ← 본 문서
    ├── 02-design/features/nonsense-quiz-mvp.design.md  (다음)
    ├── 03-analysis/nonsense-quiz-mvp.analysis.md  (이후)
    └── 04-report/features/nonsense-quiz-mvp.report.md  (마지막)
```

> **Phase 2B 진입 시 마이그레이션**: 위 구조를 `src/features/quiz/`, `src/lib/bkend.ts`, `src/app/api/questions/route.ts` 등 Dynamic 구조로 재편. 현재 vanilla JS 게임 로직은 React 컴포넌트로 포팅.

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [ ] `CLAUDE.md` 존재 — **부재** (사용자 전역 `~/.claude/CLAUDE.md` 만 있음, 프로젝트 로컬 신규 작성 보류)
- [ ] `docs/01-plan/conventions.md` (Phase 2 산출) — **부재**
- [ ] `CONVENTIONS.md` — **부재**
- [ ] ESLint configuration — **불필요** (외부 의존성 0 정책)
- [ ] Prettier configuration — **선택** (도입 시 `.prettierrc` 단순 설정)
- [ ] TypeScript configuration — **불필요** (Vanilla JS만)

### 8.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | 없음 | `kebab-case` 파일명, `camelCase` JS 변수, `BEM` CSS 클래스 (`.game__button--primary`) | High |
| **Folder structure** | 없음 | 위 §7.3 정의대로 (root 평탄 구조 + data/assets/docs) | High |
| **Import order** | 없음 | JS는 파일 1개라 N/A. CSS는 `@import` 미사용 (단일 파일) | Low |
| **Environment variables** | 없음 | GA4 측정 ID는 `<script>` 인라인 (정적 사이트 한계) — 코드에 직접 박음 | Medium |
| **Error handling** | 없음 | CSV 로드 실패 시 `try/catch` + 사용자에게 친근한 에러 화면 ("문제를 불러올 수 없어요 😢 새로고침 해주세요") | High |

### 8.3 Environment Variables Needed

| Variable | Purpose | Scope | To Be Created |
|----------|---------|-------|:-------------:|
| `GA4_MEASUREMENT_ID` | GA4 측정 ID (예: `G-XXXXXXXXXX`) | Client (HTML 인라인) | ☑ — 사용자가 GA4 속성 생성 후 발급 |
| `OG_BASE_URL` | OG meta 절대 URL (예: `https://{user}.github.io/ox-quiz/`) | HTML `<meta>` | ☑ — 배포 도메인 확정 후 박음 |

> **메모**: 정적 사이트는 빌드 환경변수 주입이 어려우므로 두 값 모두 HTML/JS에 직접 기재. Phase 2B Next.js 마이그 시 `process.env.NEXT_PUBLIC_*` 로 전환.

### 8.4 Pipeline Integration

bkit 9-phase 개발 파이프라인 별도 진입은 본 PDCA 사이클에서 **생략**. 1차 MVP는 단일 사이클로 충분.

| Phase | Status | Document Location | Note |
|-------|:------:|-------------------|------|
| Phase 1 (Schema) | ☐ | (생략) | CSV 4필드 단순 — 별도 schema doc 불필요 |
| Phase 2 (Convention) | ☐ | (생략) | §8.2 표가 미니 conventions 역할 |
| Phase 3 (Mockup) | △ | `_refs/screenshots-description.md` | 퀴즈스틱맨 텍스트 명세로 갈음 |
| Phase 4 (API) | ☐ | (생략) | 백엔드 없음 |
| Phase 5 (Design System) | △ | Plan §7.3 + Design 단계에서 토큰 확정 | |
| Phase 6 (UI Integration) | ☐ | Do 단계에서 통합 | |
| Phase 7 (SEO/Security) | △ | NFR §3.2 + Risk §5에 흡수 | |
| Phase 8 (Review) | ☐ | Check 단계 (`/pdca analyze`)에서 통합 | |
| Phase 9 (Deployment) | ☐ | GitHub Pages 단순 배포 | Do 단계 마지막 |

---

## 9. Confirmed Decisions (Plan Phase Checkpoint 답변 정리)

> Plan Phase Checkpoint 1·2에서 사용자에게 확정받은 6가지 의사결정.

| # | Question | Selected | 근거/메모 |
|---|----------|----------|-----------|
| 1 | 분석 도구 | **GA4 + UTM** | SC4 채널 추적 충족, 무료, 한국 사용자 추적 강함 |
| 2 | 배포 도메인 | **GitHub Pages 기본** (`{user}.github.io/ox-quiz`) | 무료·즉시·HTTPS. 1차 MVP에 충분 |
| 3 | 200문항 출제 방식 | **전체 풀에서 매번 30문항 셔플** | 1분 도파민 페르소나 적합. 재방문 시 다른 조합 |
| 4 | 자취생 카페 링크 노출 | **노출 안 함 (삭제)** | 1차 MVP 단순성 절대 우선. funnel 효과는 데이터로 검증 후 2차에서 |
| 5 | 종료 화면 공유 문구 톤 | **캐주얼 자취생 톤** | 페르소나 박지원과 일치. 점수 자동 삽입 |
| 6 | 다크/라이트 테마 | **단일 라이트 테마** | 만화풍 + 1차 단순화. prefers-color-scheme 미대응 |

---

## 10. Next Steps

1. [x] **PRD** 작성 — `docs/00-pm/nonsense-quiz-mvp.prd.md` ✅
2. [x] **Plan** 작성 — `docs/01-plan/features/nonsense-quiz-mvp.plan.md` ✅ (본 문서)
3. [ ] **Design** 작성 — `/pdca design nonsense-quiz-mvp` → `docs/02-design/features/nonsense-quiz-mvp.design.md`
   - 3가지 아키텍처 옵션 비교 (Plan §7.3 기반)
   - 디자인 토큰 확정 (`_refs/screenshots-description.md` §"추출된 디자인 토큰" 검토)
   - 게임 상태 머신 명세 (intro → game → end → reset)
   - 200문항 CSV 스키마 검증 규칙
   - GA4 5개 이벤트 정확한 dataLayer 페이로드
   - 모바일 5종 호환성 매트릭스
4. [ ] **Do** 단계 — 사용자가 200문항 작성 + Claude가 코드 구현
5. [ ] **Check** 단계 — Gap 분석 + 수동 모바일 테스트
6. [ ] **Report** + GitHub Pages 배포

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-09 | 초기 Plan 문서. PRD + 6 Open Questions 답변 통합 | bkit:pdca plan |
