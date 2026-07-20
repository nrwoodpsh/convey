# ADR 0008 — 콘텐츠 데이터 소스: pykrx + 뉴스·공시·거시 (KIS 실시간 제외)

- **상태**: 채택 (2026-07-20)
- **맥락**: CONVEY는 트레이딩이 아니라 **콘텐츠**다. 실시간 틱 시세(KIS OpenAPI)는 과하다. 알파(근거·관계·인과)엔 **공시·거시·뉴스**가 더 substance(사건·맥락·인과의 원천)이고 대부분 **무료 공식 API**다.
- **결정**:
  - **시세**: KIS 제외 → **`pykrx`**(KRX 공식 데이터, 무료·키 불필요). 종가·등락률·거래량(차트·이슈감지·알파3 렌더 데이터).
  - **콘텐츠 소스 3종**:
    - **뉴스**: 공개 RSS(키 없음) — 화제·사건.
    - **공시**: **DART**(opendart.fss.or.kr, 무료 키) — 실적·공시 = **사건/인과의 핵심**.
    - **거시**: **한국은행 ECOS**(무료 키) + **FRED**(무료 키) — 금리·환율·물가 = 맥락.
  - **데이터 모델 매핑**:
    - 뉴스·공시 = `Article`(원문+출처/라이선스) + `Event`(실적·공시 사건). 공시는 별도 엔티티 없이 Article/Event로 흡수(출처=DART 링크).
    - 거시 = **`MacroIndicator`**(신규 fact: 지표명·값·시점·출처). 그래프 노드 아님 — Postgres 사실 + 스크립트 맥락·이슈 신호로 사용.
- **트레이드오프**: KIS 실시간 정밀도 포기(콘텐츠엔 불필요) vs 무료·풍부한 사건/맥락. 소스 4종(pykrx·RSS·DART·ECOS/FRED)의 부패방지 계층 필요.
- **영향**:
  - `market-feed` → **pykrx** 시세(`market.ticks`). `news-feed` → RSS + **DART 공시**. 거시는 news-feed 확장 또는 신규 `macro-feed`(ECOS/FRED → `research.ingested`/사실).
  - `research`에 `MacroIndicator` 사실 추가. 그래프는 그대로(Stock·Event·Sector·Company; 공시=Event).
  - `.env`: KIS 제외, `DART_API_KEY`·`ECOS_API_KEY`·`FRED_API_KEY`·`FEED_URLS` 추가.
- **대안(기각)**: KIS OpenAPI(실시간 — 콘텐츠엔 과함·유량제한). Naver Finance 스크래핑(비공식·ToS 회색). ← pykrx가 무료·공식.
- **관련**: [0004](알파 — 근거·정확), [0005](그래프), [0006](POC 범위). 초기 "KIS 시세" 가정을 대체.
