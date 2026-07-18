# 용어집 — CONVEY (terms)

**주식/시장 쇼츠** 파이프라인의 핵심 용어. 코드 식별자(영문)와 자연어(한글)를 함께 고정한다.

## 리서치·데이터 (research)

| 용어 | 영문/코드 | 정의 | 혼동 주의 |
|:---|:---|:---|:---|
| 종목 | stock | 주식 종목(ticker·이름·섹터) | 데이터 분류의 1차 기준 |
| 사건 | event | 시장 사건(실적·공시·급등락 등), 종목·일자에 연결 | ≠ 기사. 사건은 "무슨 일", 기사는 그 근거 |
| 기사 | article | 수집 원문 + 출처 URL·라이선스 | 반드시 출처·라이선스 동반(무출처 생성 금지) |
| 시세 | price / tick | 종목 시세 스냅샷(차트·이슈감지용) | KIS 등 외부 소스 |
| 이슈 종목 | issue stock | 그날 뜨는 종목(급등락+뉴스 빈도) | `issue-detector` 산출 |
| 임베딩 | embedding | 기사 텍스트를 벡터로(로컬 `nomic-embed-text`), pgvector 저장 | **의미검색 보조**. 정확 조회는 SQL |
| 지식 그래프 | knowledge graph | 종목·사건·섹터를 노드, 관계·인과를 엣지로 저장(Neo4j) | 알파① 엔진. 관계형 조인과 달리 다홉 추론 |
| 노드 · 엣지 | node · edge | 노드=Stock·Event·Sector, 엣지=AFFECTS·SUPPLIES·COMPETES | 엣지 = 인과·수혜·경쟁 |
| 추출 | extraction | 뉴스 → 엔티티(NER)+관계추출 → 그래프 엣지 | 품질의 원천. news-feed+research |
| RAG | rag / retrieval | 그래프 traversal(관계) + 사실/벡터 회수를 합쳐 프롬프트에 주입 | 검색은 `agent`가 `/search`로, 저장은 `research` |

## 콘텐츠 (content)

| 용어 | 영문/코드 | 정의 | 혼동 주의 |
|:---|:---|:---|:---|
| 생성 잡 | generation_job | 콘텐츠 하나를 만드는 파이프라인 실행 단위(단계 상태) | ≠ 완성본. 잡은 "과정" |
| 스크립트 | script | 쇼츠 대본(내레이션·자막) + **인용 근거** | 코드 스크립트 ✗. 모든 수치는 출처에 못박음 |
| 근거/인용 | grounding / citation | 스크립트 수치를 research 데이터·출처에 결속 | 환각 금지 = 알파1 |
| 자산 | asset | broll 이미지·음성 등 합성 재료(외주 생성) | ≠ 완성본 |
| 쇼츠 | shorts | 차트·수치 렌더 + 자산을 ffmpeg 합성한 mp4 | 발행 대상 = YouTube Shorts |
| 승인 | approval / review | 완성본을 사람이 검토·발행 허가 | ≠ 발행. 승인 후 발행 |

## 선별·미디어 (컴포넌트)

| 용어 | 영문/코드 | 정의 | 혼동 주의 |
|:---|:---|:---|:---|
| 이슈 감지기 | issue-detector | 시세급변+뉴스빈도 → 이슈 종목 랭킹(워커) | 도메인 ✗, 컴포넌트. 알파2 |
| broll 생성 | image-gen | 배경 이미지 외부 API 래퍼 | **커모디티(외주)** |
| TTS | tts | 음성합성 외부 API 래퍼 | **커모디티(외주)** |
| 영상합성 | video-assembly | ffmpeg로 **정확한 차트·수치 오버레이** + 합성 → mp4 | **알파3(자체)**. 로컬 |
| 영상클립 | video-clip | 생성형 영상 클립(외부) | 현재 **보류**(차트+broll 포맷엔 불필요) |
| 부패방지 계층 | anti-corruption layer | 외부 API를 내부 모델로 격리하는 어댑터(`external_client.py`) | 외부 스키마 유출 방지 |

## 발행 (publishing)

| 용어 | 영문/코드 | 정의 | 혼동 주의 |
|:---|:---|:---|:---|
| 채널 | channel | 발행 대상 플랫폼(1차: YouTube) | ≠ Kafka 토픽 |
| 발행 | publication / publish | 승인 완성본을 외부 채널 업로드 | 사람 승인 후에만 |
| 발행 요청 | publish_request | 발행 승인 워크플로우 단위 | 승인 없이 업로드 금지 |

## 크로스커팅

| 용어 | 영문/코드 | 정의 | 혼동 주의 |
|:---|:---|:---|:---|
| 알파 | alpha | 방어가능한 차별점(정확·선별·렌더·양산) | 투자 우선순위 근거(ADR 0004) |
| 커모디티 | commodity | 외부가 이미 잘하는 것(broll·TTS·스티칭·업로드) | 외부 API로 얇게 |
| 아웃박스 | outbox | 트랜잭션 커밋 후 이벤트 발행 보장 | 원형 계승(간이) |
| 신뢰헤더 | HMAC trust header | 서비스 간 직접 호출 인증 | ≠ JWT(외부 진입용) |
| 잡 | job | Kafka로 구동되는 비동기 작업 단위 | 조회성은 동기 API |
