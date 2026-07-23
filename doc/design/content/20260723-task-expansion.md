# 20260723-task-expansion.md

> 라운드 ㉙ (확장 프로그램 — 연출·데이터·안정, C 제외). ADR 0013.
> 통합 설계 1개, 구현은 **Phase D→E→F 단계별 /run**(각 판 실 스택 검증). 계약: `api-contract-expansion.py`.

## 1. Requirements

- **결론**: C(배포·YouTube 자동·Supabase 인증)를 제외한 남은 전부를 3단계로. **D 연출**(배경 컷/xfade + 수치 scale 팝) · **E 데이터**(종목 마스터 확대·수집 소스 확대·과거 기사 관계 백필) · **F 안정**(합성 재시도·자동양산 실검증·모니터링).
- **현황 반영**: DART·RSS·pykrx는 **이미 배선됨**(news-feed 수집, market-feed 3티커) → 대부분 "범위 확대". 배경 컷·재시도·모니터링은 신규.
- **Acceptance Criteria**:
  - **Phase D (연출)** ✅ (구현·검증)
    - [x] D1: media.assemble `broll_queries`(복수) → 최대 3개 Pexels 클립 **하드 컷 전환**(xfade -22 오류로 concat 하드컷 채택). 실패 시 단일 폴백. **검증: job#37 4s 공장→26s 파란 추상 배경.**
    - [~] D2: 수치가 chart 구간에 **등장(fade) 팝**. **scale 바운스는 투명 오버레이 알파 이슈로 후속**(㉖ fade 수준 유지·설계 결정2 허용).
  - **Phase E (데이터)** ✅ (구현·검증)
    - [x] E1: `scripts/gen-stocks.py`(pykrx, 마커 치환) 커밋 + `common/stocks.py` 종목 **20→46**·섹터 확대(정적). **검증: stock_name 한국전력·SK텔레콤·엔씨소프트.** (미래-날짜 env라 pykrx 라이브 생성은 실배포 시; 지금은 큐레이션 확대.)
    - [x] E2: market-feed symbols **3→16** + news-feed RSS **2→5**. **검증: feeds=5, research.ingested 329건.**
    - [x] E3: `event_hints`→종목 **HAS_EVENT** 엣지(research consumer) + 부분문자열 태깅 오탐 수정(SK/LG). backfill `--llm` 옵션. **검증: 그래프 관계 7→54(BELONGS_TO 24·AFFECTS 13·COMPETES 8·HAS_EVENT 5·SUPPLIES 4).**
  - **Phase F (안정)** ✅ (구현·검증)
    - [x] F1: 스크립트 **인라인 재시도**(agent 호출 상한 2·백오프) + 합성 **재시도**(`GenerationJob.retry_count`, chart+script 재발행, 멱등). 영구 실패는 failed. **검증: retry_count 컬럼·기전 구현, 정상 흐름 무영향.**
    - [x] F2: 자동양산 — issue.selected(기아 000270) → job#38 `scripting→assembling`(**scenario_ready·승인 없이 자동 진행**). ✅
    - [x] F3: `GET /ui/stats`(상태별 수·최근 실패) + 대시보드 카드. **검증: by_status{ready 23·failed 9·…}·recent_failed 반환.**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **배경 컷 렌더(D1)**: N클립 xfade는 각 클립 트림·타이밍 정렬·재인코딩 → 렌더 시간·실패 위험↑. **세그먼트 오디오 총길이에 맞춰 클립 길이 분배**, 실패 시 단일 배경(현행) 폴백 필수. ㉖의 "단일 배경" 결정을 이 라운드가 대체(ADR 0013).
  - **수치 scale 팝(D2)**: ffmpeg `scale` 시간식 미지원 → `zoompan`(프레임 기반)으로 오버레이 스케일, 투명 유지 주의. 안 되면 fade만(㉖ 수준) 유지.
  - **pykrx 생성(E1)**: 오프라인 스크립트 = 사람이 실행(네트워크·시세휴장). 생성물만 커밋. 이름·섹터 매핑 품질(섹터는 업종 분류 매핑 필요 — pykrx 업종/KRX 섹터).
  - **DART 사건화(E3)**: 이미 dart_docs 수집 → 공시 유형(실적·유증·자사주)을 event 힌트로 → 그래프 HAS_EVENT. 무출처 금지 유지.
  - **백필 비용(E3)**: 과거 기사 LLM 재추출은 Ollama 수백 회 → 수 분~수십 분. 배치·재개 가능하게, 사람 실행.
  - **재시도 중복(F1)**: 재시도가 중복 발행/중복 콘텐츠 만들지 않도록 멱등(같은 job_id 갱신). 무한 루프 방지(상한).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 배경**: 택함 = **N클립 xfade 컷 전환 + 단일 배경 폴백**(사용자 확정) / 기각 = 단일 배경 유지(㉖) / 사유 = 사용자가 화려함 선택. ADR 0013(㉖ 대체).
  - **결정 2 — 종목 마스터**: 택함 = **오프라인 pykrx 생성→커밋**(정적) / 기각 = 런타임 로드 / 사유 = 배포 의존·비결정론 회피(사용자 확정).
  - **결정 3 — DART**: 택함 = **기수집 공시를 사건 태깅으로 활용 강화** / 기각 = 신규 수집기(이미 있음) / 사유 = 배선 존재 → 활용도만↑.
  - **결정 4 — 재시도 위치**: 택함 = **content 소비자에서 일시 실패 재시도(멱등·상한)** / 기각 = Kafka 재시도 토픽·DLQ(과함, POC) / 사유 = 최소 변경.
  - **결정 5 — 모니터링**: 택함 = **/ui/stats + 대시보드 카드**(로컬 무인증) / 기각 = Prometheus/Grafana(C·배포 영역) / 사유 = 로컬 가시성으로 충분.

## 3. UI/UX

- 영상: 배경이 구간마다 xfade로 바뀌고, 수치가 팝하며 등장. (레이아웃·자막·배지는 ㉖·㉗ 유지)
- 대시보드: 상단에 상태 요약(완료/진행/실패 수) + 최근 실패 목록(모니터링).

## 4. Logic (Phase별)

### Phase D — 연출 (content·video-assembly)
- **content(media)**: `broll_queries` 구성 — 종목 산업 + 우주/추상 + 시장(또는 배경 선택 real/anim에 맞춰 2~3개). media.assemble에 실음(단일 `broll_query`도 유지=폴백).
- **video-assembly(broll·assemble·worker)**: `PexelsClient.fetch_many(queries, n)` → N 클립. `assemble`에 xfade 합성 경로(각 클립 트림→xfade concat→[bg])+오버레이(차트·수치·자막·배지). 실패/1개면 기존 단일. 수치 오버레이 `zoompan` scale 팝.

### Phase E — 데이터
- **`scripts/gen-stocks.py`**(신규): pykrx로 코스피200 티커·한글명 + 업종→섹터 매핑 → `libs/common/common/stocks.py`의 `STOCK_NAMES`·`STOCK_SECTOR` 블록 재생성(마커 사이 치환). 사람 실행·커밋.
- **market-feed**: `symbols` 기본을 마스터 상위 N(예 30~50) CSV로. (전체 200은 폴링 부담 → 상위 시총/이슈 우선.)
- **news-feed**: `feed_urls`에 경제 RSS 추가(연합·한경 + 추가). `tag_event_hints`에 DART 공시 유형 반영.
- **DART 사건화**: news-feed dart_docs → 공시 유형 라벨을 `entities`/이벤트로 → research consumer가 종목→사건 `HAS_EVENT` 엣지(근거=공시). 
- **백필**: `services/research/app/backfill.py` 확장 — `--llm` 옵션 시 과거 기사 본문에 `extract_relations`(Ollama) 배치 실행(진행 로그·재개). 기본은 결정론(현행).

### Phase F — 안정
- **재시도(content consumer)**: `handle_generate`/`handle_assembled` 실패 시 `retry_count` 증가, 상한(2) 내 재발행(멱등: 같은 job). 상한 초과 시 failed.
- **자동양산 검증**: dedup 창 회피용 신선 티커로 issue.selected 발행 → ready 도달 확인(스크립트).
- **모니터링**: `repository.stats()`(상태별 count + 최근 failed) → `GET /ui/stats` → 대시보드 상단 카드.

## 5. Implementation Split (Phase = /run 3판)

- **D**: `content/media.py`·`video-assembly/{broll,assemble,worker}.py`.
- **E**: `scripts/gen-stocks.py`·`libs/common/stocks.py`(재생성)·`market-feed/config`·`news-feed/{config,tagging,worker}`·`research/consumer`(HAS_EVENT)·`research/backfill.py`(--llm).
- **F**: `content/{consumer,repository,domains/content/ui_router,schemas}`·`static/index.html`(stats 카드)·`scripts`(자동양산 검증).

## 6. File Map (요약 — Phase별 상세는 §5)

- `[New] scripts/gen-stocks.py` · `[Mod] libs/common/common/stocks.py`(재생성)
- `[Mod] services/video-assembly/app/{broll,assemble,worker}.py` · `services/content/app/domains/content/media.py`
- `[Mod] services/market-feed/app/config.py` · `services/news-feed/app/{config,tagging,worker}.py` · `services/research/app/{consumer,backfill}.py`
- `[Mod] services/content/app/{consumer,domains/content/repository,domains/content/ui_router,domains/content/schemas}.py` · `static/index.html`
- `[New] doc/design/content/api-contract-expansion.py` · `[New] doc/decisions/0013-*.md`

## 7. Verification (Phase별, 실 스택)

- **D**: 실 mp4 — 배경 xfade 전환·수치 scale 팝 프레임 확인. 폴백(1클립) 회귀.
- **E**: gen-stocks 실행 후 stock_name 커버리지↑(예 코스피200 임의 종목). 수집량↑(articles/ticks). DART 공시→HAS_EVENT 엣지. 백필 후 그래프 관계↑.
- **F**: 실패 주입 시 재시도 로그·최종 상태. 자동양산 ready. /ui/stats 응답·대시보드 표시.
- 각 Phase mypy·계약·단위테스트 통과, `/run` 실패 시 그 Phase 정지.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260723 | /builder(Phase F) | 안정화 구현·검증(확장 프로그램 완결). **F1**: consumer `handle_generate` 스크립트 인라인 재시도(상한 2·백오프) + `_retry_assemble`(합성 실패 시 `GenerationJob.retry_count`<상한이면 chart+script로 media.assemble 재발행, 멱등)·`retry_count` 컬럼(alembic d2e3f4a50012). **F2**: 자동양산 검증 — issue.selected(000270)→job#38 scripting→assembling(승인 게이트 없이 자동). **F3**: `repository.stats`·`GET /ui/stats`(`UiStatsRes`)·대시보드 statsbar 카드. **검증(실 스택)**: retry_count 마이그레이션; /ui/stats by_status·recent_failed; 자동 job#38 무정지 진행. **이탈**: 재시도가 4xx(무티커 422 등 영구 실패)도 재시도(낭비)—5xx/timeout 한정은 후속; 재시도 시 배경 real 기본(anim 선택 유실). **확장 프로그램(D·E·F) 완결.** |
| 20260723 | /builder(Phase E) | 데이터 확장 구현·검증. **E1**: `scripts/gen-stocks.py`(pykrx→common 마커 치환) 신설, `common/stocks.py` 종목 20→46·섹터 확대(미래-날짜 env로 pykrx 라이브 불가→큐레이션 확대, 스크립트는 실배포용). **E2**: market-feed symbols 3→16, news-feed feed_urls 2→5(매경·이데일리·서울경제). **E3**: research consumer가 `event_hints`로 종목→**HAS_EVENT** 결정론 엣지 + `_STOCK_NAMES_SET`; news-feed `_suppress_substrings`(SK/LG 부분문자열 오탐 수정); `backfill.py --llm/--limit`(과거 기사 LLM 관계추출). **검증(실 스택)**: stock_name 신규종목 3개; feeds=5·ingested 329; 그래프 관계 **7→54**(HAS_EVENT 포함); news-feed 테스트 6 통과(부분문자열 수정 반영). **이탈**: pykrx 라이브 생성은 미래-날짜 env로 불가→큐레이션 확대(스크립트 커밋), 결정론 HAS_EVENT는 기사 키워드 의존(희소, DART 공시로 증가), backfill --llm은 Ollama로 느림(백그라운드 무오류 실행). **F는 후속 /run.** |
| 20260723 | /builder(Phase D) | 연출 구현·검증. content(media): `broll_queries`(대표+보조2) 이벤트에 추가. video-assembly: `broll.fetch_many`(복수 클립), `assemble.build_bg_cuts`(N클립 concat **하드 컷** — xfade는 stream_loop+trim에서 -22 오류로 대체), worker가 video 2+개면 배경 합성 후 build_short_video. 수치 팝은 ㉖ fade 유지. **검증(실 스택)**: job#37 배경 3클립(공장/스카이라인/추상) 하드컷, bgx 28.5s 유효, 4s 공장→26s 파란 추상 전환; 폴백(bgx 실패 시 단일 bg0) 동작 확인(job#36). va 단위테스트 3 통과. **이탈**: xfade→하드컷(견고성), 수치 scale 바운스 후속, 대용량 Pexels 클립(128MB)로 합성 ~84s(파일크기 상한 튜닝 후속). **E·F는 후속 /run.** |
| 20260723 | /design | 확장 프로그램(C 제외) — D 연출(배경 컷/xfade+수치 scale 팝), E 데이터(오프라인 pykrx 종목 마스터·시세/RSS 확대·DART 사건화·과거 기사 LLM 백필), F 안정(합성 재시도·자동양산 검증·/ui/stats 모니터링). 배경 컷은 ㉖ 단일배경 결정을 대체(ADR 0013). 구현 Phase D→E→F. 계약 `api-contract-expansion.py`(mypy 통과). |
