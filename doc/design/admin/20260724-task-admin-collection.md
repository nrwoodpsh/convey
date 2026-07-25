# 20260724-task-admin-collection.md

> 라운드 ㉝ (운영자 설정 admin 서비스 + admin_db + 광역 수집 재설계). ADR 0016.
> 계약: `api-contract-admin.py`. 신규 도메인 `admin`(운영자 설정 — research/content/publishing과 별개).
> **단계(Phase) 분할**: P1~P4를 각각 builder→sync→commit 라운드로. 이 문서는 프로그램 전체 청사진.

## 1. Requirements

- **문제**: 수집이 코드에 박힌 46종목·5피드에 갇혀 있고(운영자가 못 바꿈), 종목 마스터가 코드(`common.stocks`)에 하드코딩. "그날의 경제·주식·사회·정치를 넓게 수집하고, 관심(종목·키워드)은 운영자가 대시보드에서 조정"이 안 됨.
- **목표**: **넓게 수집 + 운영자 설정 필터.** 설정(종목 on/off·키워드·소스 토글·기간)을 **전용 `admin` 서비스 + `admin_db`**로 관리하고, 대시보드에서 편집, 워커(news-feed·issue-detector)가 admin API로 읽는다. 종목 마스터를 admin_db로 **승격**.
- **핵심 정책**: 수집=넓게(카테고리 전반) · 관심=코스피200(기본 ON) + 키워드(체크박스) · 핫함=issue-detector가 관심 매칭 기사 랭킹.
- **Acceptance Criteria**(측정 가능):
  - [ ] AC1(P1): `admin_db` 5스키마(`stock`·`keyword`·`source_toggle`·`collection_settings` + 시드) + alembic 자동 마이그레이션. **검증: 컨테이너 up 후 테이블 존재·`stock` 행 ≥ 150(코스피200 시드).**
  - [ ] AC2(P1): admin API `GET /admin/config` 가 `{stocks(enabled), keywords, sources, period}` 반환. **검증: 계약 mypy + 실제 호출 200·형식 일치.**
  - [ ] AC3(P2): 대시보드 "설정" 메뉴에서 종목 on/off·키워드 추가/삭제·소스 토글·기간 변경 → admin_db 반영. **검증: UI→API→DB 왕복(값 변경 후 config에 반영).**
  - [ ] AC4(P3): news-feed가 admin config로 수집(하드코딩 제거) — 소스 토글·기간·종목·키워드 반영, RSS 카테고리 확대(경제+사회+정치). **검증: 소스 off 시 그 소스 미수집 / 키워드 추가 시 그 검색 수행.**
  - [ ] AC5(P4): issue-detector가 관심(코스피200 ∪ 키워드)을 admin에서 읽어 랭킹. **검증: 관심 밖 종목이 이슈 후보에서 빠짐.**
  - [ ] AC6(전체): 가드레일 — **Database per Service**(admin_db는 admin만 직접접근, 나머지는 API), 자격증명 `.env`(커밋 금지), 무출처 0·로컬 LLM만 불변.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **핵심 결정**(사용자 확정):
  - **결정 1 — 단계화**: 택함 = **Phase 분할(P1~P4)** / 기각 = 단일 라운드(위험·정지점 없음). 사유 = 여러 서비스·새 DB·UI라 중간 검증 필요.
  - **결정 2 — 종목 마스터**: 택함 = **admin_db로 승격(단일 진실)** / 기각 = common.stocks 공존(대시보드 편집 불가·이중 진실). 사유 = 운영자 편집·200 확대. **마이그레이션은 Phase로 점진**(news-feed→issue-detector→research 순, research는 후속).
  - **결정 3 — 코스피200 시드**: 택함 = **네이버 증권 스크래핑(계정 불필요, 접근 확인됨) 기본 + pykrx 대안 + 정적 fallback** / 사유 = pykrx 1.2.8은 KRX 로그인 필요(계정 신청했으나 활성 대기)인데, **네이버(finance.naver.com 코스피200)는 계정 없이 컨테이너에서 접근·코드추출 확인**됨(status 200·페이지네이션). 네이버는 비공식(HTML 변경 취약)이라 pluggable(source=naver|pykrx|static). KRX 계정은 활성 시 갱신·검증용.
- **사각지대**:
  - **시드 소스 취약성**: 기본이 네이버 스크래핑이라 **HTML 구조 변경 시 파싱 깨짐**(비공식). 이름·섹터는 추가 페이지·파싱 필요(코드는 확인). 깨지면 정적 fallback·pykrx로 교체. KRX 계정 활성 지연에 P1이 안 막힘(네이버로 진행).
  - **종목 마스터 이중 진실**: 이관 중 common.stocks와 admin_db 공존 구간 → **Phase별 소비처 이관 순서 명시**, 이관 완료 전까지 common.stocks는 fallback. research의 그래프 `_STOCK_BY_NAME`·backfill `ENTITY_NAMES`는 **P4 이후 후속**(범위 밖 명시).
  - **네이버 검색 폭증**: 코스피200 × 네이버 = 200회/사이클 → API 한도. **기간·주기·배치(사이클당 상한)로 관리**, P3에서 설계.
  - **대시보드→admin 결합**: content(:8091)가 admin API 호출(east-west). research 호출과 동일 패턴이라 수용. HMAC 서명 경유.
  - **RSS "사회·정치" 피드**: 신규 피드 URL 확보 필요(경제 외). P3에서 feed 목록을 admin `source`/설정으로 관리하거나 config로.
  - **gateway 라우트**: `/admin` 추가(대시보드·워커 접근). 워커는 east-west 직접 호출(HMAC)도 가능 — P1에서 확정.

## 3. UI/UX
- **P2 대시보드 "설정" 메뉴**(content :8091): 종목 목록(체크박스 on/off·검색) · 키워드 추가/삭제/토글 · 소스 토글(네이버·RSS·DART) · 기간(1주/1달/3달) 선택. 저장 시 admin API 호출.
- 나머지 화면 변화 없음(수집·필터 품질은 백엔드).

## 4. Logic (Phase별)
- **P1 — admin 서비스 + admin_db + 시드**:
  - 신규 서비스 `services/admin/`(FastAPI, DB per service). alembic로 `stock`·`keyword`·`source_toggle`·`collection_settings`.
  - `seed_stocks(source)`: pykrx(KRX_ID/KRX_PW) → 코스피200 `stock` 적재, 실패/미설정 시 정적 파일. 멱등(ticker upsert).
  - API: `get_config`·`list_stocks`·`set_stock_enabled`·`add/set/delete_keyword`·`set_source`·`set_period`(계약 `AdminApi`).
  - compose 서비스 블록 + gateway `/admin` 라우트.
- **P2 — 대시보드 설정 UI**: content `ui_router`에 `/ui/settings` + static 화면. admin API east-west 호출(HMAC).
- **P3 — news-feed 광역수집 + 연동**: 폴링마다 `GET /admin/config` → 종목·키워드로 네이버 검색, 소스 토글 반영, 기간 필터, RSS 카테고리 확대, 수집 dedup. `TICKER_DICT`/`feed_urls` 하드코딩 → admin config로.
- **P4 — issue-detector 연동**: 관심(config.stocks ∪ keywords)으로 랭킹 대상 제한/가중.

## 5. Implementation Split
- P1 admin 서비스·DB·시드·API → P2 대시보드 UI → P3 news-feed → P4 issue-detector. **각 Phase 독립 커밋.**

## 6. File Map (기계적)
- `[New] services/admin/` (app/{main,config,db}.py + domains/admin/{router,service,repository,models,schemas}.py + alembic) — P1
- `[New] services/admin/app/seed.py` + 정적 시드 파일(예: `services/admin/app/data/kospi200.json`) — P1
- `[Mod] docker-compose.yml` (admin 서비스 + admin_db) · `[Mod] infra/db/init/01-create-databases.sql` (`admin_db`) · `[Mod] gateway/app/config.py` (`/admin` 라우트) — P1
- `[Mod] services/content/app/domains/content/ui_router.py` + static (설정 화면) — P2
- `[Mod] services/news-feed/app/{worker,config,external_client}.py` (admin config 소비·광역 수집) — P3
- `[Mod] services/issue-detector/app/{worker,ranking}.py` (관심 목록 연동) — P4
- `[New] doc/design/admin/api-contract-admin.py` · `[New] doc/decisions/0016-*.md` · `[New] doc/ref/domains/04-admin.md`

## 7. Verification (Phase별)
- P1: 컨테이너 up → `admin_db` 테이블·시드 행수(≥150) 확인, `GET /admin/config` 200·형식. 단위: seed 멱등·config 조립.
- P2: 대시보드에서 종목 off → `GET /admin/config`에서 빠짐(왕복).
- P3: 소스 off → 미수집 / 키워드 추가 → 네이버 그 검색 수행(로그). 하드코딩 제거 확인.
- P4: 관심 밖 종목이 issue.selected 후보에서 제외.
- 전체: Database per Service(직접 접근 0), mypy·계약·기존 테스트 통과, 자격증명 커밋 0.

## 8. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /builder(P1) | **admin 서비스 신설** — `services/admin/`(FastAPI+SQLAlchemy+alembic), admin_db 4테이블(stock·keyword·source_toggle·collection_settings), `GET /admin/config` + 종목·키워드·소스·기간 CRUD(게이트웨이 HMAC dep). 시드(`app/seed.py`, 멱등 upsert). compose 블록·gateway `/admin` 라우트·infra `admin_db`. **검증**: 단위 1(seed), mypy strict 0(11파일+gateway), 실스택(admin_db 생성·마이그레이션 4테이블·시드 47·`build_config` 라이브: 활성 47·소스 ON·기간 1w). **이탈**: 시드가 코스피200(≥150) 아닌 **common.stocks 47(static)** — 네이버 200 스크래핑은 후속(P1 골격 우선, `seed_source` 스위치 유지). P2~P4는 후속 라운드. |
| 20260724 | /design | 운영자 설정 admin 서비스 + admin_db + 광역 수집. 결정: 단계화(P1~P4)·종목마스터 admin_db 승격(점진 이관)·코스피200 pykrx 시드(계정 신청, 정적 fallback). 사각지대: KRX 계정 활성 지연·종목 마스터 이중진실(이관 순서)·네이버 검색 폭증·대시보드→admin 결합. 신규 도메인 `admin`. 계약 `api-contract-admin.py` mypy 통과. ADR 0016. research 그래프 마스터 이관은 후속(범위 밖). |
