# 도메인: admin (운영자 설정)

> 크로스커팅 도메인 — research/content/publishing(콘텐츠 파이프라인)과 별개. **운영자가 시스템 동작을 설정**하는 곳. ADR 0016, 라운드㉝.

## 경계 (무엇을 소유하나)
- **수집·관심 설정**: 종목 관심 on/off · 등록 키워드 · 소스 토글(네이버·RSS·DART) · 검색 기간.
- **종목 마스터**: 코스피200(name↔ticker↔sector) — `common.stocks`(코드)에서 승격. 운영자 편집.
- 소유 저장소: **`admin_db`**(admin 서비스만 직접접근).

## 경계 밖 (무엇을 안 하나)
- 수집 실행(news-feed) · 이슈 랭킹(issue-detector) · 제작(content) — 이들은 admin **설정을 읽어** 동작할 뿐, 설정은 admin이 소유.
- 인증(Supabase, ADR 0007)·발행(publishing)과 무관.

## 관계
- **쓰기**: content 대시보드(:8091 설정 메뉴) → admin API.
- **읽기**: news-feed·issue-detector → `GET /admin/config`(Database per Service — API만, DB 직접접근 X).
- 게이트웨이 `/admin` 라우트 뒤. 자격증명(KRX_ID/KRX_PW 등)은 `.env`.
