# ref — 입력 정본 (상시 참조 인덱스)

CONVEY가 설계·구현 시 **가장 먼저 참조**하는 확정 지식. `/design`·`/builder`가 이걸 읽고 산출한다.
(← 일회성 `doc/analysis/`, 결정 기록 `doc/decisions/`와 구분)

## 지도

| 폴더 | 담는 것 | 정본 |
|:---|:---|:---|
| [architecture/](architecture/) | 아키텍처·서비스맵·토픽·크로스커팅 | `00.아키텍처.html`(시각) + `01~04`(md) |
| [domains/](domains/)   | 도메인 경계 (01 research · 02 content · 03 publishing) | 사람 관리 |
| [glossary/](glossary/) | 용어집 (코드↔한글 매핑) | `01.terms.md` |
| [patterns/](patterns/) | 확정 패턴 (api-contract·error-handling·layout·task-doc) | AI 참조 정본 |

> 상세 설계 산출물 = `doc/design/{domain}/` · 결정 근거 = `doc/decisions/` ADR
