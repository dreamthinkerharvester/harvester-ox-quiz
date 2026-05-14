# assets/

## 파일 목록

| 파일 | 용도 | 상태 |
|------|------|:----:|
| `favicon.svg` | 브라우저 탭 아이콘 (도로 배경 + O/X 두 글자) | ✅ 자체 SVG 작성 완료 |
| `og-image.png` | 카톡·페북·트위터 공유 시 미리보기 (1080×1080) | ⚠️ **별도 제작 필요** |

## og-image.png 제작 가이드

### 사양
- 사이즈: **1080×1080** (정사각, 카톡·인스타 호환)
- 포맷: PNG, < 200KB 권장
- 노출 위치: 카톡 링크 미리보기, 페이스북 셰어, 트위터 카드

### 디자인 가이드 (디자인 토큰 기준)
- 배경: 노란 방사형 (`#fdd835` + `#ffec8b`)
- 중앙 큰 한글: **"내가 짱!"** (Black Han Sans, 외곽선 흰색·내부 검정)
- 좌하/우하: 큰 둥근 **O** (청록 `#29b6f6`) / **X** (빨강 `#ef5350`)
- 캐릭터: 🥳 이모지 또는 자체 SVG 캐릭터 (단순 chibi 라운드)
- 코인 흩날림 (선택)

### 제작 도구 (권장 순서)

**가장 빠른 방법 — `og-image-source.html` 사용 (Recommended, ~3분)**
1. 로컬 서버 시작: `python3 -m http.server 8765` (저장소 루트에서)
2. 브라우저: `http://localhost:8765/assets/og-image-source.html`
3. Chrome DevTools 열기 (`F12` 또는 `Cmd+Opt+I`)
4. `Cmd+Shift+P` → "Capture node screenshot" 선택
5. `.og-card` 요소 클릭 → 자동으로 1080×1080 PNG 저장
6. 다운로드된 파일을 `assets/og-image.png` 로 이동

**playwright 자동화 (한 줄)**
```bash
npx playwright screenshot --viewport-size=1080,1080 \
  http://localhost:8765/assets/og-image-source.html \
  assets/og-image.png
```

**대체 도구**
- **Figma**: 무료, 1080×1080 캔버스 → PNG export
- **Canva**: 템플릿 기반, 빠름
- **AI 생성**: nanobanana MCP (실사 톤이라 만화풍은 프롬프트 튜닝 필요)

### 저작권
- 퀴즈스틱맨 그래픽 자산 직접 사용 금지
- 모든 캐릭터·일러스트는 자체 제작 또는 유니코드 이모지 활용

## 작업 후 검증

```bash
# OG 미리보기 확인
open "https://developers.facebook.com/tools/debug/"
# URL 입력: https://{user}.github.io/ox-quiz/
# "Scrape Again" 클릭 후 1080×1080 이미지 정상 노출 확인
```
