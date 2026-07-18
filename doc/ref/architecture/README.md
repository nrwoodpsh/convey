# 아키텍처 — CONVEY (인덱스)

> 원형: `py-msa-ai`. 전환 배경·결정은 `doc/decisions/` ADR 참조.

## 🖼 시각 정본 → **[00.아키텍처.html](00.아키텍처.html)** (브라우저로 열기)
구성도 · 서비스맵 · 지식 그래프 · 토픽 · 도메인 상세 · 크로스커팅 **전체**를 담는다.

## 마크다운 (AI·검색용 경량 refs)

| 문서 | 내용 |
|:---|:---|
| [01.research](01.research.md) | Neo4j 지식 그래프 + Postgres 사실 (저장 상세) |
| [02.content](02.content.md) | 근거 스크립트 · 미디어(외주) · 정확 렌더 · 승인 |
| [03.publishing](03.publishing.md) | YouTube Shorts 발행 |
| [04.issue-detector](04.issue-detector.md) | 오늘의 이슈 종목 선별 (알파2) |

> HTML = 사람용 시각 정본 / md = AI 자동로드·grep용 경량 인덱스. 둘 다 같은 내용을 반영.
> 알파는 `doc/decisions/0004`, 저장(Neo4j 그래프)은 `0005`.
