# nonsense-quiz-mvp Design Document

> **Summary**: Vanilla HTML/CSS/JS 단일 페이지 + 3+1 파일 Pragmatic Balance 구조의 200문항 OX 퀴즈 웹게임 설계
>
> **Project**: OX퀴즈게임
> **Version**: 0.1.0
> **Author**: bkit:pdca/design (kakaiuina@gmail.com)
> **Date**: 2026-05-09
> **Status**: Draft (PDCA Cycle 1, Design Phase)
> **Planning Doc**: [nonsense-quiz-mvp.plan.md](../../01-plan/features/nonsense-quiz-mvp.plan.md)
> **PRD**: [nonsense-quiz-mvp.prd.md](../../00-pm/nonsense-quiz-mvp.prd.md)

### Pipeline References

| Phase | Document | Status |
|-------|----------|--------|
| Phase 1 (Schema) | (생략) — CSV 4필드 단순 | N/A |
| Phase 2 (Convention) | Plan §8.2 표 | ✅ Embedded |
| Phase 3 (Mockup) | `_refs/screenshots-description.md` | ✅ |
| Phase 4 (API Spec) | (생략) — 백엔드 없음 | N/A |

---

## Context Anchor

> Plan에서 복사. Design→Do 핸드오프 시 전략 컨텍스트 보존.

| Key | Value |
|-----|-------|
| **WHY** | 5년 누적 OX 비전의 시장검증 진입점 + SNS funnel 랜딩 종착지 부재 해결 |
| **WHO** | 1차: SNS에서 OX 콘텐츠 본 자취생/20대 (페르소나 박지원, 24세). 2차/3차: 자격증 준비생, 대학교수 |
| **RISK** | (1) 200문항 자체제작 품질 불균질, (2) MVP 단순성 vs 재방문 동기 부족, (3) 정적 사이트 분석 데이터 제약, (4) 디자인 자산 저작권 |
| **SUCCESS** | 4주 내 — 평균 세션 ≥3분, 완주율 ≥40%, 공유 ≥50건, UTM 3채널 추적, 모바일 ≥70% |
| **SCOPE** | **포함**: OX 200문항(30개 셔플), 라이프 3, Q.번호, 정답·오답 즉시 피드백, "내가 짱!" 종료 화면, 공유, GA4. **불포함**: 회원·DB·마일리지·카테고리 UI·UGC·멀티·결제·다크모드·자취생카페 링크 |

---

## Design Anchor

> Pencil MCP 미사용. 디자인 토큰은 §10 + `_refs/screenshots-description.md` 에서 추출.

| Category | Tokens |
|----------|--------|
| **Colors** | bg: `#3a3a3a` (도로풍 다크), card-bg: `#fff5e6` (인트로 옅은 노랑), correct-zone: `#7cb342`, wrong-zone: `#1a1a2e`, victory: `#fdd835` (방사형), O-button: `#29b6f6`, X-button: `#ef5350`, text: `#ffffff` (외곽선) |
| **Typography** | "Black Han Sans" (제목·OX 버튼 라벨), "Jua" (본문·문제·해설). 사이즈: 제목 14vmin / 문제 6vmin / 본문 4vmin |
| **Spacing** | 8px 그리드. 카드 24px, section 32px, button-padding 16px 24px |
| **Radius** | OX 버튼 50% (원형), 카드 16px, 작은 칩 8px |
| **Tone** | 만화풍·캐주얼·도파민 친화. 외곽선 처리된 굵은 한글 타이포 + 라운드 chibi 이모지 |
| **Layout** | 모바일 세로 9:16. 화면 분할: 인트로(중앙 정렬), 게임(상단 HUD 15% / 문제 25% / 분할 씬 35% / OX 버튼 25%), 종료(중앙 폭발 배경) |

---

## 1. Overview

### 1.1 Design Goals

1. **단순성 절대 우선**: ~500 LOC 이내 단일 `script.js`. 외부 npm 의존성 0.
2. **모바일 세로 우선**: 박지원(24세 자취생) 페르소나가 지하철에서 한 손으로 조작 가능.
3. **시각적 차별점 1차 구현**: 퀴즈스틱맨식 군중심리 분할 연출을 이모지 기반으로 단순화.
4. **데이터 분리**: CSV는 코드와 분리해 사용자가 독립적으로 관리 가능 (200문항 추가/수정에 코드 변경 불필요).
5. **분석 가능성**: GA4 5개 이벤트 + UTM dimension으로 PRD §7 SC1~SC5 모두 측정.
6. **Phase 2A 진화 가능성**: 카테고리 확장 시 자연스럽게 모듈 분리(Option B로 진화) 가능한 구조.

### 1.2 Design Principles

- **Single File Section Boundaries**: `script.js` 내 명확한 섹션 주석으로 논리 구획 (`// === DATA ===`, `// === GAME LOOP ===` 등). 향후 분리 시 절단선이 됨.
- **State as Single Source of Truth**: `Game.state` 단일 객체로 전 게임 상태 유지. `render()` 함수가 항상 `state` 기반으로 DOM 업데이트.
- **Pure Functions Where Possible**: `shuffle()`, `parseCSV()`, `formatScore()` 등은 부작용 없는 순수 함수.
- **No Framework, No Build**: 페이지 로드 즉시 실행. Source map·번들·트랜스파일 0.
- **Privacy by Default**: localStorage·쿠키 미사용. GA4는 `anonymize_ip: true`.
- **Graceful Degradation**: WebShare API 미지원 → 클립보드 복사 fallback. CSV 로드 실패 → 사용자 친화 에러 화면.

---

## 2. Architecture Options

### 2.0 Architecture Comparison

3가지 옵션 중 사용자가 **Option C: Pragmatic Balance** 선택 (Checkpoint 3, 2026-05-09).

| Criteria | Option A: Minimal | Option B: Clean | **Option C: Pragmatic** ⭐ |
|----------|:-:|:-:|:-:|
| **Approach** | 단일 파일 (HTML 인라인) | ES Modules 5+ 파일 분리 | 3+1 파일, 섹션 주석 구획 |
| **New Files** | 1 (index.html) + 데이터 | 7+ (HTML/CSS/JS×5/CSV) | 4 (HTML/CSS/JS/CSV) + assets |
| **Modified Files** | 0 (greenfield) | 0 | 0 |
| **Complexity** | 매우 낮음 | 중간 | 낮음~중간 |
| **Maintainability** | LOC ≤300이면 OK | 매우 우수 | 우수 (섹션 명확) |
| **Effort** | 가장 낮음 | 가장 높음 | 중간 |
| **Risk** | 가독성 급락 위험 | 1차 MVP에 과한 분리·CORS 이슈 | 균형, Phase 2A 진화 자연스러움 |
| **Recommendation** | 1회성 prototype | 장기 Next.js 마이그 직전 | **1차 MVP 기본** |

**Selected**: **Option C — Pragmatic Balance**

**Rationale**: 1차 MVP는 ~500 LOC 예상으로 Option A의 가독성 한계(~300 LOC) 초과. Option B는 5+ JS 파일 분리가 1차에 과하고, `file://` 로컬 열기 시 ES Modules CORS 이슈 발생. Option C는 4파일 깔끔 + `script.js` 내부 섹션 주석으로 구조성 확보 + Phase 2A 카테고리 추가 시 섹션 단위로 자연스럽게 모듈 분리(B로 진화) 가능.

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (모바일 세로 우선)                                  │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  index.html (3 views, view 토글)                     │   │
│   │  ├── #intro   (인트로 화면, 시작 버튼)               │   │
│   │  ├── #game    (게임 진행 화면)                       │   │
│   │  └── #end     (종료 "내가 짱!" 화면)                  │   │
│   └─────────────────────────────────────────────────────┘   │
│           ▲                                                  │
│           │ DOM update via render(state)                     │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  script.js (Game 객체 단일)                          │   │
│   │  ├── state           (게임 상태 단일 SoT)            │   │
│   │  ├── DATA section    (loadQuestions, shuffle, parseCSV) │
│   │  ├── GAME section    (showQuestion, handleAnswer, end) │
│   │  ├── ANALYTICS section (ga(event, params), UTM)       │
│   │  ├── SHARE section   (share, copyToClipboard)         │
│   │  └── RENDER section  (render, switchView, animate)    │
│   └─────────────────────────────────────────────────────┘   │
│           │                              │                   │
│           ▼                              ▼                   │
│   ┌─────────────┐                ┌─────────────────┐        │
│   │ data/       │                │  GA4 SDK (CDN)  │        │
│   │ questions   │                │  measurement ID  │        │
│   │ _v1.csv     │                │  G-XXXXXXXXXX   │        │
│   └─────────────┘                └─────────────────┘        │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
       GitHub Pages
       (static hosting)
```

### 2.2 Data Flow

```
[페이지 로드]
   ↓
1. fetch('data/questions_v1.csv') → parseCSV() → state.questionPool[]  (200문항)
   ↓
2. renderIntro() — 인트로 화면 표시, "시작" 버튼 대기
   ↓ [사용자 시작 클릭]
3. shuffle(state.questionPool, 30) → state.currentRound[]              (30문항)
   ↓
4. ga('game_start', {})
   ↓
5. showQuestion(0) → renderGame()
   ↓ [사용자 O 또는 X 탭]
6. handleAnswer(userChoice) →
   - 정답: ga('answer_o' or 'answer_x', {correct: true})
            → animate(반대편 추락) → state.score += 1
   - 오답: ga('answer_o' or 'answer_x', {correct: false})
            → animate(자기 흔들림) → state.lives -= 1
   ↓
7. 다음 문제 자동 진행 (1초 딜레이)
   ↓ [라이프 0 OR 30문항 완주]
8. ga('game_end', {score, total: 30, lives_left})
   ↓
9. renderEnd() → "내가 짱!" 화면 + 점수
   ↓ [사용자 공유 클릭]
10. share() → WebShare API 시도 → 실패 시 clipboard 복사
    ga('share_click', {method: 'webshare' or 'clipboard'})
   ↓ [사용자 다시풀기 클릭]
11. resetState() → renderIntro() (3번으로 순환)
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| index.html | style.css, script.js, data/questions_v1.csv | 단일 진입점 |
| script.js | (네이티브) fetch, DOM API, Web Share API, navigator.clipboard | 외부 npm 0 |
| script.js | GA4 gtag SDK (CDN, async) | 분석 |
| style.css | Google Fonts CDN (Black Han Sans, Jua) | 만화체 한글 |
| Pricing | None (GitHub Pages 무료, GA4 무료, Google Fonts 무료) | 운영비 0 |

---

## 3. Data Model

### 3.1 CSV 스키마 (`data/questions_v1.csv`)

| 필드 | 타입 | 필수 | 설명 | 예시 |
|------|------|:----:|------|------|
| `id` | integer | ✅ | 1부터 시작하는 일련번호. 추후 교체 추적용 | `1` |
| `question` | string | ✅ | 문제 텍스트. 줄바꿈 없음. 쉼표·따옴표 포함 시 전체를 따옴표로 감쌈 | `"바나나는 나무에서 열린다"` |
| `answer` | enum('O','X') | ✅ | 정답 단일 문자 | `X` |
| `explanation` | string | ✅ | 짧은 해설 (50자 내외 권장) | `"바나나는 거대한 풀(초본)에서 열린다"` |

**제약**:
- `id`는 **유일**하고 정수. 누락·중복 시 로드 단계에서 경고.
- `answer`는 정확히 `O` 또는 `X` (대문자). 다른 값은 버려짐.
- 최소 30개 이상 권장 (한 라운드 30문항 셔플 위해). 30개 미만 시 인트로에서 "데이터가 부족해요" 안내.
- 권장 200개. 800자 이내 평균 → 약 100KB 미만 CSV.

### 3.2 JS State Shape (`Game.state`)

```javascript
const state = {
  // ── DATA ──
  questionPool: [],         // [{id, question, answer, explanation}, ...] 200개
  currentRound: [],         // 셔플된 30문항
  questionIndex: 0,         // 0..29

  // ── GAME ──
  score: 0,                 // 정답 수
  lives: 3,                 // 남은 라이프
  view: 'intro',            // 'intro' | 'game' | 'end' | 'error'

  // ── META ──
  utm: { source: null, medium: null, campaign: null },  // URL 파라미터에서 파싱
  sessionStartedAt: null,   // 세션 시작 시각 (Date)
  loadError: null,          // CSV 로드 실패 시 사유
};
```

### 3.3 Entity Relationships

```
[CSV 200문항] ──load(once)──→ [questionPool]
                                    │
                                    ├──shuffle(30)──→ [currentRound] ──iterate──→ [현재 문제]
                                    │
                                    └──persist? NO ── (다음 라운드는 새 셔플)
```

### 3.4 No Persistence (의도적)

- localStorage·sessionStorage·쿠키·IndexedDB **모두 미사용**.
- 새로고침 시 모든 상태 초기화 (페르소나 박지원 톤 — 가입 거부감 회피, 단순성 우선).
- 점수 기록·랭킹 등은 Phase 2B (마일리지 시스템) 진입 시 도입.

---

## 4. API Specification

### 4.1 N/A — 정적 사이트

본 1차 MVP는 백엔드 API 없음. 유일한 데이터 입출은:

| Resource | Type | Method | Purpose |
|----------|------|--------|---------|
| `data/questions_v1.csv` | Static file | GET (브라우저 fetch) | 페이지 로드 시 1회 |
| `https://www.google-analytics.com/g/collect` | External (GA4) | POST (gtag SDK) | 5개 이벤트 발화 시 |

**향후 (Phase 2A+)**: Next.js API routes (`/api/questions`, `/api/categories`) 또는 bkend.ai BaaS 도입.

---

## 5. UI/UX Design

### 5.1 Screen Layouts

#### 5.1.1 인트로 화면 (`#intro`)

```
┌─────────────────────────────────────────────┐
│  배경: 어두운 회색 #3a3a3a (도로 텍스처)    │
│  중앙 노란 점선 (수직) — CSS background    │
│                                             │
│           ╔══════════════════╗              │
│           ║  넌센스 OX 퀴즈    ║   (외곽선)  │
│           ║      준비됐어?     ║              │
│           ╚══════════════════╝              │
│                                             │
│         😀 🤔 😎 🥳 🤩 😆 😏           │ (이모지 군중)
│         🐱 🐶 🦊 🐰 🐼 🐯 🦁          │
│              👤 (나)                        │
│                                             │
│           ┌──────────────────┐              │
│           │   시작하기 ▶     │              │
│           └──────────────────┘              │
│                                             │
│   * 라이프 ❤️ 3개로 30문항 도전!             │
└─────────────────────────────────────────────┘
```

#### 5.1.2 게임 진행 화면 (`#game`)

```
┌─────────────────────────────────────────────┐
│ [HUD 15%]                                    │
│  ‖  Q.6 / 30      ❤️❤️❤️    score: 5         │
├─────────────────────────────────────────────┤
│ [문제 25%]                                   │
│                                             │
│      지구는 안쪽으로 갈 수록                │
│            뜨거워진다?                      │
│                                             │
├─────────────────────────────────────────────┤
│ [분할 씬 35%]                                │
│                  ╲    ╱                     │
│   🟢 정답 영역    ╲  ╱   ❌ 오답 영역        │
│   😀 🤔 😎          ╲╱      😱 😨           │
│   🥳 (나) 🤩       ╱╲      😰 (떨어지는)    │
│   🐱 🐶            ╱  ╲     ↓               │
│                  ╱    ╲                     │
├─────────────────────────────────────────────┤
│ [OX 버튼 25%]                                │
│                                             │
│       ┌─────┐         ┌─────┐               │
│       │  O  │         │  X  │               │
│       └─────┘         └─────┘               │
│       (청록)          (빨강)                 │
│                                             │
└─────────────────────────────────────────────┘
```

**정답·오답 즉시 피드백**:
- 정답 시: 반대편 영역 이모지가 0.5초간 `transform: translateY(100vh)` 추락
- 오답 시: 자기 영역 (나 표시) 이모지가 0.3초간 `shake` 키프레임. 라이프 -1 (❤️→💔 즉시 변경)
- 둘 다: 1초간 화면 하단에 토스트로 해설 표시 → 자동으로 다음 문제

#### 5.1.3 종료 화면 (`#end`)

```
┌─────────────────────────────────────────────┐
│  배경: 노란 방사형 #fdd835 (CSS radial-grad) │
│  방사선 뻗는 모션 (CSS conic-gradient + spin) │
│                                             │
│           ╔══════════════════╗              │
│           ║     내가 짱!      ║              │
│           ║  (외곽선 흰 폰트)  ║              │
│           ╚══════════════════╝              │
│                                             │
│              🥳                             │
│            (만세 자세)                       │
│                                             │
│          30문제 중 28개 맞춤                │
│            라이프 1개 남음                   │
│                                             │
│        🪙 OX 코인이 흩날립니다                │
│                                             │
│      ┌──────────────────────┐               │
│      │  📤 친구한테 자랑하기  │               │
│      └──────────────────────┘               │
│                                             │
│      ┌──────────────────────┐               │
│      │   🔄 다시 풀기         │               │
│      └──────────────────────┘               │
└─────────────────────────────────────────────┘
```

### 5.2 User Flow

```
(SNS 영상) ─클릭→ [URL?utm_source=youtube&utm_campaign=launch]
                          ↓
                     [#intro 화면]
                          ↓ [시작 클릭]
                     [#game Q.1] → [Q.2] → ... → [Q.30 OR 라이프 0]
                          ↓
                     [#end "내가 짱!"]
                          ↓
              ┌──────────────────────────┐
              ↓                          ↓
        [공유 클릭]                  [다시풀기 클릭]
              ↓                          ↓
   WebShare → 카톡/링크 복사        [#intro] (re-shuffle)
              ↓
        (외부 앱 이동, GA4 이벤트 발화)
```

### 5.3 Component List

| Component | Location | Responsibility |
|-----------|----------|----------------|
| Intro view | `index.html` `<section id="intro">` | 인트로 + 시작 버튼 |
| Game view | `index.html` `<section id="game">` | HUD + 문제 + 분할 씬 + OX 버튼 |
| End view | `index.html` `<section id="end">` | 점수 + 공유 + 다시풀기 |
| Error view | `index.html` `<section id="error">` | CSV 로드 실패 등 fallback |
| OX Button | `<button class="ox-btn ox-btn--o">`, `<button class="ox-btn ox-btn--x">` | 큰 둥근 버튼 |
| Heart life | `<span class="life">❤️</span>` | 라이프 표시 |
| Question card | `<div class="question">` | 문제 텍스트 |
| Crowd zone | `<div class="zone zone--correct">`, `<div class="zone zone--wrong">` | 좌/우 이모지 군중 |
| Toast | `<div class="toast" hidden>` | 정답/오답 해설 1초 |

### 5.4 Page UI Checklist (Critical for Gap Detection)

> ⚠️ 모든 항목은 Gap Detector가 1:1 검증. 누락 시 functional gap.

#### Intro Page (`#intro`)

- [ ] 타이틀: "넌센스 OX 퀴즈" 또는 "준비됐어?" — 외곽선 처리, 청록 또는 흰색
- [ ] 이모지 군중 표시: 최소 7개 다른 이모지 + "나" 라벨이 1개 캐릭터 옆에
- [ ] 안내 문구: "라이프 3개로 30문항 도전!" 또는 동일 의미
- [ ] 시작 버튼: `[시작하기 ▶]` — 둥근 모서리, 청록 배경, 흰 글자, 큰 사이즈 (지름 또는 폭 ≥ 200px)
- [ ] (선택) 진행 중 GA4 측정 안내 (privacy 정책 링크 fallback)
- [ ] 데이터 로드 실패 시 시작 버튼 비활성화 + 에러 메시지

#### Game Page (`#game`)

- [ ] HUD 상단: 일시정지(‖) 버튼 (1차 비활성화 OK), `Q.{현재}/{총30}`, 라이프 ❤️ 3개 (오답시 💔로 변경), 점수 숫자
- [ ] 문제 텍스트 영역: 흰 글자 + 외곽선, 줄바꿈 자동, 폰트 사이즈 ≥ 5vmin
- [ ] 분할 씬 (좌측 정답 영역): 옅은 청록·녹색 배경, 이모지 5개+ "나" 라벨
- [ ] 분할 씬 (우측 오답 영역): 어두운 빨강·검정 배경, 이모지 3-5개
- [ ] 분할선: CSS gradient 또는 SVG로 거친 경계
- [ ] O 버튼: 청록 #29b6f6, 원형 (border-radius: 50%), 지름 ≥ 35vw, 가운데 큰 "O" 라벨
- [ ] X 버튼: 빨강 #ef5350, 원형, 지름 ≥ 35vw, 가운데 큰 "X" 라벨
- [ ] 정답 시 애니메이션: 반대편 이모지 추락 (translateY 0.5s)
- [ ] 오답 시 애니메이션: 자기 이모지 shake + 라이프 -1
- [ ] 토스트: 정답 직후 해설 1초 표시 후 자동 제거

#### End Page (`#end`)

- [ ] 타이틀: "내가 짱!" — 외곽선 흰 굵은 글자, 폰트 사이즈 ≥ 14vmin
- [ ] 노란 방사형 배경: CSS `radial-gradient` + `conic-gradient` 광선 효과
- [ ] 점수 표시: "{N}문제 중 {M}개 맞춤" 또는 "정답 {M}/30, 라이프 {L}개 남음"
- [ ] 캐릭터 이모지: 만세 자세 또는 🥳 표시 (CSS bounce 애니메이션)
- [ ] 공유 버튼: "친구한테 자랑하기" 라벨, 📤 또는 카톡 아이콘. 클릭 시 WebShare 또는 clipboard 복사
- [ ] 다시풀기 버튼: "다시 풀기" 또는 🔄 아이콘. 클릭 시 state 초기화 + 인트로 복귀
- [ ] (장식) OX 코인 흩날림 애니메이션 (CSS `falling-coins` 키프레임)
- [ ] **자취생 카페 링크 미노출 검증** — 외부 링크 0개

#### Error Page (`#error`, fallback)

- [ ] 친근한 에러 메시지: "문제를 불러올 수 없어요 😢"
- [ ] "새로고침" 버튼

---

## 6. Error Handling

### 6.1 Error Scenarios

| Code | Scenario | Cause | Handling |
|------|----------|-------|----------|
| `CSV_LOAD_FAIL` | CSV 파일 fetch 실패 | 네트워크/배포 문제 | Error view 표시 + GA4 `error` 이벤트 |
| `CSV_PARSE_FAIL` | 파싱 중 형식 오류 | 따옴표 누락 등 | Error view + 콘솔 경고. 정상 행만 사용 (파셜 복구) |
| `TOO_FEW_QUESTIONS` | 30문항 미만 | 데이터 작성 진행 중 | 인트로에서 "데이터 준비 중이에요"로 시작 버튼 비활성화 |
| `WEBSHARE_UNSUPPORTED` | navigator.share 미지원 | 데스크톱 브라우저 | clipboard.writeText fallback + "링크가 복사됐어요" 토스트 |
| `CLIPBOARD_FAIL` | clipboard API도 실패 | 매우 구형 브라우저 | `prompt('이 링크를 복사하세요', url)` 최후 fallback |
| `INVALID_ANSWER` | CSV의 `answer`가 'O'/'X'가 아님 | 데이터 오타 | 해당 문항 스킵 + 콘솔 경고. 사용자에게는 안 보임 |

### 6.2 No Error Response JSON Format

> 정적 사이트라 서버 에러 응답 N/A. 클라이언트 에러는 위 시나리오 표 + 사용자 친화 메시지로 처리.

---

## 7. Security Considerations

> 정적 사이트 + 사용자 입력 0 (클릭만) → 공격 벡터 매우 제한적.

- [x] **XSS 방지**: 모든 동적 텍스트(문제·해설)는 `textContent`로만 삽입. `innerHTML` 사용 금지.
- [x] **인증/인가**: N/A (계정 없음)
- [x] **민감정보 저장**: 0건 (localStorage 미사용)
- [x] **HTTPS**: GitHub Pages 자동 강제
- [x] **Rate Limiting**: 정적 파일이라 N/A. GitHub Pages CDN이 트래픽 자동 처리.
- [x] **GA4 Privacy**: `gtag('config', GA_ID, { anonymize_ip: true })` 설정
- [x] **OG 미리보기 안전**: og:image는 자체 제작 1080×1080 PNG (캐릭터·텍스트 모두 자체 자산)
- [x] **CSP (Content Security Policy)**: 외부 스크립트는 GA4와 Google Fonts만 허용. `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:;">`
- [x] **저작권 자체 인증**: 코드 헤더 주석에 "퀴즈스틱맨 자산 미사용. 컬러·메커니즘 컨셉만 차용. 모든 시각 자산은 자체 제작 또는 유니코드 이모지." 명시

---

## 8. Test Plan

### 8.1 Test Scope (Tailored for Static Site)

| Type | Target | Tool | Phase | Mandatory |
|------|--------|------|-------|:---------:|
| L1: API Tests | (N/A — no backend) | — | — | ❌ |
| L2: UI Action Tests | OX 버튼·시작·공유·다시풀기 클릭 → 결과 검증 | Manual + Optional Playwright | Do | ✅ Manual |
| L3: E2E Scenario Tests | Intro→30문항 풀이→End→공유 전체 흐름 | Manual + Optional Playwright | Do | ✅ Manual |
| L4: Compatibility Tests | 모바일 5종 + 데스크톱 3종 | Manual | Check | ✅ |
| L5: Performance | Lighthouse 모바일 | Chrome DevTools | Check | ✅ |

> Playwright 자동화는 1차 MVP에서는 선택. Manual 우선. Phase 2A부터 Playwright 도입 검토.

### 8.2 L2: UI Action Test Scenarios

| # | Page | Action | Expected Result | Data Verification |
|---|------|--------|----------------|-------------------|
| 1 | Intro | 페이지 로드 | §5.4 인트로 체크리스트 모든 요소 표시. 시작 버튼 활성. | CSV 로드 성공 시 |
| 2 | Intro | "시작하기" 클릭 | Game view로 전환. Q.1 표시. | `state.view === 'game'`, `state.currentRound.length === 30` |
| 3 | Game | O 버튼 클릭 (정답이 O) | 반대편 이모지 추락 애니. 점수 +1. 토스트 해설 1초. 1초 후 다음 문제. | `state.score++`, `state.questionIndex++` |
| 4 | Game | X 버튼 클릭 (정답이 O) | 자기 흔들림 애니. 라이프 -1. 토스트 해설. 다음 문제. | `state.lives--` |
| 5 | Game | 라이프 0 도달 | End view로 자동 전환. | `state.view === 'end'` |
| 6 | Game | 30문제 완주 | End view로 전환. 점수 표시 정확. | `state.questionIndex === 30` |
| 7 | End | "친구한테 자랑하기" 클릭 | WebShare 또는 clipboard 복사 + 토스트 | GA4 `share_click` 발화 |
| 8 | End | "다시 풀기" 클릭 | Intro view 복귀, state 초기화 | `state.score === 0`, `state.lives === 3` |
| 9 | Error | CSV 강제 실패 (파일 임시 제거) | Error view 표시 + 새로고침 버튼 | Console error log |

### 8.3 L3: E2E Scenario Test Scenarios

| # | Scenario | Steps | Success Criteria |
|---|----------|-------|-----------------|
| 1 | **Happy path 전체 흐름** | UTM URL 진입 → Intro → 시작 → 30문항 풀이 → End → 공유 | 30문항 모두 출제, 점수 정확, GA4 4개 이벤트 모두 발화 (`game_start`/`answer_o`/`answer_x`/`game_end`) |
| 2 | **라이프 소진 종료** | Intro → 시작 → 의도적으로 3회 연속 오답 → End | 라이프 0 후 즉시 End 전이, 점수=0 |
| 3 | **공유→복귀** | End → 공유 클릭 (clipboard 모드) → 토스트 확인 → 다시풀기 → 새 30문항 셔플 | 두 라운드의 currentRound가 다름 |
| 4 | **CSV 데이터 부족** | CSV에 30개 미만으로 임시 수정 → 페이지 진입 | "데이터 준비 중이에요" 인트로, 시작 버튼 비활성 |
| 5 | **모바일 가로 회전** | Intro 진입 → 가로로 회전 → 다시 세로 | 레이아웃 깨짐 없음 (vmin 기반 반응형) |
| 6 | **UTM 파라미터 추적** | `?utm_source=youtube&utm_campaign=launch` URL 진입 → 30문항 완주 | GA4 `game_end` 이벤트의 dimension에 utm 값 들어감 |

### 8.4 L4: Compatibility Test Matrix

| Device | OS | Browser | Required Pass | Note |
|--------|-----|---------|:-------------:|------|
| iPhone SE (1세대 또는 2세대) | iOS 15+ | Safari | ✅ | 가장 작은 화면, fallback test |
| iPhone 12/13 | iOS 16+ | Safari | ✅ | 표준 모바일 |
| iPhone 14/15 | iOS 17+ | Safari + Chrome | ✅ | 최신 |
| Galaxy S20/S21 | Android 12+ | Chrome | ✅ | 안드로이드 표준 |
| Galaxy S23 | Android 14 | Chrome + Samsung Internet | ✅ | 최신 안드로이드 |
| Desktop | macOS | Safari, Chrome, Firefox | △ Best-effort | 데스크톱 미공식지원 |
| Desktop | Windows | Chrome, Edge, Firefox | △ Best-effort | 동일 |

### 8.5 L5: Performance Targets (Lighthouse Mobile)

| Metric | Target | Note |
|--------|:------:|------|
| Performance | ≥ 85 | First Contentful Paint < 2s |
| Accessibility | ≥ 90 | 키보드 접근, ARIA, 컬러 대비 |
| Best Practices | ≥ 90 | HTTPS, console errors 0 |
| SEO | ≥ 90 | meta tags, OG, mobile-friendly |
| Total Bundle | < 100KB | HTML+CSS+JS+CSV 합계 (이미지 제외) |

### 8.6 Seed Data Requirements

> CSV는 사용자가 200개 작성. 테스트용 fixture 별도 불필요 (실제 데이터로 통합 테스트).

| Entity | Minimum Count | Key Fields Required |
|--------|:------------:|---------------------|
| Question | 30개 (시작 가능 최소) | id 정수 유니크, question 비어있지 않음, answer ∈ {O,X}, explanation 비어있지 않음 |
| Question | 200개 (Definition of Done) | 위 + 다양한 분야 (생활상식·과학·동물·역사 등) 균형 |

---

## 9. Clean Architecture (Simplified for Static Site)

### 9.1 Layer Structure (Vanilla 단순화)

전통적 4-layer가 아닌 **섹션 기반 논리 구획**으로 적용:

| Layer (논리적) | Section in script.js | Responsibility |
|---------------|---------------------|----------------|
| **Presentation** | `// === RENDER ===` | DOM 업데이트, 애니메이션, view 토글 |
| **Application** | `// === GAME LOOP ===` | 게임 진행 흐름, 답변 처리, 상태 전이 |
| **Domain** | `state` 객체 + `// === DATA ===` 의 순수 함수 | 게임 규칙 (셔플·점수 계산·라이프 차감) |
| **Infrastructure** | `// === DATA ===` (fetch), `// === ANALYTICS ===` (GA4), `// === SHARE ===` | 외부 시스템 |

### 9.2 Dependency Rules (단순화)

```
RENDER ──reads──→ state
RENDER ──reads──→ DOM API (Infrastructure)
GAME_LOOP ──mutates──→ state
GAME_LOOP ──calls──→ ANALYTICS, SHARE (Infrastructure)
DATA ──parses──→ CSV, populates state
state ──pure──→ no external deps
```

규칙:
- **state 객체는 절대 DOM에 직접 의존 안 함** (테스트·이식성 위해)
- **RENDER는 state를 읽기만** 하고 변경 안 함 (mutation은 GAME_LOOP만)

### 9.3 File Import Rules (단순)

ES Modules 미사용 (Option C 선택). 단일 `script.js` + IIFE/객체 리터럴 패턴이라 import 규칙 N/A.
**대신**: 섹션 주석 순서를 의존성 순서로 강제.

```javascript
// === BOOTSTRAP === (Game.init만 호출)
// === DATA === (CSV 로드·파싱·셔플)
// === ANALYTICS === (GA4 헬퍼)
// === SHARE === (WebShare·clipboard)
// === GAME LOOP === (게임 진행, 위 3개 의존)
// === RENDER === (DOM 업데이트, state 의존)
```

### 9.4 This Feature's Layer Assignment

| Component | Layer | Section in script.js |
|-----------|-------|---------------------|
| Game.init() | Bootstrap | `// === BOOTSTRAP ===` |
| Game.loadQuestions() | Infrastructure→Domain | `// === DATA ===` |
| Game.shuffle() | Domain (순수) | `// === DATA ===` |
| Game.parseCSV() | Domain (순수) | `// === DATA ===` |
| Game.ga(event, params) | Infrastructure | `// === ANALYTICS ===` |
| Game.parseUTM() | Infrastructure | `// === ANALYTICS ===` |
| Game.share() | Infrastructure | `// === SHARE ===` |
| Game.copyToClipboard() | Infrastructure | `// === SHARE ===` |
| Game.startRound() | Application | `// === GAME LOOP ===` |
| Game.handleAnswer() | Application | `// === GAME LOOP ===` |
| Game.advance() | Application | `// === GAME LOOP ===` |
| Game.endGame() | Application | `// === GAME LOOP ===` |
| Game.render() | Presentation | `// === RENDER ===` |
| Game.switchView() | Presentation | `// === RENDER ===` |
| Game.animateFall() | Presentation | `// === RENDER ===` |

---

## 10. Coding Convention Reference

> 출처: Plan §8.2 + 본 Design 문서.

### 10.1 Naming Conventions

| Target | Rule | Example |
|--------|------|---------|
| HTML id | kebab-case | `#intro`, `#game-hud`, `#ox-button-o` |
| CSS class | BEM | `.game__hud`, `.ox-btn--primary`, `.zone--correct` |
| JS variable/method | camelCase | `state.questionPool`, `handleAnswer()` |
| JS constant | UPPER_SNAKE_CASE | `LIFE_INITIAL = 3`, `ROUND_SIZE = 30`, `GA_MEASUREMENT_ID = 'G-...'` |
| File | kebab-case 또는 lowercase | `index.html`, `style.css`, `script.js`, `questions_v1.csv` (예외: 데이터 파일은 underscore 허용) |
| 폴더 | kebab-case | `data/`, `assets/`, `_refs/` |
| CSS variable | kebab-case with `--` prefix | `--bg-primary`, `--btn-o-color` |

### 10.2 Import Order

ES Modules 미사용. 단일 `<script>` 태그라 N/A.
**대안 — `<head>` 의 외부 자원 로드 순서**:

```html
<!-- 1. 폰트 (paint-blocking 최소화 위해 preload) -->
<link rel="preload" href="https://fonts.googleapis.com/..." as="style" />
<link rel="stylesheet" href="https://fonts.googleapis.com/..." />

<!-- 2. 자체 CSS -->
<link rel="stylesheet" href="style.css" />

<!-- 3. GA4 (async, 페이지 렌더 차단 안 함) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-XXXXXXXXXX',{anonymize_ip:true});</script>

<!-- 4. 자체 script.js (defer로 DOMContentLoaded 후 실행) -->
<script defer src="script.js"></script>
```

### 10.3 Environment Variables (Inline Constants)

| Constant | Value | Where |
|----------|-------|-------|
| `GA_MEASUREMENT_ID` | `G-XXXXXXXXXX` (사용자 GA4 발급) | `index.html` `<head>` 인라인 + `script.js` 상수 |
| `OG_BASE_URL` | `https://{user}.github.io/ox-quiz/` | `index.html` `<meta property="og:url">` |
| `LIFE_INITIAL` | `3` | `script.js` 상수 |
| `ROUND_SIZE` | `30` | `script.js` 상수 |
| `TOAST_DURATION_MS` | `1000` | `script.js` 상수 |
| `ANIMATION_FALL_MS` | `500` | `script.js` 상수 |

### 10.4 This Feature's Conventions

| Item | Convention Applied |
|------|-------------------|
| HTML/CSS naming | BEM + kebab-case |
| JS scope | 단일 `const Game = { ... };` 객체 리터럴 — IIFE 대안 가능 |
| State mutation | GAME_LOOP 섹션 함수만 가능. RENDER는 read-only |
| DOM access | `document.getElementById` 우선. `querySelector` 는 복합 선택 시만 |
| Error handling | `try { fetch } catch (e) { renderError(e) }` 패턴. console.error는 항상 동반 |
| Animations | CSS 키프레임 우선. JS는 `classList.add/remove` 만 |
| CSV parsing | 자체 미니 파서 (200줄 이내 단순 데이터 가정). Papa Parse 등 외부 의존 X |

---

## 11. Implementation Guide

### 11.1 File Structure

```
OX퀴즈게임/
├── index.html                  ← 진입점 (~150 LOC: head + 4 view sections)
├── style.css                   ← 디자인 토큰·레이아웃·애니메이션 (~300 LOC)
├── script.js                   ← Game 객체, 6개 섹션 (~500 LOC)
├── data/
│   └── questions_v1.csv        ← 200문항 (사용자 작성)
├── assets/
│   ├── og-image.png            ← 1080×1080 SNS 미리보기 (자체 제작)
│   └── favicon.svg             ← 단순 파비콘
├── _refs/                      ← 디자인 레퍼런스 (이미 존재)
│   └── screenshots-description.md
└── docs/                       ← PDCA 문서 (이미 존재)
    ├── 00-pm/...
    ├── 01-plan/...
    └── 02-design/...
```

### 11.2 Implementation Order

> Do 단계에서 아래 순서대로 진행. 각 단계 완료 시 console·DevTools로 즉시 확인.

1. [ ] **Module 1 — 골격 + CSS 토큰 (M1)**: `index.html` 4 view section 마크업, `style.css` 디자인 토큰 + 기본 레이아웃
2. [ ] **Module 2 — 데이터 로드 (M2)**: `script.js` BOOTSTRAP + DATA section. CSV 로드·파싱·셔플 동작 콘솔 검증
3. [ ] **Module 3 — 게임 루프 (M3)**: GAME_LOOP section. Q.1~Q.30 진행, 정답·오답·라이프 차감 로직
4. [ ] **Module 4 — UI 렌더링 (M4)**: RENDER section. view 전환, HUD 업데이트, 분할 씬 + OX 버튼
5. [ ] **Module 5 — 애니메이션 (M5)**: CSS 키프레임 (`falling`, `shake`, `bounce`, `victory-burst`) + JS classList 트리거
6. [ ] **Module 6 — 분석·공유 (M6)**: ANALYTICS + SHARE section. GA4 5개 이벤트, WebShare/clipboard
7. [ ] **Module 7 — Polish + 호환성 (M7)**: 모바일 5종 수동 테스트, 에러 view, OG 이미지, favicon
8. [ ] **Module 8 — 배포 (M8)**: GitHub Pages 배포, 200문항 사용자 입력 완료, 5명 샘플 풀이 검수

### 11.3 Session Guide

> Plan~Design은 본 PDCA Cycle 1에서 완료. Do 단계는 Module별 분할 가능.

#### Module Map

| Module | Scope Key | Description | Estimated Turns |
|--------|-----------|-------------|:---------------:|
| 골격 + CSS 토큰 | `module-1` | index.html 마크업, style.css 변수·레이아웃 | 8-12 |
| 데이터 로드 | `module-2` | script.js BOOTSTRAP·DATA 섹션 | 6-8 |
| 게임 루프 | `module-3` | GAME_LOOP 섹션 + 상태 전이 | 10-15 |
| UI 렌더링 | `module-4` | RENDER 섹션 + view 전환 | 10-12 |
| 애니메이션 | `module-5` | CSS 키프레임 + JS 트리거 | 8-10 |
| 분석·공유 | `module-6` | ANALYTICS·SHARE 섹션 + UTM | 6-8 |
| Polish + 호환성 | `module-7` | 5종 모바일 테스트, OG, favicon | 10-15 |
| 배포 | `module-8` | gh-pages, 200문항 검수 | 5-8 |

#### Recommended Session Plan

| Session | Phase | Scope | Turns |
|---------|-------|-------|:-----:|
| Session 1 (이번) | PM + Plan + Design | 전체 | 30 |
| Session 2 | Do | `--scope module-1,module-2` (골격+데이터) | 25-30 |
| Session 3 | Do | `--scope module-3,module-4` (게임 루프+UI) | 35-40 |
| Session 4 | Do | `--scope module-5,module-6` (애니+분석) | 25-30 |
| Session 5 | Do | `--scope module-7,module-8` (polish+배포) | 25-30 |
| Session 6 | Check + Iterate (필요 시) + Report | 전체 | 30-40 |

> 빠른 진행 시 Session 2~5를 통합해 1-2 세션으로 완성 가능. 단, 각 module 완료 시 콘솔·브라우저로 검증 필수.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-09 | 초기 Design 문서. Option C (Pragmatic Balance) 선택, 8 module 분할, Page UI Checklist 정의 | bkit:pdca/design |
