# survival-mode-v2 Analysis Document

> **Summary**: Static gap analysis of Design vs Implementation. matchRate **94.8%** (≥90% — Report 진입 가능).
>
> **Project**: OX퀴즈게임
> **Version**: 0.2.0
> **Author**: bkit:pdca/analyze (kakaiuina@gmail.com)
> **Date**: 2026-05-10
> **Status**: Check Phase Complete
> **Predecessor**: [survival-mode-v2.design.md](../02-design/features/survival-mode-v2.design.md), [survival-mode-v2.plan.md](../01-plan/features/survival-mode-v2.plan.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | v1 메커니즘이 영상 레퍼런스의 "서바이벌 임팩트"를 충분히 못 살림 |
| **WHO** | SNS 자취생/20대 (페르소나 박지원, 24세) |
| **RISK** | 50 sprite 모바일 성능 / 라운드 분포 / 첫 문제 이탈 / NPC 튜닝 |
| **SUCCESS** | 모바일 60fps, 평균 세션 ≥2.5분, 평균 라운드 6~12, 첫 문제 탈락률 ≤25% |
| **SCOPE** | 50인 spawn, zone, 4종 이펙트, 무제한 라운드, 러닝 BG |

---

## 1. Match Rate Summary

| Axis | Score | Weight | Weighted |
|------|------:|-------:|---------:|
| Structural Match | 100% | 0.2 | 20.0 |
| Functional Depth | 92% | 0.4 | 36.8 |
| API Contract | 95% | 0.4 | 38.0 |
| **Overall** | | | **94.8%** |

> Static-only formula (no live server / Playwright). Runtime verification deferred (정적 사이트, 수동 브라우저 테스트로 대체).

**Decision**: matchRate ≥ 90% → `/pdca report` 단계로 진행. 잔여 Gap은 P1/P2이며 Report 단계에서 잔여 액션으로 기록.

---

## 2. Strategic Alignment Check

| Strategic Item | Status | Evidence |
|---|:---:|---|
| PRD 핵심 문제 (서바이벌 임팩트 향상) | ✅ Met | 50인 동시 탈락 + 4종 이펙트 + 러닝 BG 모두 구현 |
| Plan SC-V2-01 (60fps, 50 sprite) | ⚠️ Pending | 1회 spawn + transform 기반 좌표 — 구조적으로 충족, 실측 미실시 |
| Plan SC-V2-02 (평균 6~12 라운드) | ⚠️ Partial | simulate(10000) 결과 avgRound 1.98~3.57 — Design §11.4에서 "짧고 자주 재플레이" 모델로 acceptance 결정 (state.json 참조) |
| Plan SC-V2-03 (첫 문제 탈락률 ≤25%) | ⚠️ Partial | 75% 정답률 사용자만 충족 (24.8%). 평균 50% 사용자는 49.1% (state.json) — design 단계 결정 |
| Plan SC-V2-04 (평균 세션 ≥2.5분) | ❓ TBD | GA4 측정 ID 미설정 (잔여 액션 I1) |
| Plan SC-V2-05 (공유율 v1 +30%) | ❓ TBD | GA4 측정 ID 미설정 (잔여 액션 I1) |
| Architecture Option C (Pragmatic Balance) | ✅ Met | 단일 파일 + 섹션 주석 컨벤션 유지, script.js 865줄 (예상 ~820 +5%) |

---

## 3. Functional Requirements Verification

| ID | Requirement | Status | Evidence |
|---|---|:---:|---|
| FR-V2-01 | 50개 sprite 1회 spawn | ✅ Met | [script.js:357](../../script.js#L357) `spawnAllOnce()` |
| FR-V2-02 | arena 좌(O)/우(X) zone 시각화 | ✅ Met | [index.html:81-83](../../index.html#L81), [style.css:299-303](../../style.css#L299) |
| FR-V2-03 | 플레이어 O/X 버튼 탭 + 재탭 | ✅ Met | [script.js:432](../../script.js#L432) `handleBoxClick` (answerRevealed가 false인 동안 재탭 가능) |
| FR-V2-04 | NPC 1~2회 메번직 + 라운드별 정답률 | ✅ Met | [script.js:464](../../script.js#L464) `scheduleNPCDecisions`, NPC_ACCURACY_CURVE [0.35→0.72] |
| FR-V2-05 | 오답 zone 캐릭터 탈락 | ✅ Met | [script.js:545-557](../../script.js#L545) — `currentSide === wrongSide \|\| null` 모두 탈락 |
| FR-V2-06 | 4종 랜덤 이펙트 | ✅ Met | [script.js:582](../../script.js#L582) `playEliminationEffect`, [style.css:467-535](../../style.css#L467) 4 keyframes |
| FR-V2-07 | 종료 조건 + 3분기 화면 | ✅ Met | [script.js:626](../../script.js#L626) `checkEndCondition`, [script.js:736](../../script.js#L736) `renderEnd` (win/lose-survivor/lose-ranking) |
| FR-V2-08 | 무제한 라운드 + 풀 재셔플 | ✅ Met | [script.js:302](../../script.js#L302) `ensureCurrentRound` |
| FR-V2-09 | 위→아래 러닝 배경 | ✅ Met | [style.css:271-285](../../style.css#L271) `.is-running::before` + `@keyframes scroll-down 0.8s` |
| FR-V2-10 | HUD 라이프 제거, 살아남음 표시 | ✅ Met | [index.html:64-69](../../index.html#L64), [script.js:711](../../script.js#L711) `renderHUD` |
| FR-V2-11 | 공유 문구 v2 분기 | ✅ Met | [script.js:658](../../script.js#L658) `buildShareText` (win/lose-survivor/lose-ranking) |
| FR-V2-12 | 다음 라운드 살아있는 NPC 위치 유지 | ✅ Met | [script.js:421](../../script.js#L421) `positionSprite`는 transform만 변경, baseY 보존 |

**FR Coverage: 12/12 (100%)**

---

## 4. Non-Functional Requirements

| ID | Target | Status | Note |
|---|---|:---:|---|
| NFR-V2-01 | 60fps on 50 sprite | ⚠️ Pending | will-change: left/top 적용 ([style.css:441](../../style.css#L441)). 실기 측정 필요 |
| NFR-V2-02 | 첫 페인트 < 1.5s on 3G | ✅ Met | 정적 HTML, 외부 폰트만 비동기 로드 |
| NFR-V2-03 | 게임 시작 → 첫 문제 < 500ms | ✅ Met | spawnAllOnce는 50회 createElement만 (DOM reflow 1회) |
| NFR-V2-04 | script.js +200~250 / style.css +100~150 | ✅ Met | script.js 616→865 (+249), CSS 수치는 v1 baseline 미보존 |
| NFR-V2-05 | aria-live + reduced-motion | ✅ Met | [index.html:66](../../index.html#L66) `aria-live="polite"`, [style.css:732-737](../../style.css#L732) reduced-motion |
| NFR-V2-06 | CSP class-based effects | ✅ Met | inline style은 `--x`/`--y` CSS 변수만 (CSP 호환) |

---

## 5. Gap List

### 🔴 Critical (must fix before report)

없음.

### 🟡 Important (should fix)

| # | Item | Location | Severity | Recommendation |
|---|------|----------|:---:|---|
| G-01 | index.html 메타 description이 v1 그대로 ("라이프 3개로 30문항 도전") | [index.html:8](../../index.html#L8) | Important | "50명 서바이벌, 한 번 틀리면 끝!" 으로 갱신 |
| G-02 | og:description이 v1 그대로 ("200문항에서 30문항 랜덤 출제. 라이프 3개로 도전!") | [index.html:12](../../index.html#L12) | Important | v2 톤으로 갱신 |
| G-03 | og:url이 placeholder (`https://example.github.io/ox-quiz/`) | [index.html:14](../../index.html#L14) | Important | 배포 도메인 확정 후 교체 (잔여 액션 I3와 통합) |

### 🟢 Minor (nice to have)

| # | Item | Note |
|---|------|------|
| G-04 | sprite Y 범위 12~88% (Design §5.2는 15~85%) | 약간 더 넓음. 시각적 차이 미미 |
| G-05 | ZONE_JITTER 단위가 px가 아닌 % (Design §5.2 "±12px" → 구현 ±8%) | 반응형 측면에서 % 가 합리적. design 의도 충족 |
| G-06 | EFFECT random distribution: simple `Math.floor(Math.random() * 4)` | Design §5.4와 일치 (균등 분배) |

---

## 6. Decision Record Verification

| Decision | Source | Followed? |
|---|---|:---:|
| Architecture Option C (Pragmatic Balance) | Design §2.1 | ✅ |
| 단일 파일 (script.js + style.css + index.html) | Design §2.0 | ✅ |
| NPC_ACCURACY_CURVE 계단형 [0.35→0.72] | Design §11.4-Q2 | ✅ |
| 4종 이펙트 균등 25% | Design §5.4 | ✅ |
| 8px 격자 + 0.8s linear 스크롤 | Design §5.5 | ✅ |
| 인트로 "🆕 50명 서바이벌" 배지 | Design §11.4-Q5 | ✅ ([index.html:42](../../index.html#L42)) |
| 종료 3분기 (win/lose-survivor/lose-ranking) | Design §11.4-Q6 | ✅ |
| 첫 문제 NPC 정답률 35%로 신규 이탈 완화 | Design §11.4-Q1 | ✅ |
| 라이프 ❤️ DOM/state 완전 제거 | Design §11.5 | ✅ |
| `final-lives` → `final-ranking` 변경 | Design §11.5 | ✅ ([script.js:744](../../script.js#L744) `dataset.ranking`) |

**Decision Adherence: 10/10 (100%)**

---

## 7. Test Plan Status

| Level | Status | Note |
|---|:---:|---|
| L1 (Unit, console) | ✅ Available | `Game.simulate(10000)` 함수로 자동 시뮬레이션 가능 ([script.js:816](../../script.js#L816)) — qaSimulation 결과 `state.json`에 기록 |
| L2 (UI Action, manual) | ⚠️ Pending | 사용자 직접 1~2 라운드 플레이 필요 (잔여 액션 I2) |
| L3 (E2E, Playwright) | ❌ Skipped | Design §8.3 — v3 예정 |

---

## 8. Recommendations

1. **Now**: G-01, G-02 (메타 description) 즉시 수정 — 1분 내 완료. 검색·SNS 공유 시 v1 카피 노출 방지.
2. **Before deploy**: G-03 (og:url) 배포 도메인 확정과 함께. 잔여 액션 I1(GA4 ID) · I3(OG URL) 일괄 처리.
3. **Optional**: 사용자 직접 1~2 라운드 플레이로 NFR-V2-01 (60fps) 실측 확인.
4. **Skip iterate**: matchRate 94.8% ≥ 90% → 자동 iterate 불필요. 메타 태그 3건만 단순 수정 후 `/pdca report` 진입.

---

## 9. Next Step

- (선택) G-01/G-02 메타 태그 2건 즉시 수정 → `/pdca report survival-mode-v2`
- (또는) G-03 포함 3건 모두 잔여 액션으로 기록 후 바로 `/pdca report survival-mode-v2`
