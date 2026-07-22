# Backlog — 보류(C) 및 후속 과제

> A(실기능)·B(정제)까지 진행하고 **C는 보류(기록만)**. 운영 결정 시 착수. (2026-07-22 사용자 결정)

## C. 나중 — 키/외부 필요 (보류)

| # | 항목 | 필요 | 비고 |
|:--|:--|:--|:--|
| C1 | **YouTube 발행 자동화** | YouTube OAuth 키 | 지금은 완성본까지 자동·업로드는 사람(가드레일 일치). `publishing/youtube.py` 스텁. Supabase와 함께 착수 |
| C2 | **Supabase 인증** | Supabase 프로젝트 | 게이트웨이 JWKS 검증은 구현됨(ADR 0007). 프로젝트 생성·`SUPABASE_*` 채움만. 외부 공개 시 필요 |

## 운영 관점 남는 것 (클라우드 배포 시)

- 클라우드 배포·상시 구동·모니터링/로깅·장애 복구·비용 관리 (지금은 로컬 머신 + `docker compose` 기준)
- 미디어 볼륨 정리 정책(영상 broll 수십 MB 누적), 오브젝트 스토리지(MinIO/S3) 전환 검토(ADR 0006 후속)

## 정제 후속 (B에서 다룰 수도, 아니면 여기)

- 타입 그래프 노드(Stock/Event/Sector/Company — 지금 generic Entity)
- JSONB GIN 인덱스(articles.tickers 대량 시)
- broll 섹터→영문 검색어 매핑(지금 "stock market" 고정)
- 내레이션 길이 조절(전체 낭독 → 쇼츠 적정 길이)

> 정본은 각 도메인 `task-*.md`·ADR. 이 파일은 "보류 목록"의 단일 인덱스.
