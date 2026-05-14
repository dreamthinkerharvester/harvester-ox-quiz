# Dict Schema (data/dict/{subject}.json)

`scripts/extract_metadata.py` 가 사용하는 도메인 키워드 사전.

## 구조

```json
{
  "subject": "경제학",
  "version": 1,
  "updated_at": "2026-05-14",
  "keywords": [
    {
      "term": "외부효과",
      "aliases": ["외부성", "externality"],
      "topic": "후생경제학 §외부효과",
      "tags": ["외부효과", "시장실패", "후생경제학"],
      "theory_hint": "사회적 비용과 사적 비용의 괴리로 시장이 자원을 비효율 배분"
    }
  ]
}
```

## 필드

| 필드 | 필수 | 설명 |
|---|---|---|
| `term` | ✓ | 주 키워드 (한글) — 본문 매칭의 기준 |
| `aliases` | | 동의어·약어·영문 (대소문자 무관 매칭) |
| `topic` | | 매칭되면 `questions.topic` 후보 (가장 많이 매칭된 keyword의 topic이 채택) |
| `tags` | ✓ | 매칭되면 `questions.tags`(JSON array)에 합쳐 적재 |
| `theory_hint` | | enrich_session.py 마크다운 export 시 "참고: ..." 형태로 hint 제공 (사용자 보강용) |

## 추출 규칙

1. `term` 또는 `aliases` 중 하나가 `statement`에 부분 일치하면 그 keyword 적용
2. 매칭된 모든 keyword의 `tags`를 합집합으로 `questions.tags`에 적재 (max 5개, 빈도순)
3. 매칭된 keyword 중 `topic` 가진 것이 있으면, 매칭 빈도 1위 keyword의 topic 채택
4. 매칭 0건이면 모든 메타 NULL (사용자 세션 보강 대상)

## meta_quality 점수 (M6 audit과 일관)

| 필드 채워짐 | 점수 |
|---|---|
| topic | +25 |
| tags | +20 |
| theory | +15 |
| explanation_o | +20 |
| explanation_x | +20 |

Rule-based만으로는 최대 45점 (topic+tags)만 가능. 나머지 55점(theory + explanation_o/x)은 세션 보강 필요.
