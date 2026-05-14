# survival-mode-v2 Planning Document

> **Summary**: OX퀴즈게임 v2 — 50인 서바이벌 모드. 라이프 폐지, 위→아래 러닝 연출, 1명 남을 때까지 무제한 라운드.
>
> **Project**: OX퀴즈게임
> **Version**: 0.2.0 (v2 전면 메커니즘 변경)
> **Author**: kakaiuina@gmail.com
> **Date**: 2026-05-10
> **Status**: Draft (Plan Phase, PDCA Cycle 2)
> **Upstream**: v1 PRD (`docs/00-pm/nonsense-quiz-mvp.prd.md`) — Beachhead·페르소나·UTM·GA4 컨텍스트 그대로 상속. 메커니즘만 v2로 교체.
> **Predecessor**: [v1 Plan](./nonsense-quiz-mvp.plan.md), [v1 Report](../../04-report/features/nonsense-quiz-mvp.report.md)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | v1 MVP(라이프 3 + 30문항 고정)는 메커니즘이 단조로움. 사용자 영상 레퍼런스(`_refs/video-analysis.md`)의 "100인 서바이벌 OX" 톤을 v1 단순화 형태에서 충분히 살리지 못해 "1분 도파민" 강도와 공유 동기가 약함. |
| **Solution** | 50인 서바이벌 모드 — 모든 캐릭터(플레이어 1 + NPC 49)가 위→아래 러닝하면서 매 문제마다 좌(O)·우(X) 존을 선택. 오답 존 전원 탈락(여러 종 랜덤 이펙트). 1명 남거나 플레이어 탈락 시 종료. 라운드 횟수 무제한. |
| **Function/UX Effect** | 시각 임팩트 ↑↑ (49 NPC 동시 탈락 연출). 긴장감 ↑ (라이프 0, 한 번 틀리면 끝). 공유 동기 ↑ ("50명 중 ○등으로 살아남았다"). v1 GA4·UTM·만화체 폰트·라운드 테마 그대로 유지. |
| **Core Value** | 사용자: "오징어게임/넌센스버전 1분 서바이벌". 사업: SNS funnel 종착지의 도파민 강도 향상 + 영상 레퍼런스 컨셉을 1차 검증. v1과 동일 인프라(GitHub Pages·정적·무회원). |

---

## Context Anchor

> Auto-generated from Executive Summary + v1 PRD. Propagated to Design/Do documents.

| Key | Value |
|-----|-------|
| **WHY** | v1 메커니즘이 영상 레퍼런스의 "서바이벌 임팩트"를 충분히 못 살림. 페르소나(자취생/20대)에게 "1분 도파민 + 즉시 카톡 공유" 강도 강화 필요. |
| **WHO** | v1 PRD §3과 동일 — 1차: SNS에서 OX 콘텐츠 본 자취생/20대 (페르소나 박지원, 24세). 변경 없음. |
| **RISK** | (1) 50개 sprite 동시 렌더 모바일 성능, (2) 1명 남을 때까지 무제한 = 한 세션 시간 분포 변동성 ↑, (3) 라이프 폐지로 첫 문제 오답 시 즉시 종료 = 신규 사용자 이탈 위험, (4) NPC 정답률 튜닝 실패 시 라운드 끝없이 늘어남. |
| **SUCCESS** | (a) 50명 동시 렌더 시 모바일(중급기 기준) 60fps 유지, (b) 평균 세션 ≥ 2.5분(v1 3분 목표 대비 약간 짧아도 OK — 한 번 죽으면 끝이므로), (c) 평균 라운드 6~12회 사이로 NPC 정답률 튜닝, (d) 완주 시(=1명 남음) 공유율 v1 대비 +30%, (e) 첫 문제 오답 즉시 종료 비율 ≤ 25%. |
| **SCOPE** | **포함**: 50인 동시 spawn, 위→아래 러닝 배경, O/X 존 분할, NPC 1~2회 메번직, 다종 탈락 이펙트(랜덤), 라운드 무제한 + 200문항 풀 소진 시 재셔플, 살아남은 N명 표시, 공유 문구 v2(서바이벌 톤). **불포함**: 회원·로그인·DB·마일리지·카테고리 UI·UGC·멀티(v1과 동일). v1 인트로 군중·OG 이미지·라이프 UI(폐지). |

---

## 1. Overview

### 1.1 Purpose

v1 MVP가 1주차 검증을 마치고(matchRate 90.6%, REPORT 완료), 영상 레퍼런스(`_refs/video-analysis.md` — "OX 서바이벌 100인" 88프레임 분석)에서 도출된 "서바이벌 임팩트"를 v1의 단순한 라이프 시스템이 충분히 못 살린다는 판단. v2는 **메커니즘 1가지만 교체**해서 효과를 측정한다(A/B 가능 구조).

### 1.2 Background

- **v1 학습**: matchRate 90.6%, REPORT 완료. 코드/디자인 레이어는 안정. 단, 사용자가 영상 레퍼런스 첨부 후 "서바이벌 임팩트"를 명시 — v1의 "이모지 좌우 분할 + 라이프 -1" 연출은 영상 톤 대비 약함.
- **영상 분석 자료**: `_refs/video-analysis.md` (88프레임), `_refs/screenshots-description.md` (5장 + 라운드 테마 6종)
- **재사용 자산**: v1 코드의 데이터 레이어(CSV 파싱·검증), GA4 통합, 만화체 폰트, 라운드 테마 6종, sprite 풀 24종 — 그대로 상속.

### 1.3 Related Documents

- **v1 PRD**: `docs/00-pm/nonsense-quiz-mvp.prd.md` (321줄, 14절) — Beachhead/페르소나/UTM/GTM/Battlecard 전부 v2 상속
- **v1 Plan**: `docs/01-plan/features/nonsense-quiz-mvp.plan.md` — Out of Scope 항목(회원·DB·UGC 등) v2 동일
- **v1 Design**: `docs/02-design/features/nonsense-quiz-mvp.design.md` — 디자인 토큰·폰트·테마·sprite 풀 v2 재사용
- **v1 Report**: `docs/04-report/features/nonsense-quiz-mvp.report.md` — matchRate 90.6%, 잔여 액션(GA4 ID 교체·CSV 200문항·OG URL)
- **레퍼런스**: `_refs/video-analysis.md` (영상 88프레임 분석), `_refs/screenshots-description.md`
- **데이터**: `data/questions_v1.csv` (v1 그대로 사용, 200문항 풀 소진 시 자동 재셔플)

---

## 2. Scope

### 2.1 In Scope (v2 변경 항목)

#### 메커니즘 변경
- [ ] **50인 동시 spawn**: 게임 시작 시점에 50개 캐릭터(플레이어 1 + NPC 49) 한번만 생성, 라운드마다 재생성하지 않음(성능)
- [ ] **라이프 시스템 폐지**: HUD에서 ❤️ 표시 제거. 한 번 틀리면 즉시 종료
- [ ] **O/X 존 분할 arena**: 매 라운드 arena 가운데 세로 선으로 분할 → 좌측=O 존, 우측=X 존
- [ ] **플레이어 조작**: 하단 O/X 버튼 탭(v1 방식 유지). 시간 내 다시 탭하면 반대 존으로 이동(마음 변경 가능)
- [ ] **NPC 행동**: 각 NPC가 라운드 시작 후 1~2회 "메번직"하는 느낌으로 좌/우 이동. 마지막 위치가 그 NPC의 답.
  - 첫 결정: `decide_at_1 = 600 ~ 2400ms` (랜덤)
  - 두 번째 결정(50% 확률): `decide_at_2 = decide_at_1 + 1000 ~ 2200ms`
  - 정답률: 라운드 N에 비례해 점진 상승 (R1=55%, R2=58%, ..., R10=70% cap) — 후반에 결판이 나도록
- [ ] **시간 종료 → 탈락 처리**: 오답 zone에 있는 모든 캐릭터(NPC + 만약 플레이어도) 탈락
- [ ] **다종 탈락 이펙트(랜덤)**: 캐릭터마다 랜덤하게 1개 효과 적용 (지루함 감소)
  - effect-fall: 추락(v1 falling 재사용)
  - effect-poof: 주저앉으면서 ✦ 먼지구름 + 사라짐
  - effect-floor-crack: 발 밑 바닥 균열 → 0.2초 후 추락
  - effect-rocket: 위로 솟구쳐 사라짐 (역추락, 영상 톤)
  - 비율: 25% / 25% / 25% / 25% (라운드별 가중치는 추후 튜닝)
- [ ] **종료 조건**: `state.alive.length <= 1` OR `state.playerEliminated === true`
  - 살아남은 1명 = 플레이어 → 승리 화면 ("🥳 최후의 1인 너!")
  - 살아남은 1명 = NPC → 패배 화면 ("😢 너만 빼고 살아남았어")
  - 플레이어 탈락 (생존 N명) → 종료 화면 ("Q.X에서 탈락. 너 ○등")
- [ ] **라운드 무제한 + 풀 재셔플**: 200문항 풀 소진 시 다시 셔플해서 계속 (실용상 30라운드 안에 결판 — 추가 라운드는 안전망)
- [ ] **위→아래 러닝 배경**: arena에 격자/체크무늬 배경 패턴이 위→아래로 무한 스크롤(CSS animation `background-position-y`). 캐릭터는 제자리이지만 배경이 움직여서 "달리는 느낌".

#### HUD 변경
- [ ] HUD: `Q.{idx} / 살아남음 {alive}/50 / 점수 {score}` (라이프 ❤️ 제거)
- [ ] 종료 화면 점수 표시: `{Q.X에서 탈락 또는 최후의 1인} / 살아남은 N명 / 정답 K개 (k/x)`

#### 공유 문구 v2
- [ ] WIN: `🥳 50명 OX 서바이벌에서 최후의 1인 됐다 ㅋㅋ {Q.X까지 / 정답 K개}. 너도 해봐 → {url}`
- [ ] LOSE: `😢 OX 서바이벌 50명 중 ○등 했어. {Q.X에서 탈락 / 정답 K개}. 너도 해봐 → {url}`

### 2.2 Carry-Over (v1에서 그대로 유지)

- 200문항 CSV 로드·파싱·검증 로직
- 라운드 테마 6종(grass/ice/desert/cave/storm/final) — 5문항마다 변경
- sprite 풀 24종 + character-me sprite
- 만화체 폰트(Black Han Sans · Jua) + 디자인 토큰(O 청록·X 빨강)
- 5초 카운트다운 타이머 + 경고 색
- GA4 + UTM 통합 (이벤트는 §6에서 v2 보강)
- 인트로 화면 (배경에 "달리는" 캐릭터 군중 시각, 시작 버튼)
- 에러 화면, 토스트, 다시 풀기, 공유 버튼
- 모바일 세로 9:16 우선
- GitHub Pages 배포 (정적)
- 다크모드 미대응

### 2.3 Out of Scope (v1과 동일)

- 회원가입·로그인·DB (Phase 2B)
- 마일리지 경제 (Phase 2B)
- 카테고리 UI (Phase 2A)
- UGC·멀티플레이·다국어·결제·다크모드

### 2.4 v1 → v2 마이그레이션 정책

- v1 코드는 git history에 보존. v2는 **같은 파일을 in-place 수정** (사용자 도메인 1개라 A/B 안 함).
- v1 Plan/Design/Report 문서는 archive 안 하고 `Predecessor` 링크로 보존.
- CSV·assets·favicon은 그대로 사용.

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Description | Priority | Source |
|----|-------------|----------|--------|
| FR-V2-01 | 게임 시작 시 50개 캐릭터(플레이어 1 + NPC 49)를 1회 spawn하고, 라운드마다 재생성하지 않는다 | P0 | §2.1, 성능 |
| FR-V2-02 | 매 라운드 arena를 세로 가운데 선으로 분할해 좌(O)/우(X) 존으로 시각화한다 | P0 | §2.1 |
| FR-V2-03 | 플레이어는 하단 O/X 버튼을 탭해 자기 캐릭터를 해당 zone으로 이동시킨다. 시간 내 재탭 가능 | P0 | §2.1 |
| FR-V2-04 | 각 NPC는 라운드당 1~2회 좌우 이동하며, 정답률은 라운드 N에 비례 상승 (55→70% cap) | P0 | §2.1 |
| FR-V2-05 | 5초 종료 시 오답 zone의 모든 캐릭터(NPC + 플레이어 가능)를 탈락 처리하고 state.alive에서 제거 | P0 | §2.1 |
| FR-V2-06 | 탈락 이펙트는 effect-fall/poof/floor-crack/rocket 중 랜덤 1종 적용 (캐릭터별 독립) | P1 | §2.1, 지루함 감소 |
| FR-V2-07 | 종료 조건: alive ≤ 1 OR 플레이어 탈락. 결과별 종료 화면 분기 (win/lose-by-survivor/lose-by-ranking) | P0 | §2.1 |
| FR-V2-08 | 라운드 횟수 무제한. 200문항 풀 소진 시 자동 재셔플 | P0 | §2.1 |
| FR-V2-09 | arena 배경에 격자 패턴이 위→아래로 무한 스크롤 (러닝 느낌) | P1 | §2.1, 영상 레퍼 |
| FR-V2-10 | HUD에서 라이프 ❤️ 제거. `Q.{idx} / 살아남음 N/50 / 점수 K`로 변경 | P0 | §2.1 |
| FR-V2-11 | 종료 화면 공유 문구 v2 (WIN·LOSE 분기) | P1 | §2.1 |
| FR-V2-12 | 다음 라운드로 넘어갈 때 살아있는 NPC들은 자기 위치 유지(재정렬 X), 탈락 캐릭터의 자리는 비움 | P1 | §2.1, 영상 톤 |

### 3.2 Non-Functional Requirements

| ID | Description | Target |
|----|-------------|--------|
| NFR-V2-01 | 50개 sprite 동시 렌더 모바일 성능 | iPhone 12 / 갤럭시 S20 기준 라운드 전환 시 60fps 유지, GC pause < 100ms |
| NFR-V2-02 | 첫 페인트(인트로 화면 보임) | < 1.5s on 3G |
| NFR-V2-03 | 게임 시작 → 첫 문제 표시 | < 500ms (50 sprite spawn 포함) |
| NFR-V2-04 | 코드 추가량 | script.js +200 ~ +250줄 (기존 616 → 800줄 내외), style.css +100 ~ +150줄 |
| NFR-V2-05 | 접근성 | aria-live 게임 진행 알림(살아남은 수 변경 시), prefers-reduced-motion 시 러닝 배경·탈락 이펙트 단순화 |
| NFR-V2-06 | CSP | 인라인 style 추가 없이 class 기반으로 효과 적용 (v1 정책 유지) |

### 3.3 Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-V2-01 | 50개 sprite 동시 표시 + 위→아래 러닝 배경 | Chrome DevTools Performance: 라운드 전환 시 frame drop < 5% |
| SC-V2-02 | 종료까지 평균 라운드 6~12회 분포 | NPC 정답률 튜닝 후 100회 시뮬레이션 (script unit test) |
| SC-V2-03 | 첫 문제 오답 즉시 종료 비율 ≤ 25% | GA4 이벤트 `game_end` 의 `survived_rounds` 분포 |
| SC-V2-04 | 평균 세션 길이 ≥ 2.5분 (라이프 폐지 영향 흡수) | GA4 engagement_time |
| SC-V2-05 | 완주 시 공유 클릭률 v1 +30% | GA4 `share_click` / `game_end_win` |

---

## 4. Architecture (개략)

> 상세는 Design 단계에서 3가지 옵션 비교. 여기서는 v1 대비 변경 영역만 정리.

| Layer | v1 | v2 변경 |
|-------|----|---------|
| **State** | `state.score / lives / npcs[16]` | `state.alive[]`(50명 통합), `state.playerEliminated`, `state.roundIndex`, `state.boxCount` 폐지 (zone hit-test로 대체) |
| **Spawn** | 매 라운드 17 sprite 생성/제거 | 게임 시작 시 50 sprite 1회 생성, 위치만 이동 |
| **Movement** | `crowdEl(side).appendChild()` (DOM 이동) | CSS transform-based 좌표 이동 (`translateX` to zone center + jitter) |
| **Layout** | `box-o` `box-x` 두 개의 박스에 자식으로 쌓임 | arena 1개에 절대 위치 sprite, 좌/우 zone 시각 표시는 background |
| **HUD** | `q-num / lives / score` | `q-num / alive-count / score` |
| **End condition** | `lives ≤ 0` OR `idx ≥ 30` | `alive.length ≤ 1` OR `playerEliminated` |
| **Effects** | `is-falling` 1종 | `effect-fall / effect-poof / effect-floor-crack / effect-rocket` 4종 + 랜덤 디스패처 |
| **Background** | `data-theme` 정적 그라디언트 | + `background-position-y` 무한 애니메이션 (러닝) |

### 4.1 v1 재사용 코드 비율 (예상)

- 데이터 레이어 (CSV 파싱·검증): **100% 재사용**
- GA4 / UTM: **100% 재사용**, 이벤트 페이로드만 v2 필드 보강
- 라운드 테마: **100% 재사용** (5문항마다 변경 그대로)
- 타이머: **100% 재사용**
- 인트로 화면 / 에러 / 토스트 / 공유 버튼: **80% 재사용** (HUD·종료 분기만 변경)
- spawn / move / reveal: **재작성** (전면 변경)

---

## 5. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| 50 sprite 모바일 성능 저하 | High | High | sprite 1회 spawn + transform 기반 이동(reflow 회피), `will-change: transform`, prefers-reduced-motion 분기. Chrome DevTools로 NFR-V2-01 측정 게이트. |
| 라운드 끝없이 늘어남 (NPC 정답률 너무 낮음) | Medium | Medium | NPC 정답률 라운드별 cap 도입(55→70%). 100회 시뮬레이션으로 SC-V2-02 검증 후 조정. |
| 첫 문제 오답 즉시 종료 = 신규 사용자 이탈 | Medium | High | 첫 문제는 명확한 난이도 ★(쉬운 문제)로 고정 가능 옵션. 데이터에서 `difficulty: easy` 플래그 정렬. (Design 단계에서 결정) |
| 4종 탈락 이펙트가 시각적으로 혼란스러움 | Low | Medium | Design 단계에서 4종 이펙트 단순 prototype 후 사용자 피드백. 안 되면 2종으로 축소. |
| v1 사용자가 v2로 갈아탈 때 메커니즘 충격 | Low | Low | 인트로 화면에 "🆕 50명 서바이벌 모드" 배지. 첫 라운드 짧은 튜토리얼 토스트. |
| GA4 측정 ID 미교체 상태로 v2 출시 | Medium | Low | v1 잔여 액션 I1과 동일. 배포 전 필수 체크. |
| 라이프 ❤️ 폐지로 v1 페르소나의 "관용성" 기대 어긋남 | Low | Medium | 영상 레퍼런스가 이미 그 톤이므로 컨셉 일치. SC-V2-03(첫 문제 탈락률) 모니터링. |

---

## 6. Analytics (v2 보강)

v1 5개 이벤트는 그대로, 페이로드만 보강 + v2 신규 이벤트 추가.

| Event | v1 | v2 |
|-------|-----|-----|
| `game_start` | `round_size` | + `start_alive: 50`, `mode: 'survival_v2'` |
| `answer_o` / `answer_x` | `correct, user_choice, question_id, question_index` | + `survived_npcs_before, survived_npcs_after, eliminated_count` |
| `game_end` | `score, total, lives_left, duration_sec` | 폐지 → `game_end_win` / `game_end_lose` 분기 |
| `game_end_win` (신규) | — | `survived_rounds, score, duration_sec, ranking: 1` |
| `game_end_lose` (신규) | — | `survived_rounds, score, duration_sec, ranking, alive_at_death` |
| `share_click` | `method` | + `result: 'win' | 'lose'` |
| `round_advance` (신규) | — | `round_idx, alive_count` (라운드별 생존자 추이 분석) |

---

## 7. Implementation Phases

| Phase | Module | 내용 | Est. LOC |
|-------|--------|------|---------|
| M1 | state-refactor | state 스키마 변경(alive[], playerEliminated, roundIndex), resetState 갱신 | +30 / -40 |
| M2 | spawn-once | 게임 시작 시 50 sprite 1회 spawn (arena 직접 자식, transform 좌표) | +50 / -30 (v1 spawnRoundCharacters 폐기) |
| M3 | zone-split | arena 좌/우 zone 시각화 + 플레이어/NPC 이동 로직(transform 기반) | +60 / -50 (v1 moveCharacterToBox 폐기) |
| M4 | npc-behavior | NPC 1~2회 메번직 + 라운드별 정답률 cap | +40 |
| M5 | reveal-eliminate | 시간 종료 → 오답 zone 캐릭터 탈락 + alive[] 갱신 | +50 / -30 (v1 revealAnswer 부분 교체) |
| M6 | effects | 4종 탈락 이펙트 CSS + JS 랜덤 디스패처 | +60 (CSS +100) |
| M7 | running-bg | arena background 위→아래 무한 스크롤 CSS | +30 |
| M8 | hud-end | HUD에서 lives 제거 + 종료 화면 분기(win/lose-survivor/lose-ranking) + 공유 문구 v2 | +40 / -20 |
| M9 | analytics-v2 | game_end → win/lose 분기, round_advance 신규, 페이로드 보강 | +30 |
| M10 | qa-tune | NPC 정답률 100회 시뮬레이션 + 첫 문제 난이도 정렬 결정 | +20 |
| **Total** | | | **+410 / -170 ≈ 순증 +240** |

---

## 8. Acceptance Test (수동 시나리오)

| ID | 시나리오 | Pass 조건 |
|----|----------|-----------|
| AT-V2-01 | 게임 시작 → 50개 캐릭터 동시 등장 | 모바일 60fps, 1.5초 내 첫 문제 표시 |
| AT-V2-02 | O 정답 라운드 → X 존 NPC 전원 탈락 | alive count 정확히 감소, 4종 이펙트 시각적으로 구분됨 |
| AT-V2-03 | 5라운드 후 alive=1(플레이어) | "최후의 1인" 화면 + WIN 공유 문구 |
| AT-V2-04 | 1라운드에 플레이어 탈락 (생존 N명) | "Q.1에서 탈락 너 25등" 화면 + LOSE 공유 문구 |
| AT-V2-05 | 라운드 중 마음 변경 (O→X→O) | 마지막 위치 기준으로 판정, NPC도 동일 |
| AT-V2-06 | 100라운드 시뮬레이션(autotest) | 평균 8~10라운드에 결판, 30라운드 초과 비율 < 5% |
| AT-V2-07 | prefers-reduced-motion 사용자 | 러닝 배경 정지, 탈락 이펙트 단순화 |
| AT-V2-08 | 데스크톱 브라우저 | 480px max-width 유지, 50명 가독성 OK |

---

## 9. Open Questions (Design 단계로 이월)

1. **첫 문제 난이도 고정?** — SC-V2-03(첫 문제 탈락률 ≤ 25%) 충족 위해 데이터에 `difficulty` 컬럼 추가 vs 첫 1~2문제만 별도 풀 분리 vs 그대로 두기. (Plan에서는 옵션 제시만, Design에서 결정)
2. **NPC 정답률 곡선**: 선형 R1=55→R10=70 vs 시그모이드 vs 첫 3라운드 50%로 평탄 후 급상승. 100회 시뮬 결과 보고 결정.
3. **arena 좌/우 zone 시각화 강도**: 단순 세로 선 vs zone별 다른 톤(O=청록 옅게, X=빨강 옅게) vs 라운드 테마와 결합.
4. **러닝 배경 패턴**: 격자 vs 점선 vs 라운드 테마별 패턴(잔디결, 얼음결, 모래결).
5. **인트로 화면**: v1 그대로 vs "50명 서바이벌" 강조 배지/카피 추가.
6. **종료 화면 코인 비/축포**: WIN에만 적용 vs LOSE에는 위로 톤 일러.

---

## 10. Approval Checklist

- [ ] 50명 + 라이프 폐지 + 무제한 라운드 = 핵심 메커니즘 합의 ✓ (사용자 확정 2026-05-10)
- [ ] 4종 탈락 이펙트 + 위→아래 러닝 배경 = 시각 컨셉 합의 ✓
- [ ] v1 인프라(GA4·UTM·CSV·테마·sprite) 그대로 상속 ✓
- [ ] Design 단계 진입 준비

---

**Next Step**: `/pdca design survival-mode-v2`
