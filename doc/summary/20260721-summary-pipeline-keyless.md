# 20260721 — 요약: 근거 기반 쇼츠 end-to-end (키 없는 코어) 관통

- **Task**: `doc/design/content/task-pipeline-keyless-20260721.md` (라운드⑤, ADR 0006·0008)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 PG·Neo4j·Kafka·Ollama·ffmpeg)
- **상태**: `POST /content/generate` 한 방으로 근거 인용 쇼츠 mp4까지 **전 스택 실서비스 관통**. 6개 AC 전부 충족.

## 개요

부품(agent `build_script`·`render_chart`·`build_short`)은 이미 있었고, 이번 라운드는 이를 **하나의 파이프라인으로 배선**했다. 외부 broll/TTS(키 필요) 없이 — 배경은 로컬 타이틀 카드, 오디오는 무음 — 리서치→스크립트→차트→mp4까지 키 없이 끝까지 돈다. 수치는 사실에 못박고(알파1), 차트는 PriceTick과 1:1(알파3).

## 파이프라인 (관통 확인)

```
POST /content/generate → 잡(pending) → content.generate
  → [content] scripting: agent POST /agent/script (HTTP+HMAC)
       agent: /research/search(facts + price) → build_script(수치=사실슬롯, 연결문장=Ollama)
     → Script 저장 → assembling: media.assemble
  → [video-assembly] render_chart + 타이틀카드(로컬배경) + build_short(무음) → mp4
     → content.assembled
  → [content] Content 저장 → status=ready (사람 승인 대기)
```

## 변경사항 (BE)

**research** — 가격 근거 공급
- `domains/research/repository.py` — `latest_price`(최근 종가 시계열·직전대비 등락률·출처), `price_source_url`
- `domains/research/{service,schemas,router}.py` — `/search`에 `ticker` 파라미터 + `price`(PriceEvidence) 부착

**agent** — 근거 회수 + 스크립트 API
- `rag/retriever.py` — `Retriever.gather`(research `/search` 실 HTTP+HMAC → price·facts), 스텁 해소
- `main.py` — `POST /agent/script`(retriever→build_script→ScriptRes), 동기 LLM 호출자(llm-inference `/generate`)

**content** — 오케스트레이션(핵심)
- `consumer.py` — `handle_generate`(scripting→agent→Script 저장→`media.assemble`) + `handle_assembled`(Content 저장→ready) + 두 소비 루프
- `domains/content/models.py` — `Script`·`Content` 엔티티 추가
- `config.py` — `topic_assemble`·`topic_assembled` / `main.py` — 두 백그라운드 소비자 등록

**video-assembly** — 합성 워커 배선
- `worker.py` — `media.assemble` 소비 → render + `render_title_card` + build_short → `content.assembled`(sleep 스텁 해소)
- `render.py` — `render_title_card`(키 없는 로컬 배경) / `config.py` — assemble 토픽

## API/계약 변경

- `doc/design/content/api-contract-pipeline-keyless.py` (신규) — ScriptRequest/Response·ChartData·MediaAssembleEvent·ContentAssembledEvent·PriceEvidence. contract-gate 통과.
- `doc/design/research/api-contract.py` `SearchRes`에 optional `price`(PriceEvidence) 추가(이탈 — 사실 수치 공급).

## DB

- content_db에 `scripts`·`contents` 테이블 추가(dev는 `create_all`). research_db `price_ticks`에 실 KRX 25일 백필(005930·000660·035420).
- **후속**: Alembic 베이스라인(scripts·contents·price_ticks unique) — 현재 alembic versions 없는 기존 갭과 함께.

## 검증 (전부 실서비스·로컬)

- 전 스택 기동(llm-inference·research·agent uvicorn + video-assembly worker + Kafka/PG/Neo4j/Ollama) → 드라이버로 관통.
- AC2 상태전이 pending→scripting→assembling→ready 관찰.
- AC3 mp4 **h264 1080×1920 6s + aac**(ffprobe).
- AC4 스크립트 인용 전부 source_url 동반(무출처 0).
- AC5 차트 close 254,500 / 등락 +4.30% == research `PriceTick` 1:1.
- AC6 외부 broll/TTS 미사용(로컬 배경+무음), 원문 전체 외부 반출 0.
- mypy --strict clean, 기존 단위(agent builder 3·video render/assemble 3) 회귀 없음.

## 특이사항 (남은 작업·후속)

- **키 없는 경로 완성**: 리서치→쇼츠 mp4까지 무키 전자동. 발행(YouTube 업로드)은 사람 승인 후(가드레일).
- **후속(키 발급 후)**: image-gen/tts fan-out(외부 broll·음성), Supabase 인증, DART/ECOS/FRED 소스.
- **후속(정리)**: Alembic 베이스라인, compose 미디어 공유 볼륨(발행 라운드 — content/video-assembly/publishing이 mp4 공유), `/agent/script`는 가격 근거 없으면 422(이슈 종목 전제).
- 커밋: 아직(사람 게이트 — `/commit`).
