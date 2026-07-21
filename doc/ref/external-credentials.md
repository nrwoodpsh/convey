# 외부 자격증명 — 발급·확인 가이드

CONVEY 외부 연동에 필요한 키·계정 목록과 **발급 방법 + 확인(테스트) 명령**. 값은 `.env`에만(커밋 금지, `.env.example`엔 이름만).

> 가드레일: 텍스트 LLM은 로컬 Ollama만(외부 금지). 아래는 **시세·인증·미디어·발행**용 외부 연동이며 텍스트 추론과 무관.

## 우선순위 요약

| # | 자격증명 | 용도(라운드) | 키 필요? | .env 키 |
|:--|:---|:---|:--:|:---|
| 0 | (없음) pykrx 시세 | 시세(R①) | ❌ 키 없음 | — (KRX 공개, ADR 0008) |
| 0 | (없음) 공개 RSS | 뉴스 수집(R①) | ❌ 키 없음 | `FEED_URLS` |
| 1 | DART | 공시(R⑥) | ✅ 무료 | `DART_API_KEY` |
| 2 | 네이버 검색 | 뉴스검색(R⑥) | ✅ 무료 | `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET` |
| 3 | ECOS(한국은행) | 거시-국내(R⑥) | ✅ 무료 | `ECOS_API_KEY` |
| 4 | FRED(미 연준) | 거시-미국(R⑥) | ✅ 무료 | `FRED_API_KEY` |
| 5 | Supabase | 인증(R0) | ✅ 무료 | `SUPABASE_URL`·`SUPABASE_JWKS_URL`·`SUPABASE_AUD` |
| 6 | YouTube Data API | 발행(R⑤) | ✅ 무료 | `YOUTUBE_CLIENT_ID`·`YOUTUBE_CLIENT_SECRET`·`YOUTUBE_REFRESH_TOKEN` |
| 7 | 이미지 생성 API | broll(R④) | ✅ 유료 | `IMAGE_GEN_BASE_URL`·`IMAGE_GEN_API_KEY` |
| 8 | TTS API | 음성(R④) | 로컬 무료/유료 | `TTS_BASE_URL`·`TTS_API_KEY` (로컬 엔진 시 불요) |

> KIS OpenAPI는 ADR 0008로 **폐기**(pykrx 대체). 시세는 키 불필요.

---

## 0. 뉴스 RSS (키 없음)

- **용도**: `news-feed`가 공개 뉴스 RSS를 폴링 → 종목·사건 태깅 → `research.ingested`.
- **발급**: 불필요. 공개 RSS URL만 모으면 됨(예: 연합뉴스 경제·한국경제·매일경제 RSS).
- **확인**:
  ```bash
  curl -s "<RSS_URL>" | head -40   # <rss>…<item><title>…</title> XML이 나오면 OK
  ```
- **.env**: `FEED_URLS=https://a/rss,https://b/rss` (CSV).

## 1. KIS OpenAPI (한국투자증권 — 시세)

- **용도**: `market-feed`가 시세를 받아 `market.ticks` 발행.
- **발급**:
  1. **KIS Developers**(`apiportal.koreainvestment.com`) 가입 → 로그인.
  2. **App 등록** → **APP Key / APP Secret** 발급(실전/모의 구분 — 모의는 도메인·계좌 다름).
  3. 계좌번호(8자리-2자리) 확보.
- **확인** (OAuth 토큰 발급 — 성공하면 키 유효):
  ```bash
  curl -s -X POST "https://openapi.koreainvestment.com:9443/oauth2/tokenP" \
    -H "content-type: application/json" \
    -d '{"grant_type":"client_credentials","appkey":"$KIS_APP_KEY","appsecret":"$KIS_APP_SECRET"}'
  # → {"access_token":"…","expires_in":86400} 나오면 OK (토큰 24h)
  ```
- **.env**: `KIS_APP_KEY`·`KIS_APP_SECRET`·`KIS_ACCOUNT`. (모의면 `KIS_BASE_URL`도 모의 도메인으로)
- **주의**: 토큰 24h 캐시·재발급, 호출 유량 제한. 부패방지 계층(`market-feed/external_client.py`)에 가둠.

## 2. Supabase (인증)

- **용도**: 로그인·JWT 발급은 Supabase, 게이트웨이가 JWKS로 검증(ADR 0007).
- **발급**:
  1. `supabase.com` → 프로젝트 생성 → **Project URL** 확보(`https://<ref>.supabase.co`).
  2. **비대칭 JWT 서명키 사용** — Dashboard **Project Settings → JWT Keys**에서 **asymmetric(ES256/RS256) 서명키**를 활성화(우리 검증기는 JWKS 기반). *(레거시 HS256 공유시크릿만 쓰면 검증기를 HS256 모드로 바꿔야 함 — 비대칭 권장.)*
  3. 테스트 사용자 생성(Authentication → Users).
- **확인**:
  ```bash
  # (a) JWKS 공개키 노출 확인
  curl -s "$SUPABASE_URL/auth/v1/.well-known/jwks.json"   # {"keys":[…]} 나오면 OK
  # (b) 토큰 발급(비밀번호 로그인) — anon key 필요
  curl -s -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
    -H "apikey: <ANON_KEY>" -H "content-type: application/json" \
    -d '{"email":"t@t.com","password":"…"}'   # access_token 획득
  # (c) 그 토큰으로 게이트웨이 호출 → 200 이면 검증 통과
  curl -H "Authorization: Bearer <access_token>" http://localhost:8080/research/search?q=삼성
  ```
- **.env**: `SUPABASE_URL`·`SUPABASE_AUD=authenticated`. (게이트웨이가 `iss={URL}/auth/v1`·JWKS로 검증)

## 3. 이미지 생성 API (broll — 커모디티)

- **용도**: `image-gen`(신규)이 배경 이미지 생성. 제공자 선택(Stability·Replicate·OpenAI Images 등). **이미지 생성은 외부 허용**(텍스트 아님).
- **발급**: 택한 서비스 콘솔에서 API 키 발급.
- **확인**: 해당 서비스의 "이미지 1장 생성" 예제 호출 → 이미지 URL/바이너리 반환.
- **.env**: `IMAGE_GEN_BASE_URL`·`IMAGE_GEN_API_KEY`. 부패방지 계층에 가두고 **원문 전체 반출 금지(프롬프트만)**.

## 4. TTS API (음성 — 커모디티)

- **용도**: `tts`(신규)가 내레이션 음성 생성. 한국어 품질 고려(Naver Clova Voice·Google Cloud TTS·ElevenLabs 등).
- **발급**: 택한 서비스 API 키(또는 서비스계정).
- **확인**: 짧은 문장 합성 호출 → 오디오(mp3/wav) 반환.
- **.env**: `TTS_BASE_URL`·`TTS_API_KEY`.

## 5. YouTube Data API v3 (발행)

- **용도**: `publishing`이 승인 완성본을 업로드. **사람 승인(content.approved) 후에만**.
- **발급**:
  1. **Google Cloud Console** → 프로젝트 생성 → **YouTube Data API v3** 사용 설정.
  2. **OAuth 동의 화면** 구성 → **OAuth 2.0 클라이언트 ID**(데스크톱/웹) 생성 → client id/secret.
  3. OAuth 플로우로 **refresh token** 획득(스코프 `https://www.googleapis.com/auth/youtube.upload`).
- **확인** (refresh token으로 채널 조회 성공하면 유효):
  ```bash
  # access token 갱신
  curl -s -X POST https://oauth2.googleapis.com/token \
    -d client_id=$YOUTUBE_CLIENT_ID -d client_secret=$YOUTUBE_CLIENT_SECRET \
    -d refresh_token=$YOUTUBE_REFRESH_TOKEN -d grant_type=refresh_token
  # 그 access_token으로:
  curl -s "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true" \
    -H "Authorization: Bearer <access_token>"   # 채널 id 나오면 OK
  ```
- **.env**: `YOUTUBE_CLIENT_ID`·`YOUTUBE_CLIENT_SECRET`·`YOUTUBE_REFRESH_TOKEN`. 커밋 금지.

---

## 이미 준비된 것(키 불필요·로컬)

| 항목 | 상태 |
|:---|:---|
| Ollama(로컬 LLM·qwen3:14b) | ✅ `localhost:11434` |
| Neo4j(로컬 컨테이너) | ✅ `NEO4J_AUTH=neo4j/convey-dev-pw` |
| Postgres·Kafka(로컬 컨테이너) | ✅ 5432 · 29092 |

## 소스 4종 발급·확인 (R⑥ — 전부 무료)

### DART (공시) — `DART_API_KEY`
1. opendart.fss.or.kr → 회원가입 → **인증키 신청/관리 → 인증키 신청**(즉시 발급, 40자리)
2. 확인: `https://opendart.fss.or.kr/api/list.json?crtfc_key=키&page_count=1` → `status`가 `000`이면 정상

### 네이버 검색(뉴스) — `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET`
1. developers.naver.com → 애플리케이션 등록 → **사용 API "검색"** 선택(웹 서비스 URL은 `http://localhost` 가능 — 실제 도메인 불필요)
2. 확인: `curl -H "X-Naver-Client-Id: ID" -H "X-Naver-Client-Secret: SECRET" "https://openapi.naver.com/v1/search/news.json?query=삼성전자&display=1"` → `items` 반환
   - 데이터랩(검색어트렌드)은 **다른 API**(이슈 신호용) — 뉴스 근거는 "검색"

### ECOS (한국은행 거시) — `ECOS_API_KEY`
1. ecos.bok.or.kr → 회원가입 → **OpenAPI → 인증키 신청**(즉시)
2. 확인: `https://ecos.bok.or.kr/api/StatisticSearch/키/json/kr/1/1/722Y001/M/202501/202501` → 기준금리 행
   - 주기별 날짜 포맷 주의: D=YYYYMMDD, M=YYYYMM, Y=YYYY. 응답은 오름차순.

### FRED (미 연준 거시) — `FRED_API_KEY`
1. fred.stlouisfed.org → My Account → `fredaccount.stlouisfed.org/apikeys` → **Request API Key**(즉시, 32자리)
2. 확인: `https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=키&file_type=json&limit=1&sort_order=desc`

## 착수 순서 권장

1. **RSS**(키 없음) + **pykrx**(키 없음) → 파이프라인 입구 완성. ✅ 완료
2. **DART·네이버·ECOS·FRED**(무료) → 근거 소스 확장(R⑥). ✅ 완료
3. **Supabase**(무료) → 실제 인증(비대칭 JWT 키 활성화 필수). 멀티유저/공개 시.
4. **YouTube**(무료) → 발행(승인 게이트 후). TTS는 로컬 엔진(무료) 권장.
5. **이미지 생성**(유료) → broll. 없으면 로컬 타이틀 카드.
