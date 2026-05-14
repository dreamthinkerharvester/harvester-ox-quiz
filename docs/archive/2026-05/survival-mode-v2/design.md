# survival-mode-v2 Design Document

> **Summary**: v1 단일 파일 구조를 그대로 계승(Option C — Pragmatic Balance) + 새 섹션(ARENA · NPC BEHAVIOR · EFFECTS · RUNNING BG) 추가. 50인 1회 spawn, transform 기반 zone 이동, 4종 랜덤 탈락 이펙트.
>
> **Project**: OX퀴즈게임
> **Version**: 0.2.0
> **Author**: bkit:pdca/design (kakaiuina@gmail.com)
> **Date**: 2026-05-10
> **Status**: Draft (PDCA Cycle 2, Design Phase)
> **Planning Doc**: [survival-mode-v2.plan.md](../../01-plan/features/survival-mode-v2.plan.md)
> **Predecessor**: [v1 Design](./nonsense-quiz-mvp.design.md), [v1 PRD](../../00-pm/nonsense-quiz-mvp.prd.md)

### Pipeline References

| Phase | Document | Status |
|-------|----------|--------|
| Phase 1 (Schema) | v1 design §3 + 본 문서 §3 (state schema 변경) | ✅ |
| Phase 2 (Convention) | v1 design §10 그대로 상속 | ✅ |
| Phase 3 (Mockup) | `_refs/screenshots-description.md` + `_refs/video-analysis.md` (88프레임) | ✅ |
| Phase 4 (API Spec) | 백엔드 없음 (정적) | N/A |

---

## Context Anchor

> v2 Plan에서 복사. Design→Do 핸드오프 시 전략 컨텍스트 보존.

| Key | Value |
|-----|-------|
| **WHY** | v1 메커니즘이 영상 레퍼런스의 "서바이벌 임팩트"를 충분히 못 살림. "1분 도파민 + 즉시 카톡 공유" 강도 강화 |
| **WHO** | v1과 동일 — SNS에서 OX 콘텐츠 본 자취생/20대 (페르소나 박지원, 24세) |
| **RISK** | (1) 50개 sprite 모바일 성능, (2) 라운드 시간 분포 변동성, (3) 첫 문제 오답 즉시 종료 = 신규 이탈, (4) NPC 정답률 튜닝 실패 |
| **SUCCESS** | 모바일 60fps, 평균 세션 ≥2.5분, 평균 라운드 6~12회, 첫 문제 탈락률 ≤25%, 완주 공유율 v1 +30% |
| **SCOPE** | **포함**: 50인 spawn, zone 분할, NPC 1~2회 메번직, 4종 랜덤 이펙트, 라운드 무제한 + 풀 재셔플, 위→아래 러닝 BG. **불포함**: 회원·DB·UGC·멀티·다국어·다크모드 |

---

## Design Anchor

> v1 디자인 토큰 100% 상속 + v2 신규 토큰만 추가.

| Category | v1 (재사용) | v2 신규/변경 |
|----------|-------------|-------------|
| **Colors** | bg-primary `#3a3a3a`, color-O `#29b6f6`, color-X `#ef5350`, bg-victory `#fdd835` | zone-O-overlay: `rgba(41,182,246,0.10)`, zone-X-overlay: `rgba(239,83,80,0.10)`, zone-divider: `rgba(255,255,255,0.4)` 1px dashed, grid-line: `rgba(255,255,255,0.05)` 8px |
| **Typography** | Black Han Sans (제목), Jua (본문) | 변경 없음. 단 alive-count는 Black Han Sans + 큰 사이즈 (`Q.{idx} / 살아남음 ${n}/50`) |
| **Spacing** | 8px 그리드, 카드 24px | sprite 자체 크기 24px(v1 32px → 작아짐, 50명 가독성 위해) |
| **Radius** | OX 버튼 50%, 카드 16px | sprite는 사각 (배경 이미지) 그대로 |
| **Tone** | 만화풍·도파민 친화 | + "서바이벌 긴장감" — alive-count 색상이 30↓시 노랑, 10↓시 빨강 깜빡 |
| **Layout** | 9:16 모바일 우선, max-width 480px | arena 비율 변경: HUD 12% / 문제 18% / **arena 50%** / OX 버튼 20% (arena 35%→50%로 확대) |

---

## 1. Overview

### 1.1 Design Goals

1. **v1 구조 일관성 유지**: 동일한 단일 파일 + 섹션 주석 컨벤션. v1 학습한 사람이 즉시 이해 가능
2. **성능 최우선**: 50개 sprite 동시 렌더 → 1회 spawn + transform 기반 이동 + `will-change: transform`. DOM reflow 최소화
3. **시각 임팩트 ↑↑**: 영상 레퍼런스의 "다중 탈락" 톤을 4종 랜덤 이펙트로 구현. 모든 캐릭터가 같은 방식으로 사라지지 않게
4. **메커니즘 격리**: zone-split / npc-behavior / effects 각각 별도 섹션. v3에서 부분 교체 쉽게
5. **프로그레시브 페일세이프**: NPC 정답률 곡선·첫 라운드 처리 등 모든 게임 밸런스 상수를 한 곳에 모아 튜닝 가능

### 1.2 Design Principles

- **State as Single Source of Truth**: `Game.state.alive`(Set 또는 number 배열) 단일 출처. DOM에서 alive count를 세지 않음 (v1의 recalcBoxCounts 학습)
- **Spawn Once, Move Many**: 50 sprite는 게임 시작 시 1회 생성. 라운드마다 transform으로 좌표만 변경. DOM 트리 변동 0
- **Zone as Visual Only**: 좌/우 zone은 시각 표시 + hit-test 좌표 영역만 의미. DOM 컨테이너로 분할하지 않음 (sprite가 `arena` 직속)
- **Effect as Random Dispatcher**: 4종 이펙트는 동등 확률. 캐릭터별 독립 선택. 시각 통일감을 일부러 깨뜨려 지루함 감소
- **No Framework, No Build, No Bundle**: v1 정책 유지
- **Privacy by Default**: localStorage 미사용 유지. 단, 향후 best score 보존 시 단일 키 `oxsv:best`만 가능 (v3 예정, 본 문서에선 NO)

---

## 2. Architecture Options

### 2.0 Architecture Comparison

3가지 옵션 중 사용자가 **Option C: Pragmatic Balance** 선택 (Checkpoint 3, 2026-05-10).

| Aspect | A (Minimal) | B (Modular) | **C (Pragmatic) ✅** |
|--------|-------------|-------------|---------------------|
| 파일 수 | 3 (v1 그대로) | 7 (modules) | 3 (v1 그대로) |
| script.js 크기 | ~780줄 | 분산 ~900 | ~820줄 |
| 가독성 | 낮음 (v1/v2 섞임) | 높음 (모듈) | 중상 (섹션 분리) |
| 빌드 도구 | 불필요 | type="module" | 불필요 |
| 향후 v3 진화 | 어려움 | 쉬움 | 중간 (섹션 단위 발췌 가능) |
| 구현 속도 | 가장 빠름 | 가장 느림 | 빠름 |
| 학습 곡선 | 낮음 | 중간 | 낮음 |
| **평가** | v1 흔적 잔존 위험 | MVP에 과함 | **v1 일관성 + 정리된 v2** |

### 2.1 Selected: Option C — Pragmatic Balance

```
script.js (단일 파일, ~820줄)
├── // === CONSTANTS ===
│   ├─ 게임 룰: ALIVE_INITIAL=50, NPC_COUNT=49, TIMER_DURATION_SEC=5
│   ├─ NPC 행동: NPC_ACCURACY_CURVE = [0.35, 0.50, 0.58, 0.62, 0.66, 0.69, 0.71, 0.72]
│   ├─ 이펙트: EFFECT_TYPES = ['fall', 'poof', 'floor-crack', 'rocket']
│   └─ 좌표: ZONE_O_X_RATIO=0.25, ZONE_X_X_RATIO=0.75, JITTER_PX=±12
│
├── // === STATE ===  (single source of truth)
│   ├─ questionPool, currentRound, questionIndex, score
│   ├─ roundIndex (NPC accuracy curve 인덱스)
│   ├─ alive: Set<number>  (살아있는 캐릭터 id, 50명 → 0/1/2/.../49)
│   ├─ playerId = 0 (고정), playerEliminated: boolean
│   ├─ playerChoice: 'O'|'X'|null  (마음 변경 가능)
│   ├─ npcs[49]: { id, sprite, currentSide, decideTimes[], element }
│   ├─ answerRevealed, sessionStartedAt, utm, loadError
│   └─ timerHandle, npcTimerHandles[]
│
├── // === BOOTSTRAP ===
│   ├─ init(), parseUTM(), bindIntroHandlers, bindGameHandlers, bindEndHandlers
│   └─ populateIntroCrowd  (v1 그대로 — 인트로는 그대로)
│
├── // === DATA ===  (v1 100% 재사용)
│   └─ fetchCSV, parseCSV, splitCSVLine, validateQuestion, shuffle
│
├── // === ANALYTICS ===  (v1 + v2 페이로드 보강)
│   └─ ga(), parseUTM
│
├── // === GAME LOOP ===
│   ├─ startGame()       (v1 startRound → 명칭 변경, 50명 spawn 1회)
│   ├─ showQuestion(idx) (라운드별: theme · HUD · question · zone reset · timer · NPC schedule)
│   ├─ applyRoundTheme   (v1 재사용)
│   └─ advance()         (다음 라운드 또는 endGame)
│
├── // === ARENA & SPAWN ===  (v2 신규)
│   ├─ spawnAllOnce()           (게임 시작 시 50 sprite 1회 생성)
│   ├─ resetArenaForRound()     (라운드 시작 시: 살아있는 sprite 위치 reset)
│   ├─ positionSpriteInZone(id, side)  (transform: translateX/Y)
│   └─ showZoneOverlays()       (좌/우 zone 색상 활성화 + 점선 표시)
│
├── // === PLAYER INPUT ===
│   ├─ handleBoxClick(side)  (재탭 시 반대편으로 이동)
│   └─ moveToZone(id, side)  (transform 기반 + arrive 애니)
│
├── // === NPC BEHAVIOR ===  (v2 신규)
│   ├─ scheduleNPCDecisions(correctAnswer, roundIdx)
│   │   └─ 각 NPC별:
│   │       1) decide_at_1 = 600~2400ms 랜덤
│   │       2) 50% 확률로 decide_at_2 = decide_at_1 + 1000~2200ms
│   │       3) 매 결정마다: P(정답) = NPC_ACCURACY_CURVE[min(roundIdx, len-1)]
│   ├─ npcDecide(npc, choice)  (transform + waver 시각)
│   └─ getNpcAccuracy(roundIdx)
│
├── // === REVEAL & ELIMINATION ===  (v2 신규)
│   ├─ revealAnswer()
│   │   ├─ 1) timer/NPC 결정 모두 정지
│   │   ├─ 2) zone 시각 피드백 (정답 zone 깜빡, 오답 zone 어두워짐)
│   │   ├─ 3) 오답 zone에 있는 모든 alive id 식별
│   │   ├─ 4) 각각 효과 디스패처 호출 (지연 i*40ms로 순차)
│   │   ├─ 5) state.alive에서 제거
│   │   ├─ 6) 플레이어가 오답이면 playerEliminated = true
│   │   ├─ 7) HUD 갱신 (alive count)
│   │   └─ 8) 해설 토스트
│   └─ checkEndCondition() → endGame(reason)
│
├── // === EFFECTS (탈락 4종 랜덤) ===  (v2 신규)
│   ├─ EFFECT_DISPATCHERS = { fall, poof, floor-crack, rocket }
│   ├─ playEliminationEffect(element)
│   │   └─ const type = EFFECT_TYPES[Math.floor(Math.random() * 4)]
│   │       element.classList.add(`is-eliminated`, `effect-${type}`)
│   │       setTimeout(() => element.remove() OR keep-as-ghost, EFFECT_DURATION_MS[type])
│   └─ EFFECT_DURATION_MS = { fall: 600, poof: 500, 'floor-crack': 800, rocket: 700 }
│
├── // === RUNNING BACKGROUND ===  (v2 신규)
│   ├─ startRunningBg()  (CSS class 'is-running' arena에 추가)
│   ├─ stopRunningBg()
│   └─ (실제 애니는 CSS @keyframes scroll-down 으로 처리)
│
├── // === HUD / END / SHARE ===  (v1 + v2)
│   ├─ renderHUD()  (Q.{idx} · 살아남음 N/50 · 점수 K, 라이프 ❤️ 제거)
│   ├─ switchView, renderQuestion, renderTimer, setBoxesEnabled (v1 재사용)
│   ├─ renderEnd(reason)  (win / lose-survivor / lose-ranking 분기)
│   ├─ buildShareText(reason)  (v2 문구)
│   ├─ share(), showToast (v1 재사용)
│   └─ endGame(reason)  (GA4 이벤트 분기)
│
└── // === RENDER UTILS ===  (v1 boxEl/crowdEl 폐기, 신규 zone helpers)
    └─ zoneOfX(xRatio) → 'O' | 'X'  (sprite 좌표가 어느 zone인지)
```

**Pros:**
- v1 학습자가 즉시 새 섹션을 식별 가능 (v2 신규는 모두 코멘트로 명시)
- 게임 밸런스 튜닝(NPC_ACCURACY_CURVE 등)이 한 곳에 모임
- v3에서 effects나 npc-behavior만 교체 시 섹션 단위 발췌 쉬움
- 빌드 도구 없음 → GitHub Pages 그대로 배포

**Cons:**
- 단일 파일 크기 ~820줄 (v1 616→대폭 증가). 향후 v4쯤엔 모듈 분리 검토 필요
- effects가 CSS와 JS 양쪽에 분산됨 (CSS 키프레임 + JS 디스패처). 통일성 약함

---

## 3. Data Model

### 3.1 State Schema

```js
Game.state = {
  // === 데이터 (v1 재사용) ===
  questionPool: Question[],     // CSV 200문항
  currentRound: Question[],     // 셔플된 라운드 풀 (소진 시 자동 재셔플)
  questionIndex: number,         // 0..currentRound.length-1
  score: number,                 // 플레이어 정답 개수
  utm: { source, medium, campaign },
  sessionStartedAt: ISO8601,
  loadError: string | null,
  view: 'intro'|'game'|'end'|'error',

  // === v2 신규: 서바이벌 ===
  roundIndex: number,            // NPC accuracy curve 인덱스 (0부터)
  alive: Set<number>,            // 살아있는 캐릭터 id 집합 {0(player), 1..49(NPC)}
  playerId: 0,                   // 고정
  playerEliminated: false,
  playerChoice: 'O'|'X'|null,    // 현재 라운드 선택 (마음 변경 가능)

  // === v2 신규: NPC ===
  npcs: NPC[49],                 // 게임 시작 시 1회 생성. 사망 후에도 배열에 남음 (alive에서만 제거)

  // === 라운드 진행 ===
  timerRemaining: number,
  answerRevealed: boolean,
  timerHandle: number | null,
  npcTimerHandles: number[],     // 모든 NPC 결정 타이머
}
```

### 3.2 NPC Schema

```js
type NPC = {
  id: number,                    // 1..49 (0은 player)
  sprite: string,                // CHARACTER_POOL에서 추출
  element: HTMLSpanElement,      // arena의 절대 위치 자식
  basePos: { x: number, y: number },  // arena 내 기본 좌표(러닝 줄)
  currentSide: 'O'|'X'|null,     // 현재 zone (라운드마다 reset)
  decisionsMade: number,         // 0~2 (1~2회 메번직)
}
```

### 3.3 Question Schema (v1 재사용)

```js
type Question = {
  id: number,
  question: string,
  answer: 'O'|'X',
  explanation: string,
  // (선택) difficulty?: 'easy'|'medium'|'hard'  ← 본 v2에선 사용 X
}
```

### 3.4 GA4 Event Schema (v2)

| Event | Params |
|-------|--------|
| `game_start` | `mode='survival_v2', start_alive=50` |
| `answer_o` / `answer_x` | `correct, user_choice, question_id, question_index, round_index, alive_before, alive_after, eliminated_count` |
| `round_advance` (신규) | `round_idx, alive_count` |
| `game_end_win` (신규) | `survived_rounds, score, duration_sec, ranking=1` |
| `game_end_lose` (신규) | `survived_rounds, score, duration_sec, ranking, alive_at_death, reason: 'survivor_left'\|'player_eliminated'` |
| `share_click` | `method, result: 'win'\|'lose'` |

---

## 4. API Specification

백엔드 없음 — 정적 사이트. v1 동일.

다만, GA4 이벤트는 외부 통신이므로 Contract 명시:

| Endpoint | Direction | Payload |
|----------|-----------|---------|
| GA4 collect | client → google-analytics.com | event name + params (위 §3.4) |
| Web Share API | client → device | `{ title, text, url }` |

---

## 5. UI/UX Design

### 5.1 Screen Flow

```
[INTRO]
  ├─ "🆕 50명 서바이벌" 배지 + "준비됐어?" 타이틀
  ├─ 인트로 군중(v1 그대로, 25명 미리보기)
  ├─ "라이프 없음, 한 번 틀리면 끝!" 카피
  └─ [시작하기 ▶]
       ↓
[GAME]
  ├─ HUD: Q.{idx} · 살아남음 N/50 · 점수 K
  ├─ Question text
  ├─ Timer 5s
  ├─ ARENA (50% 화면 비중)
  │   ├─ 위→아래 격자 스크롤 BG
  │   ├─ 좌측 zone(O, 청록 옅게) | 점선 | 우측 zone(X, 빨강 옅게)
  │   └─ 50개 sprite (절대 위치, transform 이동)
  ├─ [O 버튼]  [X 버튼]
  └─ revealAnswer → 4종 랜덤 이펙트 → 다음 라운드
       ↓
[END (3 분기)]
  ├─ WIN: "🥳 최후의 1인 너!" + 코인 비 + WIN 공유 문구
  ├─ LOSE-survivor: "😢 너만 빼고 살아남았어" + 살아남은 NPC 1명 표시
  └─ LOSE-ranking: "Q.{X}에서 탈락. 너 {N}등 / 50" + LOSE-ranking 공유
```

### 5.2 ARENA 좌표 시스템

```
ARENA (CSS contain: layout)
┌──────────────────────────────────────────┐
│ ═════════ 위→아래 격자 BG (스크롤) ═══ │
│                  ╎                      │
│   [O zone]       ╎       [X zone]       │
│   alpha 0.10     ╎       alpha 0.10     │
│                  ╎                      │
│  • • • •  •      ╎      • • •  • •      │
│  • • • • • •     ╎      • • • • • •     │
│  • • • • •       ╎      • • • • •       │
│   ↑ npc sprite (24px) at random Y         │
│                  ╎                      │
│            점선 1px dashed                │
└──────────────────────────────────────────┘
```

**좌표 규칙:**
- ARENA 폭 100%, 높이 ~50vh
- O zone center X = 25%, X zone center X = 75%
- sprite Y 기본값: 게임 시작 시 라운덤 (15%~85% 범위)
- 라운드마다 sprite를 자기 zone center ±jitter(12px)로 transform
- "달리는 느낌" → sprite는 제자리 + 배경이 위→아래 스크롤 (역방향 = sprite 가 아래로 달리는 듯)

### 5.3 Zone Visual

- 비활성 (시간 종료 후): zone overlay 0
- 활성 (라운드 진행 중): 좌/우 zone 색 옅게 (alpha 0.10)
- 정답 발표 시: 정답 zone 1초간 깜빡(alpha 0.30 → 0.10), 오답 zone 0.5초간 어두워짐 (overlay alpha 0 → 0.40 검정)
- 가운데 점선 1px dashed white alpha 0.4

### 5.4 4종 탈락 이펙트 상세

| Type | 시각 | Duration | CSS keyframes | 사용 비율 |
|------|------|----------|---------------|-----------|
| **fall** (v1 재사용) | 회전하며 화면 아래로 추락 | 600ms | `falling` (v1 그대로) | 25% |
| **poof** | scale(0) + opacity 0 + ✦ 텍스트 1개 spawn | 500ms | `poof-shrink` + ::after `poof-burst` | 25% |
| **floor-crack** | 0.2s 정지(균열 ::after) → 추락 | 800ms (200+600) | `crack-pause` → `falling` | 25% |
| **rocket** | translateY(-100vh) + rotate(180deg) | 700ms | `rocket-up` | 25% |

**랜덤 분배**: 단순 `Math.random() * 4 | 0`. 라운드별 가중치 없음 (지루함 감소가 목표 — 분포 균등이 충분).

### 5.5 위→아래 러닝 배경

```css
.arena.is-running {
  background-image: 
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 8px 8px;
  animation: scroll-down 0.8s linear infinite;
}
@keyframes scroll-down {
  from { background-position-y: 0; }
  to   { background-position-y: 8px; }
}
```

prefers-reduced-motion 시 애니메이션 정지 (배경 패턴은 유지).

### 5.6 HUD

```
┌─────────────────────────────────────────┐
│  ‖   Q.7      살아남음 32/50    점수 4  │
└─────────────────────────────────────────┘
  ↑     ↑          ↑               ↑
  pause progress   alive            score
  (disabled v1과 동일)
```

- 살아남음 색상:
  - n > 30: white
  - 10 < n ≤ 30: `#fdd835` (노랑 경고)
  - n ≤ 10: `#ef5350` (빨강) + `is-pulse` 0.6s 깜빡 무한
- 라이프 ❤️ 표시 영역 완전 제거

### 5.7 종료 화면 분기

| 분기 | 트리거 | 화면 | 공유 문구 |
|------|--------|------|-----------|
| **win** | alive.size === 1 && alive.has(0) | "🥳 최후의 1인 너!" + 코인 비 + champion (v1 재사용) | `🥳 50명 OX 서바이벌 최후의 1인! Q.{X}까지 / 정답 K개. 너도 해봐 → {url}` |
| **lose-survivor** | alive.size === 1 && !alive.has(0) | "😢 너만 빼고 살아남았어" + 살아남은 NPC 1명 표시 | `😢 OX 서바이벌, 50명 중 ${ranking}등. 정답 K개. 너도 해봐 → {url}` |
| **lose-ranking** | playerEliminated && alive.size > 1 | "Q.{X}에서 탈락. 너 ${ranking}등 / 50" + 아쉬운 톤 일러 | `OX 서바이벌 50명 중 ${ranking}등 했어. Q.{X}에서 탈락 / 정답 K개. 너도 해봐 → {url}` |

`ranking` 계산: `50 - alive.size + 1` (탈락 시점의 등수 = 살아남은 인원 수보다 1 큰 값)

### 5.8 인트로 화면 변경

- v1 인트로 그대로 + 상단에 `🆕 50명 서바이벌` 배지 (작은 캡슐, 노랑 배경)
- 카피 변경: "라이프 ❤️ 3개로 30문항 도전!" → "라이프 없음. 한 번 틀리면 끝!"
- 시작 버튼 텍스트 동일 ("시작하기 ▶")

---

## 6. Error Handling

v1과 동일 — CSV fetch 실패 / 파싱 실패 / 0문항 → error view + 재시도 버튼.

추가:
- 50개 sprite spawn 중 1개라도 실패 (`createElement` 예외) → 무시하고 진행. NPC 1명 적게 출발 (alive 49명).
- 라운드 진행 중 모든 NPC가 동시에 같은 zone으로 가서 alive 0이 되면 (논리상 불가능하지만) → "모두 탈락" 화면 (lose-survivor 분기 fallback).

---

## 7. Security Considerations

v1과 동일.
- CSP: 인라인 style 추가 없이 class 기반으로 effect 적용 (NFR-V2-06). 단, `transform` 좌표는 inline style로 설정 (CSP 정책상 허용 — `unsafe-inline` 이미 style-src에 있음)
- localStorage 미사용 유지
- GA4 anonymize_ip: true 유지

---

## 8. Test Plan

### 8.1 L1 — Unit Test (수동 console)

| ID | 테스트 | 입력 | 기대 출력 |
|----|--------|------|-----------|
| L1-01 | `getNpcAccuracy(0)` | round 0 | 0.35 |
| L1-02 | `getNpcAccuracy(7)` | round 7 | 0.72 (cap) |
| L1-03 | `zoneOfX(0.2)` | x ratio 0.2 | 'O' |
| L1-04 | `zoneOfX(0.6)` | x ratio 0.6 | 'X' |
| L1-05 | NPC 1000회 결정 시뮬 (round 0) | accuracy 0.35 | 정답률 33~37% (오차 ±2%) |
| L1-06 | 100라운드 게임 시뮬 | NPC_ACCURACY_CURVE | 평균 라운드 6~12, 30라운드 초과 < 5% |
| L1-07 | EFFECT_TYPES 분포 1000회 | random | 각 25%±3% |

### 8.2 L2 — UI Action Test (Chrome DevTools 수동)

| ID | 시나리오 | Pass 조건 |
|----|----------|-----------|
| L2-01 | 시작 버튼 → 50명 spawn | sprite 50개, 1.5초 내, 60fps |
| L2-02 | O 버튼 탭 → "나" 캐릭터 O zone 이동 | transform 적용, arrive 애니 |
| L2-03 | 시간 내 X 버튼 재탭 → "나" X zone으로 | transform 갱신 |
| L2-04 | 5초 종료 → 오답 zone 캐릭터 탈락 | alive count 정확, 이펙트 4종 시각 확인 |
| L2-05 | 살아남은 캐릭터로 다음 라운드 | sprite 위치 reset, NPC 결정 재시작 |
| L2-06 | 플레이어 탈락 → lose-ranking 화면 | "Q.X에서 탈락. 너 N등" 표시 |
| L2-07 | alive=1 && player → win 화면 | 코인 비 + "최후의 1인" |
| L2-08 | alive=1 && NPC → lose-survivor 화면 | 살아남은 NPC sprite 1개 강조 |
| L2-09 | prefers-reduced-motion 모드 | 러닝 BG 정지, 이펙트 단순화 |
| L2-10 | iPhone 12 시뮬레이터 1라운드 풀 플레이 | frame drop < 5% |

### 8.3 L3 — E2E (Playwright, optional)

본 MVP에선 수동 테스트 우선. Playwright 환경 구축은 v3 예정.

### 8.4 NPC 정답률 시뮬레이션 (L1-06 상세)

```js
// 콘솔에서 실행
function simulate(n=100) {
  const results = [];
  for (let i=0; i<n; i++) {
    let alive = 50, round = 0;
    while (alive > 1 && round < 30) {
      const acc = Game.getNpcAccuracy(round);
      // 정답 확률 acc 인 NPC들 → 오답 NPC만 탈락
      const dead = Math.round((alive-1) * (1 - acc));
      // 플레이어도 50% 확률로 정답 가정 (사용자 평균)
      const playerCorrect = Math.random() < 0.5;
      if (!playerCorrect) { results.push({round: round+1, alive: alive-dead, lose: true}); break; }
      alive = alive - dead;
      round++;
    }
    if (alive === 1) results.push({round, alive, win: true});
  }
  return results;
}
```

수용 기준: `simulate(100)`의 평균 round가 6~12, 30 이상 케이스 < 5%.

---

## 9. Clean Architecture (Simplified)

v1과 동일 정책 — 정적 사이트라 layered architecture는 과함. 단, 책임 분리 원칙은 섹션 주석으로 표현.

| Concern | Section | Files |
|---------|---------|-------|
| Domain (게임 룰) | CONSTANTS, STATE, GAME LOOP | script.js |
| Adapters (외부 I/O) | DATA(CSV fetch), ANALYTICS(GA4) | script.js |
| UI (DOM 조작) | ARENA, EFFECTS, HUD/END/SHARE, RUNNING BG | script.js + style.css |
| Composition Root | BOOTSTRAP (init) | script.js |

---

## 10. Coding Convention Reference

v1 §10 그대로 상속. 추가 규칙:

- v2 신규 함수는 모두 `// [v2]` 주석 prefix
- 게임 밸런스 상수(NPC_ACCURACY_CURVE 등)는 CONSTANTS 섹션에만 위치. 함수 내 매직넘버 금지
- effect 클래스명 컨벤션: `effect-{type}` (kebab-case)

---

## 11. Implementation Guide

### 11.1 Module Map

| ID | Module | Files Touched | Sections in script.js |
|----|--------|---------------|------------------------|
| **M1** | state-refactor | script.js | CONSTANTS, STATE |
| **M2** | spawn-once | script.js, style.css | ARENA & SPAWN |
| **M3** | zone-split | script.js, style.css, index.html | ARENA & SPAWN, PLAYER INPUT |
| **M4** | npc-behavior | script.js | NPC BEHAVIOR |
| **M5** | reveal-eliminate | script.js | REVEAL & ELIMINATION |
| **M6** | effects | script.js, style.css | EFFECTS |
| **M7** | running-bg | style.css | (RUNNING BACKGROUND CSS only) |
| **M8** | hud-end-share | script.js, index.html, style.css | HUD/END/SHARE |
| **M9** | analytics-v2 | script.js | ANALYTICS |
| **M10** | qa-tune | script.js (시뮬레이션) | (no production change) |

### 11.2 Implementation Order (의존성 기준)

```
M1 (state) ──┬─→ M2 (spawn) ──┬─→ M3 (zone) ──┬─→ M4 (npc) ──┬─→ M5 (reveal+elim) 
             │                 │                │              │
             └─→ M9 (analytics)│                │              ├─→ M6 (effects)
                               │                │              │
                               └─→ M7 (running) │              ├─→ M8 (hud/end)
                                                │              │
                                                └──────────────┴─→ M10 (qa-tune)
```

### 11.3 Session Guide (multi-session 분할)

`/pdca do survival-mode-v2 --scope <module-id>` 로 부분 구현 가능. 권장 세션 분할:

| Session | Scope | 예상 시간 | 산출물 검증 |
|---------|-------|-----------|-------------|
| **S1** | M1, M2, M9 | ~30분 | 시작 시 50개 sprite가 arena에 등장. analytics 페이로드 console 로그 확인 |
| **S2** | M3, M4 | ~40분 | 플레이어 OX 탭 시 zone 이동 시각 확인. NPC 메번직 시각 확인 (탈락 처리 X) |
| **S3** | M5, M6, M7 | ~50분 | 시간 종료 → 4종 이펙트 랜덤 시각 확인. 러닝 BG 활성. alive 갱신 확인 |
| **S4** | M8 | ~25분 | 종료 화면 3분기, 공유 문구, HUD 색상 변화 |
| **S5** | M10 | ~20분 | 100회 시뮬 → NPC 정답률 곡선 확정 + 첫 문제 처리 결정 |

전체: 약 2시간 30분 (S1~S5 한 번에 가능).

### 11.4 Open Questions Resolution (Plan §9)

Plan 단계의 6개 Open Question을 본 Design에서 모두 결정:

| # | 질문 | 결정 |
|---|------|------|
| 1 | 첫 문제 난이도 고정? | **데이터는 그대로 두고 NPC 정답률만 R1=35%로 낮춤** (사용자가 안전감 = "남들도 많이 틀린다"). CSV 변경 X. SC-V2-03 충족. |
| 2 | NPC 정답률 곡선 | **계단형 cap**: `[0.35, 0.50, 0.58, 0.62, 0.66, 0.69, 0.71, 0.72]` (round 0-7+). 시그모이드보다 직관적·튜닝 쉬움. |
| 3 | zone 시각화 강도 | **활성 시 alpha 0.10 + 가운데 점선 1px dashed white**. 라운드 테마는 arena 외곽 그라디언트 그대로 유지 (zone overlay와 분리). |
| 4 | 러닝 배경 패턴 | **8px 격자 (white alpha 0.05) + 0.8s linear 무한 스크롤**. 라운드 테마와 무관 (단순함). |
| 5 | 인트로 화면 | **v1 인트로 + 상단 "🆕 50명 서바이벌" 배지** + 카피 변경 ("라이프 없음, 한 번 틀리면 끝!"). |
| 6 | 종료 화면 톤 | **3분기**: WIN(코인 비+champion), LOSE-survivor(살아남은 NPC 강조), LOSE-ranking("Q.X에서 탈락 너 N등"). 모두 공유 버튼 + 다시 풀기. |

### 11.5 Migration Checklist (v1 → v2)

- [ ] v1 `state.lives`, `state.boxCount` 삭제
- [ ] v1 `box-o`/`box-x` DOM 컨테이너는 그대로 두되 box__crowd는 비움 (NPC가 arena 직속으로 이동)
- [ ] v1 `boxEl/crowdEl/countEl` 헬퍼 폐기 → `zoneOfX/positionSpriteInZone` 으로 대체
- [ ] v1 `recalcBoxCounts/setBoxCount` 폐기 (alive Set 추적)
- [ ] v1 `index.html` `#count-o`, `#count-x`, `#lives` 제거
- [ ] v1 `final-lives` → `final-ranking` 으로 변경 (라이프 없으므로 등수 표시)
- [ ] v1 `revealAnswer`의 `correctSide`/`wrongSide` 분기는 유지하되, 박스 클래스 토글 → zone overlay 갱신으로 변경

---

## 12. Approval Checklist

- [x] Architecture Option C 선택 (Pragmatic Balance, v1 일관성)
- [x] 6개 Open Question 모두 결정 (§11.4)
- [x] State 스키마 설계 (§3.1)
- [x] 4종 이펙트 + zone 시각 설계 (§5.4, §5.3)
- [x] NPC 정답률 곡선 결정 (R0=35% → R7+=72%)
- [x] Module Map + Session Guide 작성 (§11.1, §11.3)
- [ ] Do 단계 진입 준비

---

**Next Step**: `/pdca do survival-mode-v2` (전체) 또는 `/pdca do survival-mode-v2 --scope M1,M2,M9` (S1만)
