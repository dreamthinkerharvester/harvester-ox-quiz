# PDCA Archive — 2026-05

이 폴더는 완료된 PDCA 사이클의 4종 문서(plan, design, analysis, report)를 보관한다. 메트릭 요약은 `.bkit/state/pdca-status.json`에 보존.

## 보관된 Feature

### survival-mode-v2 (2026-05-10 완료)

| 문서 | 위치 |
|---|---|
| Plan | [survival-mode-v2/plan.md](./survival-mode-v2/plan.md) |
| Design | [survival-mode-v2/design.md](./survival-mode-v2/design.md) |
| Analysis | [survival-mode-v2/analysis.md](./survival-mode-v2/analysis.md) |
| Report | [survival-mode-v2/report.md](./survival-mode-v2/report.md) |

**핵심 결과**: matchRate 94.8%, M1-M10 구현, +724 LOC. 50인 서바이벌 메커니즘 + 4종 이펙트 + 위→아래 러닝 BG. SC-V2-02 미달 (avgRound 1.98-3.57, "짧고 자주 재플레이" 모델 acceptance).

---

### survival-mode-v3 (2026-05-10 완료)

| 문서 | 위치 |
|---|---|
| Plan | [survival-mode-v3/plan.md](./survival-mode-v3/plan.md) |
| Design | [survival-mode-v3/design.md](./survival-mode-v3/design.md) |
| Analysis | [survival-mode-v3/analysis.md](./survival-mode-v3/analysis.md) |
| Report | [survival-mode-v3/report.md](./survival-mode-v3/report.md) |

**핵심 결과**: matchRate 96.4% (단일 패스, Critical/Important 0건), M1-M9 구현, +130 LOC. Grand Slam 시스템 + V1-V4 시각 보강 + NPC 곡선 완화. **GRAND_SLAM_THRESHOLD: 11→4 tuning** (Bernoulli simulate 검증). SC-V3-01 충족 (avg user 6.80%, strong 15.53%).

---

## 함께 보관된 Pre-PDCA 자료

| 자료 | 위치 |
|---|---|
| 영상 분석 리포트 (v3 PRD-equivalent) | [docs/00-pm/reference-video-analysis-2026-05-10.report.md](../../00-pm/reference-video-analysis-2026-05-10.report.md) |
| v1 분석 (88프레임) | [_refs/video-analysis.md](../../../_refs/video-analysis.md) |
| v3 분석 (6 HQ 프레임) | [_refs/video-analysis-v2.md](../../../_refs/video-analysis-v2.md) |

영상 분석 자료는 v4+ 사이클에서도 재사용되므로 archive에서 제외.

## 복구 방법

archive에서 active 상태로 복구하려면:

```bash
mv docs/archive/2026-05/survival-mode-v2/plan.md docs/01-plan/features/survival-mode-v2.plan.md
# (다른 3개 문서도 동일)
```

`.bkit/state/pdca-status.json`의 해당 feature `archivedAt`/`archivedTo` 필드 제거.
