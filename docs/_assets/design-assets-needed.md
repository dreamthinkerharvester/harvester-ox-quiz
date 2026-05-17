# 필요 디자인 에셋 인벤토리 (사용자 제작 요청)

> 마지막 갱신: 2026-05-17
> 트리거: 카테고리 15 → **433** 폭증, 자격증·과목 시각 구분 필요
> 제공 위치: `assets/` (전역) / `exam/_assets/` (학습 페이지 전용)
> 모든 자산은 PNG (또는 SVG) — 저작권은 자체 제작 또는 라이선스 명확한 것만

---

## 0. 중복 방지 — 이미 있는 자산 (제작 불필요)

| 카테고리 | 위치 | 개수 | 비고 |
|----------|------|:---:|------|
| 캐릭터 sprite | `_refs/sprites/char-*.png` | 25 | 메인 게임용 (히어로·동물·몬스터·기타). **학습 페이지에 부적합** (만화체 톤 불일치) |
| 말풍선 sprite | `_refs/sprites/bubble-*.png` | 11 | confident·confused·cute·easy·go-go·help·hmm·noooo·pity·shock 등. **학습 페이지 토스트로 재사용 가능** |
| 도장 sprite | `_refs/sprites/stamp-*.png` | 5 | combo·fail·pass·perfect·wrong — 학습 페이지 결과 화면에 즉시 활용 가능 |
| 타이머 sprite | `_refs/sprites/timer-clock-*.png` | 3 | calm·warning·critical — 학습 페이지 시간제한 모드에 활용 |
| 표정 sprite | `_refs/sprites/expr-*.png` | 5 | cold-sweat·confident·cry·laugh·think — 통계/오답노트에 강조용 |
| 이펙트 sprite | `_refs/sprites/fx-*.png` `particle-*.png` | 23 | 별·하트·코인·먼지 등 — 정답 효과 |
| favicon | `assets/favicon.svg` | 1 | 도로 + O/X — 두 사이트 공용 |
| og-image | `assets/og-image.png` | 1 | 1080×1080 — **메인 게임 전용**, 학습 페이지 버전 별도 필요 (§5) |

---

## 1. 🔴 Critical — 자격증 아이콘 (24개)

**용도**: 학습 페이지 카테고리 카드 `.cat__mark` 56×56 영역 (현재 비어있음)
**사양**: 단일 아이콘 PNG, **64×64 px** (2x 대응 위해 128×128 권장), 투명 배경
**스타일**: 베이지·미니멀, 단색 또는 2색, line-art 또는 flat. 만화체 X
**파일명**: `exam/_assets/jik/{slug}.png`

| # | 슬러그 | 자격증 | 모티프 제안 | DB 카테고리 수 | OX 수 |
|:--:|--------|--------|------------|:---:|:----:|
| 1 | `g9` | 국가직 9급 | 정부서울청사 / 9 숫자 | 99 | 3,841 |
| 2 | `g7` | 국가직 7급 | 동일 톤 + 7 숫자 | 90 | 4,031 |
| 3 | `g5` | 국가직 5급 | 동일 톤 + 5 숫자 | — | — |
| 4 | `l9` | 지방직 9급 | 지방청사 / 지도 마커 | 45 | 1,366 |
| 5 | `l7` | 지방직 7급 | 동일 + 7 | 10 | 450 |
| 6 | `s9` | 서울시 9급 | 서울시청 실루엣 | — | (TODO) |
| 7 | `s7` | 서울시 7급 | 동일 + 7 | — | — |
| 8 | `na9` | 국회직 9급 | 국회의사당 돔 | 15 | 693 |
| 9 | `na8` | 국회직 8급 | 동일 + 8 | 14 | 656 |
| 10 | `na5` | 국회직 5급 | 동일 + 5 | — | — |
| 11 | `ct9` | 법원직 9급 | 정의의 저울 | — | — |
| 12 | `ct5` | 법원직 5급 | 동일 + 5 | — | — |
| 13 | `pol-cmdr` | 경찰 간부 | 경찰 무궁화 + 별 | 37 | 3,416 |
| 14 | `pol-misc` | 경찰 (기타) | 경찰 마크 | 14 | 1,243 |
| 15 | `pol-prom` | 경찰 승진 | 경찰 + 상향 화살표 | 5 | 616 |
| 16 | `pol-spec` | 경찰 특공대 | 방패 | 3 | 229 |
| 17 | `fire-cmdr` | 소방 간부 | 소방 헬멧 + 별 | 11 | 696 |
| 18 | `fire-misc` | 소방 (기타) | 소방 마크 / 호스 | 11 | 667 |
| 19 | `fire-prom` | 소방 승진 | 소방 + 상향 화살표 | — | — |
| 20 | `ms9` | 군무원 9급 | 군 마크 + 9 | 25 | 1,063 |
| 21 | `ms-misc` | 군무원 (기타) | 군 마크 | 3 | 77 |
| 22 | `cg-prom` | 해경 승진 | 해양 + 닻 | 13 | 1,092 |
| 23 | `cg-cmdr` | 해경 간부 | 동일 + 별 | — | — |
| 24 | `met9` | 기상직 9급 | 구름·기온계 | — | — |

**전문직 (별도 톤 — 더 격식)** 8개:
| # | 슬러그 | 자격증 | 모티프 | OX |
|:--:|--------|--------|--------|----|
| 25 | `tax` | 세무사 | 계산기 + 원화 | 765 |
| 26 | `cpa` | 회계사 | 회계장부 + 펜 | 649 |
| 27 | `admin` | 행정사 | 서류 + 도장 | 591 |
| 28 | `cpla` | 노무사 | 사람 + 균형 | — |
| 29 | `appr` | 감정평가사 | 부동산 + 돋보기 | 108 |
| 30 | `bizmgt` | 경영지도사 | 그래프 차트 | — |
| 31 | `customs` | 관세사 | 컨테이너 + ✓ | 57 |
| 32 | `franch` | 가맹거래사 | 매장 + 핸드셰이크 | 69 |
| 33 | `law` | 변호사시험 | 정의의 저울 + 책 | 9 |

**총 33개 아이콘**. 일관성 위해 **한 디자이너가 같은 스타일 시트**로 일괄 작성 권장.

---

## 2. 🟡 Important — 자격증 카테고리 컬러 시스템 (계열별 8색)

**용도**: `.cat__mark` 배경색 + 카테고리 그룹 헤더. 색약(deuteranopia) 대비 점검 필수.

> 33개 자격을 각각 별도 색으로 두면 인지 부담 큼 → **8개 계열 그룹**

| 계열 | 색 (Light) | 색 (Deep) | 포함 자격 |
|------|------------|-----------|----------|
| 국가직 | `#e3f2fd` | `#1976d2` | g5·g7·g9 |
| 지방·서울 | `#e1f5fe` | `#0288d1` | l7·l9·s7·s9 |
| 국회·법원 | `#ede7f6` | `#5e35b1` | na5·na8·na9·ct5·ct9 |
| 경찰 | `#ffebee` | `#c62828` | pol-cmdr·pol-misc·pol-prom·pol-spec |
| 소방 | `#fff3e0` | `#ef6c00` | fire-cmdr·fire-misc·fire-prom |
| 군무원·해경 | `#e8f5e9` | `#2e7d32` | ms*·cg* |
| 기상직·기타 | `#fafafa` | `#616161` | met9·misc·emrg |
| 전문직 | `#fff8e1` | `#f9a825` | tax·cpa·admin·cpla·appr·bizmgt·customs·franch·law |

**사용자 결정 사항**: 위 톤이 베이지 페이퍼 배경(`#f7efe0`)과 어울리는지 — 미세 조정 필요할 수 있음. **컬러 토큰 JSON 또는 CSS 변수 1세트만 제공**해주시면 됩니다.

---

## 3. 🟡 Important — 빈 상태 (Empty State) 일러스트 4종

**용도**: 학습 페이지 검색·북마크·오답노트·통계 빈 화면
**사양**: PNG **240×240** (또는 SVG), 베이지 톤, 친근하지만 차분한 일러스트
**파일명**: `exam/_assets/empty/{name}.png`

| # | 슬러그 | 상황 | 메시지 톤 |
|:--:|--------|------|----------|
| 1 | `search-none` | 검색 결과 0건 | "🔍 검색어를 다시 확인해보세요" |
| 2 | `bookmark-empty` | 북마크 없음 | "⭐ 풀이 중 ⭐을 눌러 모아보세요" |
| 3 | `wrong-empty` | 오답노트 없음 | "📝 아직 틀린 문제가 없어요" |
| 4 | `stats-empty` | 통계 데이터 없음 | "📊 첫 문제를 풀어보세요" |

→ 기존 `_refs/sprites/expr-*.png` 표정 sprite 재활용 가능. **새 일러스트 대신 표정 sprite + 텍스트 조합도 OK** (사용자 선호 확인 필요)

---

## 4. 🟢 Nice-to-Have — 중요도 배지 ★ 강조 (현재는 텍스트 별 ★)

**용도**: 반복 출제 문항 강조 — 현재 frequency≥2 인 경우 `.q-star-badge` 노출
**사양**: SVG (확장 자유), 16×16 ~ 24×24, 골드 톤
**파일명**: `exam/_assets/star-{1..5}.svg` (5단계)

→ **유니코드 ★ + CSS color로 충분히 표현 가능** — 별도 제작 비용 vs 효과 비교해서 결정

---

## 5. 🟢 Nice-to-Have — 학습 페이지 og-image (1080×1080)

**현재**: `assets/og-image.png` 은 메인 게임 ("내가 짱!") 전용
**필요**: 학습 페이지(`/exam/`) 공유용 별도 og-image
**파일명**: `assets/og-image-exam.png`

**디자인 가이드**:
- 베이지 배경 (`#f7efe0`)
- 중앙: "OX로 푸는 기출문제 21,216개"
- 좌하: 자격증 아이콘 5개 그리드 (세무사·회계사·국가직 9급·경찰 간부·소방 간부)
- 우하: O/X 큰 원
- 폰트: Black Han Sans

---

## 6. 🟢 Nice-to-Have — PWA 아이콘 (모바일 홈 추가)

**조건**: 모바일 사용자 비중 80%+ 인 경우 효과 큼
**파일명**: `assets/icon-{192,512}.png` + `assets/manifest.json`
**사양**: 정사각 PNG, 라운드 처리 안 함 (OS가 마스킹), 안전영역 padding 12%

| 사이즈 | 용도 |
|:------:|------|
| 192×192 | Android 홈 화면 |
| 512×512 | iOS 홈 추가, splash screen |

---

## 7. 🟢 Nice-to-Have — 카테고리 트리 분류 헤더 배경 패턴 (선택)

**조건**: 카테고리 트리 토글이 계층형으로 발전할 때 (현재 flat list)
**스킵 가능**: 위 §2 컬러 시스템만으로 충분

---

## 📦 전달 방법

### 폴더 구조 권장
```
사용자_제공_에셋/
├── jik/                       # §1 자격증 아이콘 (33개)
│   ├── g9.png  g7.png  g5.png
│   ├── l9.png  l7.png
│   ├── s9.png  s7.png
│   ├── na9.png na8.png na5.png
│   ├── ct9.png ct5.png
│   ├── pol-cmdr.png pol-misc.png pol-prom.png pol-spec.png
│   ├── fire-cmdr.png fire-misc.png fire-prom.png
│   ├── ms9.png ms-misc.png
│   ├── cg-prom.png cg-cmdr.png
│   ├── met9.png
│   ├── tax.png cpa.png admin.png cpla.png
│   ├── appr.png bizmgt.png customs.png franch.png law.png
│   └── _STYLE-GUIDE.md       # 컬러·라인 두께 등 명세 (선택)
├── empty/                     # §3 빈 상태 일러스트 (4개, optional)
│   ├── search-none.png
│   ├── bookmark-empty.png
│   ├── wrong-empty.png
│   └── stats-empty.png
├── og-image-exam.png          # §5 학습 페이지 og-image (optional)
├── icon-192.png               # §6 PWA (optional)
├── icon-512.png
└── color-system.json          # §2 컬러 토큰 (JSON 또는 CSS)
```

### 우선순위 가이드
1. **즉시 가치 (1주 내)**: §1 자격증 아이콘 33개 + §2 컬러 시스템
2. **사용성 향상 (2주 내)**: §3 빈 상태 일러스트
3. **마케팅 부스트 (선택)**: §5 og-image + §6 PWA
4. **스킵 가능**: §4 별 배지, §7 패턴

### 받은 후 통합 절차 (자동)
1. `assets/` / `exam/_assets/` 로 복사
2. `exam.css` 에 컬러 토큰 변수 추가
3. `exam/exam.js` `renderCategoryList()` 에 `<img src="_assets/jik/{slug}.png">` 자동 매핑
4. `_index.json` 의 slug prefix 보고 아이콘 자동 선택
5. validate + smoke test + commit

---

## ❓ 사용자 확인 필요한 4가지

1. **§1 아이콘 톤** — 베이지·미니멀 line-art 톤이 맞는지 (메인 게임은 만화체라 다름)
2. **§2 컬러 시스템** — 직렬 8그룹 계열로 묶는 게 OK인지, 더 세분화 원하는지
3. **§3 빈 상태** — 새 일러스트 만들지 vs 기존 `_refs/sprites/expr-*.png` 재활용할지
4. **§5·§6 마케팅 자산** — 학습 페이지 단독 공유·PWA 푸시 계획 있는지
