# jik 자격증 아이콘 매핑

> 출처: `_refs/ox2/{hash}.jpeg` (Genspark 생성, 1254×1254 JPEG)
> 변환: `_refs/ox2/*.jpeg` → 흰 배경 투명화(threshold 240) → 256×256 PNG
> 통합 일자: 2026-05-17

## 적용된 18개 (이번 batch)

| 원본 hash | slug | 자격증 |
|-----------|------|--------|
| 0wPAW2nT.jpeg | `l9` | 지방직 9급 |
| 9H3Rjgdk.jpeg | `fire-cmdr` | 소방 간부 |
| DqM2JOQh.jpeg | `s7` | 서울시 7급 |
| EbVgf3vy.jpeg | `ct5` | 법원직 5급 |
| Fq7su1JQ.jpeg | `pol-spec` | 경찰 특공대 |
| IW0YYMXC.jpeg | `g5` | 국가직 5급 |
| WSPRwybQ.jpeg | `g7` | 국가직 7급 |
| YeE1Q75X.jpeg | `fire-misc` | 소방 (기타) |
| b2oSLBMq.jpeg | `pol-cmdr` | 경찰 간부 |
| h96zIV9c.jpeg | `pol-misc` | 경찰 (기타) |
| j7oaoCdP.jpeg | `s9` | 서울시 9급 |
| oPVysd2R.jpeg | `ct9` | 법원직 9급 |
| r6qaaKyl.jpeg | `na5` | 국회직 5급 |
| u5qLXh4v.jpeg | `pol-prom` | 경찰 승진 |
| uAsAMfpp.jpeg | `na9` | 국회직 9급 |
| wCXaz5V6.jpeg | `g9` | 국가직 9급 |
| z8dI9XBQ.jpeg | `na8` | 국회직 8급 |
| zDs3W4X2.jpeg | `l7` | 지방직 7급 |

## 아직 필요한 15개 (사용자 추가 제작)

| slug | 자격증 | 모티프 제안 |
|------|--------|------------|
| `fire-prom` | 소방 승진 | 소방 헬멧 + 상향 화살표 |
| `ms9` | 군무원 9급 | 군 마크 + 9 |
| `ms7` | 군무원 7급 | 동일 + 7 |
| `ms5` | 군무원 5급 | 동일 + 5 |
| `ms-misc` | 군무원 (기타) | 군 마크 |
| `cg-prom` | 해경 승진 | 닻 + 상향 화살표 |
| `cg-cmdr` | 해경 간부 | 닻 + 별 |
| `cg-misc` | 해경 (기타) | 닻 |
| `met9` | 기상직 9급 | 구름 + 기온계 |
| `tax` | 세무사 | 계산기 + 원화 |
| `cpa` | 회계사 | 회계장부 + 펜 |
| `admin` | 행정사 | 서류 + 도장 |
| `cpla` | 노무사 | 사람 + 균형 |
| `appr` | 감정평가사 | 부동산 + 돋보기 |
| `bizmgt` | 경영지도사 | 그래프 차트 |
| `customs` | 관세사 | 컨테이너 + ✓ |
| `franch` | 가맹거래사 | 매장 + 핸드셰이크 |
| `law` | 변호사 시험 | 정의의 저울 + 책 |

→ 추가 PNG가 들어오면 `exam.js` 의 `JIK_ICON_AVAILABLE` set에 slug만 추가하면
   자동으로 카드에 노출됨.
