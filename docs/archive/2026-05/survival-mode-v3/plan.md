# survival-mode-v3 Planning Document

> **Summary**: v2 일명 제일 — Grand Slam 시스템(P1) + 시각 보강 4건 + NPC 곡선 완화. 콘텐츠 깊이 ↑↑, SC-V2-02 미달 보정.
>
> **Project**: OX퀴즈게임
> **Version**: 0.3.0 (v3 일명 제일 + 시각 톤 강화)
> **Author**: kakaiuina@gmail.com
> **Date**: 2026-05-10
> **Status**: Draft (Plan Phase, PDCA Cycle 3)
> **Upstream**: [v2 Plan](./survival-mode-v2.plan.md) (메커니즘 그대로 상속), [영상 분석 리포트](../../00-pm/reference-video-analysis-2026-05-10.report.md) (v3 스코프 결정 근거)
> **Predecessor**: [v2 Design](../../02-design/features/survival-mode-v2.design.md), [v2 Report](../../04-report/features/survival-mode-v2.report.md)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | v2 (matchRate 94.8%, simplified)는 50인 서바이벌 메커니즘은 잘 구현했지만, 영상 분석 결과 ① SC-V2-02(평균 라운드 6~12) 미달(실측 1.98~3.57) ② 재플레이 동기 부족(원본의 Grand Slam 같은 도전 과제 미구현) ③ 시각 톤 일부 미스(원본은 "줄지어 달리다 분기" vs 우리는 산개 + 인원 카운터 텍스트). |
| **Solution** | (P1) Grand Slam 시스템 추가: 11라운드까지 무탈락 정답 시 종료 화면 4번째 분기 + 코인비 강화 + 전용 공유 문구. (V1) 캐릭터 세로 일렬 배치(러닝 줄) + (V2) HUD 단순화 + (V3) "나" 노란 캡슐 + (V4) 점수 ⭐ 아이콘화. (T1) NPC 곡선 [0.35→0.72]→[0.30→0.65]로 완화해 평균 라운드 ↑. |
| **Function/UX Effect** | "11라운드 정답 = 천재" 도전 과제로 재플레이 동기 추가. 시각적으로 영상 톤에 더 가까워짐. SC-V2-02 미달 보정으로 1게임 ≈ 1.5-2분으로 안정화. |
| **Core Value** | 사용자: "한 판 더!" 동기 확보 + "Grand Slam = SNS 자랑". 사업: v2 대비 share_click + 재방문 +20% 목표. v2 인프라 유지 (정적·무회원·GitHub Pages). |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | v2 컨셉은 OK이나 도전 과제 부재로 1회 플레이 후 이탈. 영상 원본은 11라운드 Grand Slam으로 재플레이 동기 형성. |
| **WHO** | v2와 동일 — SNS 자취생/20대 (페르소나 박지원). 변경 없음. |
| **RISK** | (1) Grand Slam 트리거 빈도 너무 낮으면 도전 자체가 비현실적, (2) 시각 보강이 v2 50fps 성능 저하 야기, (3) NPC 곡선 완화로 라운드가 너무 길어져 도파민 약화, (4) 캐릭터 세로 일렬 배치가 모바일 세로에서 부자연스러움. |
| **SUCCESS** | (a) Grand Slam 도달률 5-15% (시뮬레이션 기준), (b) 평균 라운드 4-7회 (v2 1.98~3.57 → +50%), (c) 시각 보강 후 60fps 유지 (NFR-V2-01 그대로), (d) share_click v2 대비 +20%. |
| **SCOPE** | **포함**: Grand Slam 시스템(P1), 캐릭터 세로 일렬(V1), HUD 단순화(V2), "나" 말풍선(V3), 점수 ⭐(V4), NPC 곡선 완화(T1). **불포함**: 카테고리 시스템(P2 — v4), 100명 모드(P3 — v4), 메인 메뉴 시스템(v4). |

---

## 1. Overview

### 1.1 Purpose

v2 (matchRate 94.8%) 출시 후 재플레이 동기 부족이 핵심 문제. 영상 정밀 분석(`docs/00-pm/reference-video-analysis-2026-05-10.report.md`)에서 원본 게임의 핵심 도파민 트리거가 **"11라운드 Grand Slam = 특별 보상"**이라는 사실 확인. v3는 이 단일 메커니즘 추가 + 시각 톤 보강 + NPC 곡선 완화로 v2의 한계를 보정한다.

### 1.2 Background

- **v2 학습**: matchRate 94.8%, M1~M10 모두 구현 완료. simulation 결과 평균 라운드 1.98(50% 정답률 사용자)~3.57(75% 정답률 사용자) — SC-V2-02 미달.
- **영상 분석 발견**: 원본은 평균 11라운드 / 약 2분 안정 설계. Grand Slam (11라운드 정답)이 핵심 재플레이 트리거.
- **재사용 자산**: v2의 모든 코드(state.alive, NPC 곡선, 4종 이펙트, zone, 러닝 BG, 종료 3분기) 100% 상속. v3는 추가만, 기존 변경 최소.

### 1.3 Related Documents

- **영상 분석 리포트**: `docs/00-pm/reference-video-analysis-2026-05-10.report.md` — P1/P2/P3 후보 + 시각 보강 4건 정의
- **상세 영상 분석**: `_refs/video-analysis-v2.md` — 6 HQ 프레임 + 비교표 + 미해결 5건
- **v2 Plan**: `docs/01-plan/features/survival-mode-v2.plan.md` — 메커니즘 그대로 상속
- **v2 Design**: `docs/02-design/features/survival-mode-v2.design.md` — Option C 단일 파일 구조
- **v2 Report**: `docs/04-report/features/survival-mode-v2.report.md` — Lessons Learned (SC-V2-02 미달 원인)
- **v2 Analysis**: `docs/03-analysis/survival-mode-v2.analysis.md` — Match Rate 94.8% gap 목록

---

## 2. Scope

### 2.1 In Scope (v3 추가 항목)

#### P1. Grand Slam 시스템
- [ ] state.consecutiveCorrect 추적: 매 라운드 정답 시 +1, 오답 시 리셋
- [ ] state.allCorrect: 모든 라운드 정답 boolean (한 번이라도 오답이면 false)
- [ ] 종료 시 4분기 분기 추가:
  - **`win-grand-slam`**: alive.size === 1 && alive.has(0) && consecutiveCorrect >= GRAND_SLAM_THRESHOLD (=11)
  - 기존 win/lose-survivor/lose-ranking은 그대로
- [ ] Grand Slam 시각 연출:
  - 코인 비 2배 (12개 → 24개)
  - "👑 GRAND SLAM!" 메인 텍스트
  - 골든 글로우 애니메이션 (champion 캐릭터 주변)
  - 별 아이콘 ⭐⭐⭐⭐⭐ 표시
- [ ] Grand Slam 전용 공유 문구: `🏆 OX 서바이벌 GRAND SLAM! 11라운드 무패 + 최후의 1인! 너도 도전 → {url}`
- [ ] GA4 이벤트: `game_end_grand_slam` 신규 (`survived_rounds, consecutive_correct, duration_sec`)

#### V1. 캐릭터 세로 일렬 배치 (러닝 줄)
- [ ] spawnAllOnce 시 NPC들의 baseY를 **시간 차로 부여** (각 NPC가 다른 Y에서 시작)
- [ ] 새 상수 `SPAWN_LANE_PATTERN`: 'random' (v2 그대로) | 'column' (v3 신규, 세로 일렬)
- [ ] column 모드: NPC들이 화면 위에서 시작 → 1.5초 동안 화면 중앙으로 이동 → 라운드 시작
- [ ] zone 선택 시점에서는 v2와 동일 (좌우 zone center로 이동)

#### V2. HUD 단순화 (그룹 시각 우선)
- [ ] 살아남음 카운터를 **메인이 아닌 보조 표기**로 격하
- [ ] 라이아웃 변경: `Q.{idx}    살아남음 {n}    점수 {k}` → `Q.{idx}    ⭐{k}    👥{n}`
- [ ] aria-live는 그대로 유지 (접근성)

#### V3. "나" 노란 말풍선 캡슐
- [ ] `.character.is-me::before` 가짜 element로 "나" 라벨 표시
- [ ] 노란 배경 (`var(--bg-victory)` `#fdd835`) + 검은 글자 + 둥근 캡슐 + 살짝 아래로 살짝 (sprite 위에)
- [ ] 게임 진행 중에만 표시 (탈락 시 fade out)

#### V4. 점수 ⭐ 아이콘화
- [ ] HUD 점수 텍스트 `점수 N` → `⭐ N` (이모지 또는 SVG)
- [ ] 종료 화면도 동일 적용

#### T1. NPC 정답률 곡선 완화
- [ ] `NPC_ACCURACY_CURVE`: `[0.35, 0.50, 0.58, 0.62, 0.66, 0.69, 0.71, 0.72]` → `[0.30, 0.42, 0.50, 0.55, 0.60, 0.62, 0.64, 0.65]`
- [ ] 시뮬레이션 (`Game.simulate(10000)`)으로 평균 라운드 4-7회 / Grand Slam 도달률 5-15% 검증
- [ ] 검증 통과 못 하면 곡선 추가 조정 (50% 정답률 사용자 기준)

### 2.2 Carry-Over (v2에서 그대로 유지)

- 50인 서바이벌 메커니즘 (M1-M10 전부)
- 4종 탈락 이펙트 (fall/poof/floor-crack/rocket)
- 위→아래 러닝 배경
- 라운드 테마 6종 (5문항마다 변경)
- zone 분할 (좌 O 청록 / 우 X 빨강 + 점선)
- GA4 + UTM (이벤트만 grand_slam 신규 추가)
- CSV 200문항 풀 (`data/questions_v1.csv`) — Plan 단계에선 기존 그대로
- 만화체 폰트, 만화풍 sprite 풀 24종
- 종료 3분기 (win/lose-survivor/lose-ranking) — Grand Slam은 4번째로 추가
- GitHub Pages 배포

### 2.3 Out of Scope (v4+ 이월)

- **카테고리/레벨 시스템 (P2)**: CSV 카테고리 컬럼 + 메인 메뉴 화면. 영상 원본의 핵심이지만 코드 ~150 LOC + UI + 콘텐츠 작업 필요. v4 후보 1순위.
- **100명 모드 (P3)**: 50/100 토글 + sprite 크기 조정. v4 후보 2순위.
- **가상 화폐**: 다이아/코인/입장료. 백엔드 도입 후 v5+ 검토.
- **친구 룸 / 멀티**: 영상의 "동네퀴즈대회" 모드. 백엔드 도입 후 검토.
- **회원/DB**: v2 정책 유지.

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Description | Priority | Source |
|----|-------------|----------|--------|
| FR-V3-01 | 매 라운드 정답 시 `state.consecutiveCorrect` +1, 오답 시 0 리셋 | P0 | §2.1 P1 |
| FR-V3-02 | `state.allCorrect` boolean: 한 번이라도 오답이면 false 고정 | P0 | §2.1 P1 |
| FR-V3-03 | 종료 시 4번째 분기 `win-grand-slam` 추가 (alive=1 + player + consecutiveCorrect ≥ 11) | P0 | §2.1 P1 |
| FR-V3-04 | Grand Slam 시각 연출 (코인 비 2배, 골든 글로우, 👑 텍스트, ⭐⭐⭐⭐⭐) | P0 | §2.1 P1 |
| FR-V3-05 | Grand Slam 전용 공유 문구 + GA4 `game_end_grand_slam` 이벤트 | P0 | §2.1 P1 |
| FR-V3-06 | 캐릭터 세로 일렬 spawn 모드 ('column'), 1.5초 등장 애니메이션 | P1 | §2.1 V1 |
| FR-V3-07 | HUD 단순화: `⭐{k}  👥{n}` 라이아웃, 살아남음을 보조 표기로 | P1 | §2.1 V2 |
| FR-V3-08 | 플레이어 sprite에 "나" 노란 캡슐 라벨 (CSS pseudo-element) | P1 | §2.1 V3 |
| FR-V3-09 | 점수 ⭐ 아이콘 (HUD + 종료 화면) | P2 | §2.1 V4 |
| FR-V3-10 | NPC_ACCURACY_CURVE 완화 [0.30, 0.42, 0.50, ...] | P0 | §2.1 T1 |
| FR-V3-11 | simulate(10000) 검증: Grand Slam 도달률 5-15%, 평균 라운드 4-7 | P0 | §2.1 T1 |

### 3.2 Non-Functional Requirements

| ID | Description | Target |
|----|-------------|--------|
| NFR-V3-01 | 시각 보강 후 모바일 60fps 유지 | iPhone 12 / 갤럭시 S20 기준, 동일 조건 |
| NFR-V3-02 | 추가 코드량 | script.js +60~90줄 (855 → 920~945), style.css +30~50줄, index.html ±5줄 |
| NFR-V3-03 | v2와의 행동 호환성 | 50% 정답률 사용자 기준 평균 라운드 v2 1.98 → v3 4-7 (정확히 SC-V2-02 미달 해소) |
| NFR-V3-04 | 접근성 | aria-live 유지 (HUD 단순화에도 살아남음 인원 변경 시 screen reader 알림) |
| NFR-V3-05 | CSP | v2 정책 유지 (인라인 style 추가 X, class 기반 효과만) |

### 3.3 Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-V3-01 | Grand Slam 도달률 5-15% (50% 정답률 사용자 기준) | Game.simulate(10000) 출력 |
| SC-V3-02 | 평균 라운드 4-7회 (50% 정답률 사용자) | Game.simulate(10000) 출력 |
| SC-V3-03 | NFR-V3-01 (60fps) 시각 보강 후 유지 | Chrome DevTools Performance, frame drop < 5% |
| SC-V3-04 | 코드 +60~90 LOC 내 (NFR-V3-02 충족) | wc -l 비교 |
| SC-V3-05 | matchRate ≥ 90% (gap-detector 정적 분석) | analyze 단계 자동 측정 |
| SC-V3-06 | (출시 후) share_click v2 대비 +20% | GA4 (배포 후 1주 측정) |

---

## 4. Architecture (개략)

> 상세는 Design 단계에서 3가지 옵션 비교. 여기선 v2 대비 변경 영역만 정리.

| Layer | v2 | v3 변경 |
|-------|----|---------|
| **State** | `consecutiveCorrect` 없음 | `consecutiveCorrect: number`, `allCorrect: boolean` 신규 |
| **Constants** | `NPC_ACCURACY_CURVE [0.35→0.72]` | `[0.30→0.65]` 완화. 새 상수 `GRAND_SLAM_THRESHOLD = 11`, `SPAWN_LANE_PATTERN = 'column'` |
| **Spawn** | 산개 (`SPRITE_Y_MIN_PCT~MAX`) | 'column' 모드: 화면 위에서 시작 → 1.5s 중앙 이동 |
| **Reveal** | 정답 처리 + alive 갱신 | + consecutiveCorrect 추적, allCorrect 갱신 |
| **End** | 3분기 (win/lose-survivor/lose-ranking) | 4분기 (+ win-grand-slam) |
| **HUD** | `Q.X 살아남음 N/50 점수 K` | `Q.X ⭐K 👥N` (단순화) |
| **Player Sprite** | `is-me` class (CSS) | + `::before` 노란 "나" 캡슐 |
| **Effects** | 4종 이펙트 그대로 | 변경 없음 (Grand Slam 골든 글로우만 추가 keyframe) |
| **GA4** | `game_end_win/lose/...` | + `game_end_grand_slam` |

### 4.1 v2 재사용 코드 비율

- 데이터 레이어: **100%** 재사용
- GA4 / UTM: **95%** 재사용 (grand_slam 이벤트만 추가)
- 라운드 진행: **100%** 재사용
- 종료 화면 분기: **75%** 재사용 (win 분기를 win/win-grand-slam으로 분리만)
- Spawn / Movement: **80%** 재사용 (column 모드만 추가, random은 그대로)
- HUD: **70%** 재사용 (라이아웃만 변경)
- 4종 이펙트: **100%** 재사용

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Grand Slam 트리거 빈도가 너무 낮음 (도달률 < 1%) | Medium | High | T1 NPC 곡선 완화 + simulate(10000) 검증으로 5-15% 조정 |
| Grand Slam 트리거 빈도가 너무 높음 (도달률 > 30%) | Low | Medium | "특별함" 약화. simulate 결과 보고 GRAND_SLAM_THRESHOLD를 12-13으로 조정 |
| 캐릭터 세로 일렬(V1) 시각이 모바일 세로에 부자연스러움 | Medium | Medium | Design 단계에서 'random' vs 'column' 사용자 토글 옵션도 검토. 또는 'column'을 portrait 시 스킵하고 landscape에만 적용 |
| HUD 단순화(V2)로 인원수 인지 어려움 | Low | Low | aria-live 유지 + 인원 ≤ 10일 때 빨강 깜빡 그대로 (위급 시각 유지) |
| 시각 보강이 60fps 저하 (NFR-V3-01 미달) | Low | High | 각 V1-V4를 독립 모듈로 구현 → simulate 측정 시 1개씩 끄고 측정 가능. 미달 시 가장 무거운 것 제거 |
| NPC 곡선 완화(T1)로 라운드가 너무 길어짐 (평균 > 8) | Medium | Medium | 곡선 cap을 0.65 대신 0.68로 미세 조정 |
| Grand Slam 추적 state 누락으로 v2 호환성 깨짐 | Low | High | resetState에서 명시적 초기화 + Design 단계 마이그레이션 체크리스트 |

---

## 6. Analytics (v3 추가)

v2 6개 이벤트 그대로 + 신규 1건.

| Event | v2 | v3 |
|-------|-----|-----|
| `game_start` | mode, start_alive | + `npc_curve: 'eased' \| 'v2'` (T1 적용 여부 추적) |
| `answer_o` / `answer_x` | 그대로 | + `consecutive_correct` (현재 연속 정답 수) |
| `round_advance` | 그대로 | 변경 없음 |
| `game_end_win` | 그대로 | 변경 없음 (Grand Slam은 별도 이벤트) |
| `game_end_lose` | 그대로 | 변경 없음 |
| `game_end_grand_slam` (신규) | — | `survived_rounds, consecutive_correct, duration_sec, score` |
| `share_click` | 그대로 | + `result: 'grand_slam'` 분기 추가 |

---

## 7. Implementation Phases

| Phase | Module | 내용 | Est. LOC |
|-------|--------|------|---------|
| M1 | state-grand-slam | state에 `consecutiveCorrect`, `allCorrect` 추가 + resetState 갱신 | +10 |
| M2 | grand-slam-trigger | revealAnswer에서 정답 시 += 1, 오답 시 0 리셋. allCorrect 갱신 | +8 |
| M3 | end-fourth-branch | checkEndCondition에 `win-grand-slam` 분기 + renderEnd COPY 테이블 1행 추가 | +12 |
| M4 | grand-slam-effects | 코인 비 2배, 골든 글로우 keyframe, 👑 텍스트, ⭐⭐⭐⭐⭐ | +25 (CSS) +5 (JS) |
| M5 | analytics-v3 | game_end_grand_slam 이벤트 + share_click result='grand_slam' | +5 |
| M6 | npc-curve-easing | NPC_ACCURACY_CURVE 완화 + simulate 함수 호출로 검증 | +3 (상수만) |
| M7 | hud-simplify | HUD 라이아웃 변경 (`⭐{k} 👥{n}`) + 점수 ⭐ 아이콘화 | +10 -8 |
| M8 | me-label | `.is-me::before` 노란 캡슐 CSS | +12 (CSS) |
| M9 | spawn-column | SPAWN_LANE_PATTERN = 'column' + spawnAllOnce 분기 + 등장 애니메이션 | +30 |
| **Total** | | | **+90 / -8 ≈ 순증 +82** |

---

## 8. Acceptance Test (수동 시나리오)

| ID | 시나리오 | Pass 조건 |
|----|----------|-----------|
| AT-V3-01 | 11라운드 모두 정답 → Grand Slam 화면 | "👑 GRAND SLAM!" 표시, 코인 비 2배, GA4 `game_end_grand_slam` 호출 |
| AT-V3-02 | 10라운드 정답 + 11라운드 정답 → Grand Slam | (위와 동일) |
| AT-V3-03 | 5라운드 정답 + 6라운드 오답 → 일반 win 또는 lose | win-grand-slam 분기 안 탐 |
| AT-V3-04 | 캐릭터 spawn — column 모드 | 1.5초 내 50명이 화면 위→중앙으로 이동 |
| AT-V3-05 | HUD 라이아웃 | `⭐ K  👥 N` 표시, 인원 ≤ 10 시 빨강 깜빡 |
| AT-V3-06 | 플레이어 sprite | "나" 노란 캡슐이 head 위 표시 |
| AT-V3-07 | 점수 표시 | HUD/종료 모두 ⭐ 아이콘 사용 |
| AT-V3-08 | NPC 곡선 검증 | `Game.simulate(10000)` 출력에서 50% 사용자 평균 라운드 4-7 |
| AT-V3-09 | Grand Slam 빈도 | `Game.simulate(10000)` Grand Slam 도달률 5-15% (50% 정답률) |
| AT-V3-10 | 60fps 유지 | Chrome DevTools Performance, V1+V2+V3+V4 적용 후 frame drop < 5% |

---

## 9. Open Questions (Design 단계로 이월)

1. **Grand Slam 시각 연출 강도**: 코인 비 2배 vs 별도 코인 폭발 + 카메라 줌 vs 풀스크린 햇살 광선. (Design에서 prototype)
2. **세로 일렬 배치 적용 범위**: 모든 라운드 vs 첫 라운드만 vs 사용자 토글. (Design에서 결정)
3. **HUD 단순화 — 인원 카운터 완전 제거?**: `⭐K` 만 + 인원은 시각으로만 vs `⭐K 👥N` 둘 다.
4. **"나" 캡슐 위치**: head 위 vs 머리 옆 vs 발밑 (캐릭터 종류마다 균형 다름)
5. **NPC 곡선 완화 vs Grand Slam Threshold 둘 중 어느 것 먼저 튜닝?**: 곡선 우선 → Threshold 후속 vs 동시 진행
6. **Grand Slam 공유 문구 + 시간 강조 추가?**: `🏆 Grand Slam! N초 만에 11라운드` (시간 강조) vs 정답 개수만 강조

---

## 10. Approval Checklist

- [x] Grand Slam 시스템 (P1) 핵심 메커니즘 합의 ✓ (2026-05-10 사용자 확정)
- [x] 시각 보강 4건 (V1-V4) 합의 ✓
- [x] NPC 곡선 완화 (T1) 합의 ✓
- [x] v2 인프라 100% 상속 ✓
- [x] P2 (카테고리)·P3 (100명 모드) v4 이월 명시 ✓
- [ ] Design 단계 진입 준비

---

**Next Step**: `/pdca design survival-mode-v3`
