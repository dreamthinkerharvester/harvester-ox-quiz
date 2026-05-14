# survival-mode-v3 Design Document

> **Summary**: v2 단일 파일 구조(Option C) 그대로 + v3 신규 코드는 명시적 `// === V3 ===` 섹션. Grand Slam 4분기 + 시각 보강 4건 + NPC 곡선 완화.
>
> **Project**: OX퀴즈게임
> **Version**: 0.3.0
> **Author**: bkit:pdca/design (kakaiuina@gmail.com)
> **Date**: 2026-05-10
> **Status**: Draft (PDCA Cycle 3, Design Phase)
> **Planning Doc**: [survival-mode-v3.plan.md](../../01-plan/features/survival-mode-v3.plan.md)
> **Predecessor**: [v2 Design](./survival-mode-v2.design.md), [영상 분석 리포트](../../00-pm/reference-video-analysis-2026-05-10.report.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | v2 컨셉 OK이나 도전 과제 부재로 1회 플레이 후 이탈. 영상 원본 11라운드 Grand Slam이 핵심 재플레이 트리거. |
| **WHO** | v2와 동일 (자취생/20대) |
| **RISK** | (1) Grand Slam 트리거 빈도 부적합, (2) 시각 보강이 60fps 저하, (3) NPC 곡선 완화로 라운드 너무 길어짐, (4) 세로 일렬이 모바일 세로 부자연스러움 |
| **SUCCESS** | Grand Slam 도달률 5-15%, 평균 라운드 4-7, 60fps 유지, share_click v2 +20% |
| **SCOPE** | **포함**: P1 + V1-V4 + T1. **불포함**: P2 카테고리·P3 100명 모드(v4) |

---

## Design Anchor

> v2 디자인 토큰 100% 상속 + v3 신규 토큰만 추가.

| Category | v2 (재사용) | v3 신규/변경 |
|----------|-------------|-------------|
| **Colors** | bg-primary `#3a3a3a`, color-O `#29b6f6`, color-X `#ef5350`, bg-victory `#fdd835` | grand-slam-gold: `#ffd700` (왕관), grand-slam-glow: `radial-gradient(circle, rgba(255,215,0,0.4) 0%, transparent 70%)`, me-label-bg: `var(--bg-victory)` |
| **Typography** | Black Han Sans (제목), Jua (본문) | Grand Slam title은 Black Han Sans + 큰 사이즈 (`clamp(40-72px)`) + 골든 그라디언트 |
| **Spacing** | 8px 그리드, 카드 24px | "나" 캡슐: 4px padding, 8px above sprite |
| **Tone** | 만화풍·도파민 친화 | + Grand Slam: 화려·축제감 (코인 비 ×2, 골든 글로우, 별 5개) |

---

## 1. Overview

### 1.1 Design Goals

1. **v2 일관성 유지**: 같은 단일 파일 + 섹션 컨벤션. v2 학습자 즉시 이해.
2. **v3 신규 코드 명시적 식별**: 모든 v3 추가는 `// === V3 ... ===` 섹션 마커
3. **기존 v2 코드 수정 최소**: 변경 시 `// [v3]` prefix로 변경 지점 표시
4. **점진적 적용 가능 모듈**: V1-V4 시각 보강은 각각 독립적이라 60fps 미달 시 1개씩 끄기 가능

### 1.2 Design Principles

- **State as SoT 유지**: `consecutiveCorrect`, `allCorrect`는 state에만, DOM에서 추론 안 함
- **Grand Slam = win 분기 확장**: 새 분기 코드 분리하지 않고 `checkEndCondition`을 단 한 줄 확장
- **Spawn 모드 토글 기반**: `SPAWN_LANE_PATTERN` 상수로 column ↔ random 즉시 전환 (v2 호환성 보장)
- **CSS-only 시각 보강**: V3(나 캡슐), V4(점수 ⭐)는 CSS pseudo-element + 텍스트만 — JS 불필요

---

## 2. Architecture

### 2.0 Architecture Comparison

3가지 옵션 중 사용자가 **Option C: Pragmatic Balance** 선택 (Checkpoint 3, 2026-05-10).

### 2.1 Selected: Option C — Pragmatic Balance

```
script.js (단일 파일, ~945줄, +90 from v2)
├── // === CONSTANTS (v2) ===
│   ├─ ALIVE_INITIAL=50, NPC_COUNT=49, TIMER_DURATION_SEC=5
│   ├─ NPC_ACCURACY_CURVE = [0.30, 0.42, 0.50, 0.55, 0.60, 0.62, 0.64, 0.65]  // [v3] 완화
│   ├─ EFFECT_TYPES = ['fall', 'poof', 'floor-crack', 'rocket']
│   ├─ ZONE_O_CENTER_X=25, ZONE_X_CENTER_X=75, ZONE_JITTER_X_PCT=8
│   └─ ...
│
├── // === V3 CONSTANTS ===
│   ├─ GRAND_SLAM_THRESHOLD = 4        (라운드 임계치)
│   ├─ SPAWN_LANE_PATTERN = 'column'    ('random' | 'column')
│   ├─ SPAWN_COLUMN_DURATION_MS = 1500  (위→중앙 등장 시간)
│   └─ ME_LABEL_TEXT = '나'              (CSS에서도 var로 사용)
│
├── // === STATE ===
│   ├─ ...v2 그대로
│   └─ // [v3] 신규 추가
│       ├─ consecutiveCorrect: number  (현재 연속 정답)
│       └─ allCorrect: boolean         (한 번이라도 오답이면 false)
│
├── // === BOOTSTRAP ===  (v2 그대로, 단 resetState 갱신)
│   └─ resetState():
│       ├─ ...v2 reset 그대로
│       └─ consecutiveCorrect = 0, allCorrect = true  // [v3]
│
├── // === DATA ===  (v2 100%)
├── // === ANALYTICS ===  (v2 + game_end_grand_slam)
├── // === GAME LOOP ===  (v2 그대로)
│
├── // === ARENA & SPAWN ===
│   ├─ spawnAllOnce()
│   │   ├─ ...v2 그대로
│   │   └─ if (SPAWN_LANE_PATTERN === 'column') Game.applyColumnSpawn();  // [v3]
│   ├─ // [v3] applyColumnSpawn()  (신규)
│   │   └─ NPC들의 baseY를 화면 위 -10% 시작 → animation으로 중앙 이동 (1.5s)
│   └─ // 기존 함수들 그대로
│
├── // === V3 GRAND SLAM ===  (신규 섹션)
│   ├─ trackCorrectness(correct):
│   │   ├─ if (correct) state.consecutiveCorrect += 1
│   │   ├─ else { state.consecutiveCorrect = 0; state.allCorrect = false; }
│   │   └─ revealAnswer() 끝부분에서 호출
│   ├─ isGrandSlam():
│   │   └─ return state.allCorrect && state.consecutiveCorrect >= GRAND_SLAM_THRESHOLD
│   └─ // checkEndCondition()의 win 분기를 win-grand-slam vs win 으로 split
│
├── // === REVEAL & ELIMINATION ===  (v2 + 1줄 추가)
│   └─ revealAnswer():
│       ├─ ...v2 그대로
│       └─ // [v3] Game.trackCorrectness(playerCorrect);
│
├── // === END FLOW ===
│   ├─ // [v3] checkEndCondition() 분기 확장
│   │   └─ const isWin = aliveSize === 1 && alive.has(PLAYER_ID);
│   │       if (isWin && Game.isGrandSlam()) return 'win-grand-slam';
│   │       if (isWin) return 'win';
│   │       ... (나머지 v2 그대로)
│   ├─ endGame():
│   │   └─ // [v3] eventName 분기 확장 (win-grand-slam → 'game_end_grand_slam')
│   └─ renderEnd():
│       └─ COPY 테이블에 'win-grand-slam' 행 1개 추가
│
├── // === SHARE ===  (v2 + grand_slam 분기 1줄)
│   └─ buildShareText():
│       └─ // [v3] if (result === 'win-grand-slam') return `🏆 OX 서바이벌 GRAND SLAM! ...`
│
├── // === HUD ===  (v2 그대로, renderHUD만 라이아웃 변경)
│   └─ renderHUD():
│       └─ // [v3] index.html의 새 라이아웃과 일치
│
└── // === V3 SIMULATION ===  (Game.simulate 함수에 grandSlam 카운트 추가)
    └─ simulate(n=10000): { ...v2 stats, grandSlams: number, grandSlamPct: string }
```

```
style.css (~795줄, +52 from v2)
├── ... v2 100% 그대로
├── // === V3: GRAND SLAM EFFECTS ===
│   ├─ .end[data-result="win-grand-slam"] .champion::after  // 골든 글로우
│   │   ├─ background: radial-gradient(circle, rgba(255,215,0,0.4), transparent 70%)
│   │   └─ animation: gs-glow 2s ease-in-out infinite
│   ├─ @keyframes gs-glow { 0%/100%: scale(1); 50%: scale(1.3); }
│   ├─ .end[data-result="win-grand-slam"] .coins  // 코인 추가 12개 .coin--gs
│   └─ .end[data-result="win-grand-slam"] .title--end  // 골든 그라디언트
│
├── // === V3: ME LABEL ===
│   └─ .arena__sprites .character.is-me::before
│       ├─ content: "나"
│       ├─ position: absolute; top: -16px; left: 50%
│       ├─ background: var(--bg-victory) #fdd835
│       ├─ padding: 1px 6px; border-radius: 8px
│       └─ font-size: 9px
│
├── // === V3: HUD SIMPLIFICATION ===
│   ├─ .hud__progress  (Q.X 그대로)
│   ├─ .hud__score (⭐ 아이콘 + 숫자, 더 큰 사이즈)
│   ├─ .hud__alive  (👥 아이콘 + 숫자, 보조 표기로 작게)
│   └─ HUD 그리드: 4-column → 3-column (left/center/right)
│
└── // === V3: SPAWN COLUMN ANIMATION ===
    ├─ .character.is-spawning-column  (위 -10% 시작 → 중앙 이동)
    └─ @keyframes spawn-column-fall { 0%: translateY(-50vh); 100%: translateY(0); }
```

```
index.html (~125줄, -3 from v2 — HUD 단순화)
├── ... v2 100% 그대로 (intro, game, end view 구조)
├── HUD 부분만 변경:
│   <header class="hud">
│     <button id="pause-btn" disabled>‖</button>
│     <span class="hud__progress">Q.<span id="q-num">1</span></span>
│     <span class="hud__score">⭐ <span id="score">0</span></span>     <!-- [v3] -->
│     <span id="alive-display" class="hud__alive">                      <!-- [v3] -->
│       <span id="alive-count">50</span>
│     </span>
│   </header>
│   (라이프 ❤️ 영역 v2에서 이미 제거됨, 변경 없음)
└── End view에 grand-slam 시 추가 코인 12개 동적 추가 (JS로)
```

**Pros**:
- v2 학습자가 모든 v3 추가를 즉시 식별 (`// === V3 ... ===`)
- 기존 v2 코드 95% 그대로 → 회귀 리스크 최소
- Grand Slam은 win 분기의 **확장**이므로 4분기로의 전환이 자연스러움
- V1-V4가 각각 독립 모듈 → 60fps 미달 시 개별 비활성화 가능

**Cons**:
- 단일 파일이 ~945줄로 커짐 (v1 616 → v3 945, 53% 증가)
- v4 카테고리 추가 시 분리 필요할 수 있음 (그때 모듈화 검토)

---

## 3. Data Model

### 3.1 State Schema (v3 신규 항목만)

```js
Game.state = {
  ...v2 모든 필드,

  // [v3] 신규
  consecutiveCorrect: number,    // 현재 연속 정답 수 (오답 시 0)
  allCorrect: boolean,           // 한 번이라도 오답이면 false (Grand Slam 자격)
}
```

**상태 전이**:
- 게임 시작 시: `consecutiveCorrect = 0`, `allCorrect = true`
- 매 라운드 정답: `consecutiveCorrect += 1` (allCorrect 변경 없음)
- 매 라운드 오답: `consecutiveCorrect = 0`, `allCorrect = false`
- 게임 종료: 그대로 보존 (다음 게임은 resetState로 초기화)

### 3.2 New Constants

```js
const GRAND_SLAM_THRESHOLD = 4;       // 4라운드 무패 + 최후의 1인 (Bernoulli simulate에서 SC-V3-01 충족 sweet spot)
const SPAWN_LANE_PATTERN = 'column';   // 'random' (v2) | 'column' (v3 default)
const SPAWN_COLUMN_DURATION_MS = 1500; // 위→중앙 등장 시간

// NPC 곡선 완화 (T1)
const NPC_ACCURACY_CURVE = [0.30, 0.42, 0.50, 0.55, 0.60, 0.62, 0.64, 0.65];
// (v2: [0.35, 0.50, 0.58, 0.62, 0.66, 0.69, 0.71, 0.72])
```

### 3.3 GA4 Event Schema (v3 추가)

| Event | v2 | v3 |
|-------|-----|-----|
| `game_start` | mode, start_alive | + `npc_curve: 'eased'` |
| `answer_o`/`answer_x` | ... | + `consecutive_correct: number` |
| `game_end_grand_slam` (신규) | — | `survived_rounds, consecutive_correct, duration_sec, score, ranking: 1` |
| `share_click` | method, result: 'win'\|'lose' | + result: 'grand_slam' 분기 |

---

## 4. UI/UX Design

### 4.1 Grand Slam End Screen

```
┌──────────────────────────────────────┐
│       🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙       │  ← 코인 비 12개 (v2 그대로)
│       🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙🪙       │  ← [v3] 추가 12개 (코인 비 ×2)
│                                      │
│        👑 GRAND SLAM! 👑               │  ← 골든 그라디언트 텍스트
│                                      │
│    ⭐ ⭐ ⭐ ⭐ ⭐                        │  ← 별 5개
│                                      │
│  [😊 (golden glow halo)]              │  ← 챔피언 캐릭터 + 골든 글로우 (눈빛)
│                                      │
│  Q.11까지 무패 + 최후의 1인!           │  ← 메인 카피
│  ⭐ 11 · 50명 중 1등 (perfect)        │  ← 보조 정보
│                                      │
│  [📤 친구한테 자랑하기]                │
│  [🔄 다시 풀기]                        │
└──────────────────────────────────────┘
```

### 4.2 Grand Slam Share Text

`🏆 OX 서바이벌 GRAND SLAM 달성! 11라운드 무패 + 최후의 1인! 너도 도전 → {url}`

### 4.3 HUD 단순화 (V2)

**v2**:
```
┌─────────────────────────────────────────┐
│  ‖   Q.7      살아남음 32/50    점수 4  │
└─────────────────────────────────────────┘
```

**v3**:
```
┌─────────────────────────────────────────┐
│  ‖   Q.7         ⭐ 4         👥 32     │
└─────────────────────────────────────────┘
```

- 살아남음 카운터 텍스트 `32/50` → `👥 32` (보조 표기)
- 점수 텍스트 `점수 4` → `⭐ 4`
- aria-live 그대로 유지 (`aria-label="살아남은 인원"`)

### 4.4 "나" 노란 캡슐 (V3)

```
   ┌──┐
   │나│   ← 노란 캡슐, 9px Black Han Sans
   └──┘
    👤    ← 플레이어 sprite (is-me 큰 사이즈)
```

CSS pseudo-element `::before`로 sprite 위 -16px 위치에 표시. JS 불필요.

### 4.5 캐릭터 세로 일렬 spawn (V1)

```
시간 0ms: 화면 위 -10vh에서 50명이 가로 일렬로 대기
         (너무 많으면 일부는 위로 더 올라감, baseY로 시간차 부여)

시간 ~1500ms: 모든 캐릭터가 baseY 위치에 도달
            (이후 v2 동일 — zone center 이동)
```

CSS animation `spawn-column-fall`: `translateY(-50vh) → translateY(0)` over 1.5s, ease-out.

---

## 5. Test Plan

### 5.1 L1 — Unit / Console (Game.simulate)

| ID | Test | Expected |
|----|------|----------|
| L1-V3-01 | `Game.simulate(10000)` Grand Slam 도달률 | 5-15% (50% 정답률 사용자) |
| L1-V3-02 | `Game.simulate(10000)` 평균 라운드 | 4-7 (50% 정답률 사용자) |
| L1-V3-03 | `state.consecutiveCorrect` 정답 시 +1, 오답 시 0 | 단계별 추적 |
| L1-V3-04 | `state.allCorrect` 한 번이라도 오답 시 false | 기록 |
| L1-V3-05 | `isGrandSlam()` 11회 정답 + alive=1 시 true | true |
| L1-V3-06 | `isGrandSlam()` 한 번 오답 + 이후 11회 정답 | false (allCorrect=false) |

### 5.2 L2 — UI Action (Chrome DevTools 수동)

| ID | Scenario | Pass Criteria |
|----|----------|---------------|
| L2-V3-01 | 11라운드 모두 정답 → Grand Slam 화면 | "👑 GRAND SLAM!" 표시, 코인 비 24개, 골든 글로우 |
| L2-V3-02 | 10라운드 정답 + 11라운드 오답 → win/lose 분기 | win-grand-slam은 안 보임 |
| L2-V3-03 | spawn 시 캐릭터 위→중앙 이동 (1.5s) | 60fps 유지 |
| L2-V3-04 | HUD 라이아웃 `Q.X ⭐K 👥N` | 디자인 일치 |
| L2-V3-05 | 플레이어 sprite "나" 캡슐 | head 위 -16px 노란 |
| L2-V3-06 | Grand Slam 공유 텍스트 | `🏆 GRAND SLAM` 포함 |
| L2-V3-07 | iPhone 12 시뮬레이터 1게임 | 모든 V1-V4 적용 시 frame drop < 5% |

### 5.3 L3 — E2E (옵션)

본 MVP는 수동 테스트 우선.

---

## 6. Module Map (Plan §7과 동일)

| ID | Module | Files Touched | LOC |
|----|--------|---------------|-----|
| **M1** | state-grand-slam | script.js (CONSTANTS, STATE, resetState) | +10 |
| **M2** | grand-slam-trigger | script.js (revealAnswer 1줄) | +8 |
| **M3** | end-fourth-branch | script.js (checkEndCondition, COPY 테이블) | +12 |
| **M4** | grand-slam-effects | style.css (keyframes + .end[data-result="win-grand-slam"]) | +25 |
| **M5** | analytics-v3 | script.js (game_end_grand_slam) | +5 |
| **M6** | npc-curve-easing | script.js (NPC_ACCURACY_CURVE 1행 변경) | +3 |
| **M7** | hud-simplify | script.js (renderHUD), index.html (HUD 라이아웃), style.css (HUD 그리드) | +10 -8 |
| **M8** | me-label | style.css (.is-me::before) | +12 |
| **M9** | spawn-column | script.js (applyColumnSpawn), style.css (@keyframes spawn-column-fall) | +30 |
| **Total** | | | **+90 / -8 ≈ 순증 +82** |

### Implementation Order (의존성)

```
M1 (state) → M2 (track) → M3 (end-branch) → M5 (analytics)
                                           ↓
                          M4 (effects-css) ← (병렬 가능)
                                           ↓
M6 (curve) ────────────────────────────────┴→ T1 시뮬레이션 검증
M7 (hud) → M8 (me-label) ← 독립
M9 (spawn-column) ← 독립
```

### 11.3 Session Guide

| Session | Scope | 예상 시간 | 산출물 검증 |
|---------|-------|-----------|-------------|
| **S1** | M1, M2, M3, M5, M6 | ~30분 | 콘솔 시뮬 → Grand Slam 도달률 5-15% 확인 |
| **S2** | M4 | ~25분 | Grand Slam 화면 시각 확인 (콘솔에서 강제 트리거) |
| **S3** | M7, M8 | ~25분 | HUD 단순화 + "나" 캡슐 시각 확인 |
| **S4** | M9 | ~30분 | 50 sprite 위→중앙 이동 60fps 유지 |

전체: ~110분 (~2시간).

---

## 7. Open Questions Resolution (Plan §9)

Plan 6개 Open Question 결정:

| # | 질문 | 결정 |
|---|------|------|
| 1 | Grand Slam 시각 연출 강도 | **코인 비 ×2 + 골든 글로우 + 골든 텍스트** (3중 강조). 풀스크린 햇살은 과함. |
| 2 | 세로 일렬 적용 범위 | **모든 라운드 적용** (단순함 우선). 사용자 토글은 v4에서. |
| 3 | HUD 인원 카운터 완전 제거? | **`👥 N` 보조 표기 유지** (접근성·≤10 위급 시각 둘 다 살림) |
| 4 | "나" 캡슐 위치 | **head 위 -16px** (가장 자연스러움. 캐릭터 종류 무관) |
| 5 | NPC 곡선 vs Grand Slam Threshold 우선순위 | **곡선 완화 먼저 적용 → simulate 결과 보고 Threshold 11 고정 또는 12-13으로 조정** |
| 6 | 공유 문구 시간 강조? | **시간 미강조** — 정답 11개 + GRAND SLAM 강조만. 시간은 자랑 동기로 약함 |

---

## 8. Migration Checklist (v2 → v3)

- [ ] state에 `consecutiveCorrect`, `allCorrect` 추가
- [ ] resetState에서 둘 다 초기화 명시 추가
- [ ] NPC_ACCURACY_CURVE 값 교체 (`[0.35→0.72]` → `[0.30→0.65]`)
- [ ] revealAnswer 끝에 `Game.trackCorrectness(playerCorrect)` 1줄 추가
- [ ] checkEndCondition의 win 분기를 `'win-grand-slam' OR 'win'`으로 split
- [ ] renderEnd COPY 테이블에 `'win-grand-slam'` 행 추가
- [ ] endGame eventName 분기 확장 (win-grand-slam → game_end_grand_slam)
- [ ] buildShareText에 `'win-grand-slam'` 분기 추가
- [ ] index.html HUD 라이아웃 변경 (`살아남음 N/50` → `⭐K  👥N`)
- [ ] style.css `.end[data-result="win-grand-slam"]` 신규 styling
- [ ] style.css `.is-me::before` "나" 캡슐
- [ ] style.css `@keyframes spawn-column-fall`
- [ ] simulate 함수에 grandSlams 카운트 추가
- [ ] (검증) `Game.simulate(10000)` 결과 SC-V3-01/02 충족

---

## 9. Approval Checklist

- [x] Architecture Option C 선택 (v2 일관성)
- [x] 6개 Open Question 모두 결정 (§7)
- [x] State 스키마 설계 (§3.1)
- [x] Grand Slam 시각 연출 + HUD 단순화 + "나" 캡슐 + 세로 일렬 spawn 4가지 전부 설계 (§4)
- [x] Module Map + Session Guide (§6)
- [x] Migration Checklist (§8)
- [ ] Do 단계 진입 준비

---

**Next Step**: `/pdca do survival-mode-v3` (전체) 또는 `/pdca do survival-mode-v3 --scope M1,M2,M3,M5,M6` (S1만)
