# task-pipeline-keyless-20260721.md

> 라운드 ⑤ (근거 기반 쇼츠 end-to-end — **키 없는 코어**). 알파1·3·4.
> 계약 정본 = `api-contract-pipeline-keyless.py`. 여기엔 자연어 설계만.

## 1. Requirements

- **결론**: 부품(agent `build_script`·`render_chart`·`build_short`)은 이미 있고 검증됐다. 이 라운드는 이들을 **하나의 파이프라인으로 배선**해, 이슈 종목 하나로 `POST /content/generate`를 부르면 **근거가 인용된 쇼츠 mp4**가 로컬에 생기게 한다. 외부 API(broll·TTS) 없이.
- **Scenario**: 사람이 이슈 종목으로 `POST /content/generate` → content가 잡을 만들고 → agent가 research 근거로 스크립트 생성 → video-assembly가 정확 차트+합성으로 mp4 → 잡 `ready`(사람 승인 대기).
- **Objective**: 키 없이 파이프라인 끝까지(리서치→스크립트→차트→mp4)를 관통시킨다. 수치는 사실에 못박고(알파1), 차트는 PriceTick과 1:1(알파3), 흐름은 이벤트로 재개 가능(알파4).
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract-pipeline-keyless.py`가 contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: `POST /content/generate` 1건 → 잡 상태가 `pending→scripting→assembling→ready`로 전이, `GET /content/jobs/{id}`로 관찰
  - [ ] AC3: 완성 mp4가 로컬 볼륨에 실재 + **h264 9:16**(ffprobe로 코덱·1080×1920 확인), 재생 가능
  - [ ] AC4: 스크립트의 모든 수치가 `Citation`(source_url+ref_id)에 결속 — **무출처 수치 0**(알파1)
  - [ ] AC5: 차트 오버레이 수치가 research `PriceTick` 사실과 **1:1 일치**(수치 오차 0, 알파3)
  - [ ] AC6: 외부 broll/TTS **미사용**(배경=로컬 타이틀 카드, 오디오=무음). 외부로 원문 전체 반출 0

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대(부딪히면 배울 함정)**:
  - `content.consumer.handle_generate`가 로그 스텁 → 잡 진행·agent 호출·assemble 트리거 전부 신규.
  - `agent.Retriever.search`가 빈 문자열 스텁 → 실제 `/research/search` HTTP 미구현. agent엔 스크립트 HTTP 엔드포인트도 없음(`/chat`만).
  - **가격 근거 공백**: `build_script`·`render_chart`는 `close·change_pct·series`(PriceTick)가 필요한데 `/research/search`는 지금 facts(Article)만 반환 → 가격 근거 공급 경로 신설 필요.
  - `video-assembly.worker.run`이 sleep 스텁 → `media.assemble` 소비→render→compose→회신 신규.
  - `build_short`는 배경 `image_path`(켄번즈 base)를 요구 → 키 없는 경로엔 외부 broll이 없으므로 **배경을 로컬 생성**해야 함.
  - 미디어 바이너리 저장 위치·볼륨(로컬) — 컨테이너 간 공유 경로.
- **핵심 결정**(택한 안 + 기각한 대안):
  - **결정 1 — 오케스트레이션 형태**: 택함 = **하이브리드**. content→agent는 **요청/응답 HTTP**(east-west+HMAC, 스크립트는 동기 1콜), content→video-assembly는 **이벤트**(`media.assemble`→`content.assembled` fan-in). / 기각 = 전부 동기 HTTP(video-assembly는 워커·무거운 ffmpeg라 비동기가 맞음)·전부 이벤트(스크립트까지 이벤트면 왕복 복잡) / 사유 = 서비스 성격에 맞춤(agent=계산, video-assembly=배치 워커), 재개·양산(알파4).
  - **결정 2 — 가격 근거 공급**: 택함 = **`/research/search` 응답에 optional `price`(PriceEvidence) 추가** — research가 소유한 PriceTick에서 최신 종가·창내 등락률·시계열 산출(사실·출처 동반). / 기각 = 별도 `/research/price` 엔드포인트(계약 하나 더)·agent가 DB 직접(경계 위반) / 사유 = 근거 회수는 이미 `/search` 한 곳(계약 최소), 사실 소유자(research)가 산출.
  - **결정 3 — 키 없는 배경·오디오**: 택함 = **배경=로컬 타이틀 카드(matplotlib), 오디오=무음(anullsrc)**. broll/TTS는 키 발급 후 fan-out으로. / 기각 = 지금 외부 API(키 없음)·생성형 영상(ADR 0006 제외) / 사유 = 키 없이 end-to-end 관통이 목표, 정확 렌더(알파3)는 이미 우리 것.
  - **결정 4 — 미디어 저장**: 택함 = **로컬 볼륨 경로**(`media_dir`), content_db엔 경로·메타만(media task 결정3 계승) / 기각 = MinIO/S3(POC 과함) / 사유 = POC 단순.
  - **결정 5 — 신규 영속 엔티티**: 택함 = content_db에 **Script**(sections·citations JSON) + **Content**(mp4 경로·메타) 추가, `GenerationJob.script_id·content_id` 채움 / 기각 = 잡에 전부 인라인 / 사유 = 스크립트·완성본은 재사용·조회 대상.

## 3. UI/UX

해당 없음 (API 전용 BE). 산출물은 mp4 파일(로컬).

## 4. Logic

```
POST /content/generate {topic, ticker}
  → GenerationJob(pending) 커밋 → content.generate 발행 → 202 {job_id}

[content.consumer: on content.generate]
  status=scripting
  → agent POST /agent/script {job_id, topic, ticker}   (east-west HTTP + HMAC)
       agent: Retriever.search → GET /research/search?q=topic&entity=ticker
                → facts(Article, 출처) + price(PriceEvidence: close·change_pct·series)
              build_script(topic, price, facts, llm)  (수치=사실 슬롯만, 연결문장=Ollama)
              → ScriptResponse{sections, citations, chart}
  → Script 저장(content_db), job.script_id 세팅
  status=assembling
  → media.assemble 발행 {job_id, chart, title, subtitle, duration}

[video-assembly.worker: on media.assemble]
  render_chart(ChartOverlay from chart) → chart.png           (정확 수치·차트)
  render_title_card(title) → bg.png                           (키 없는 배경, 로컬)
  build_short(bg.png, chart.png, out.mp4, subtitle=subtitle, audio=None)  (무음)
  → mp4 로컬 볼륨 저장
  → content.assembled 발행 {job_id, ok, mp4_path}

[content.consumer: on content.assembled]
  ok=True  → Content(mp4_path) 저장, job.content_id 세팅, status=ready  (내부 상태)
  ok=False → status=failed, error 기록
  (status=ready → content.ready 발행: 사람 승인 대기)

POST /content/{id}/approve  (사람 승인 — ready만)
  → status=approved → content.approved 발행 → publishing (mp4 업로드는 발행 승인 후)
```

- **환각 차단(AC4)**: `build_script`는 이미 수치를 `price` 슬롯에서만 주입(LLM은 연결문장만). citations에 모든 수치 결속. 이 라운드는 배선만 — 이 성질 유지.
- **정확 렌더(AC5)**: `chart.close/change_pct/series`는 research PriceTick에서 온 값 그대로 `render_chart`에 전달(중간 가공 없음).
- **실패 처리**: agent·assemble 실패 시 잡 `failed`+error. consumer는 한 메시지 실패로 죽지 않음(기존 패턴).

## 5. Implementation Split

- **BE(research)**: `/research/search`에 `price` 산출·부착(PriceEvidence). PriceTick 창 조회 + 등락률 계산.
- **BE(agent)**: `Retriever.search` 실 HTTP 구현 + `POST /agent/script`(build_script 래핑, ScriptResponse 반환).
- **BE(content)**: consumer 오케스트레이션(scripting→assemble 트리거→assembled 처리), Script·Content 모델·저장, 상태 전이. main에 tick/assembled 소비 등록.
- **BE(video-assembly)**: worker가 `media.assemble` 소비 → render_chart + 타이틀 카드 + build_short → `content.assembled`. 타이틀 카드 렌더 함수 신설.
- **FE 없음.**

## 6. File Map (기계적)

- `[New] doc/design/content/api-contract-pipeline-keyless.py` — 계약 (작성 완료·mypy 통과)
- `[Mod] services/research/app/domains/research/{service,repository,schemas}.py` — `/search`에 `price`(PriceEvidence) 산출·부착. `[Mod] api-contract.py(research)` SearchResponse에 optional `price`.
- `[Mod] services/agent/app/rag/retriever.py` — `/research/search` 실 HTTP 호출(HMAC), facts+price 파싱
- `[Mod] services/agent/app/main.py` — `POST /agent/script`(Retriever→build_script→ScriptResponse). Retriever 주입.
- `[Mod] services/content/app/consumer.py` — `handle_generate`(scripting→agent 호출→Script 저장→media.assemble) + `handle_assembled`(ready/failed). 두 토픽 소비.
- `[Mod] services/content/app/domains/content/models.py` — `Script`·`Content` 엔티티 추가.
- `[Mod] services/content/app/domains/content/{service,repository,schemas}.py` — Script/Content 저장·상태 전이.
- `[Mod] services/content/app/config.py` — `topic_assemble`·`topic_assembled` 추가.
- `[Mod] services/video-assembly/app/worker.py` — `media.assemble` 소비 → render+compose → `content.assembled`.
- `[Mod] services/video-assembly/app/render.py` — `render_title_card(title, out)` 신설(키 없는 배경).
- `[Mod] services/video-assembly/app/config.py` — bootstrap·토픽·media_dir 정합.
- `[Mod] docker-compose.yml` — 미디어 공유 볼륨(content·video-assembly), 토픽 env. (검증은 로컬 프로세스로도 가능)

## 7. Verification

- 계약: `python -m mypy --strict --ignore-missing-imports doc/design/content/api-contract-pipeline-keyless.py` → Exit 0 (AC1) ✅
- 구현 후(`/builder` — 전부 실서비스·로컬):
  - `build_script` 단위: LLM이 거짓 숫자를 내도 `data_slots`/citations는 사실만(AC4 회귀).
  - **실 파이프라인 관통**: 실 research_db(005930 PriceTick·Article) → agent `/agent/script`(실 Ollama) → media.assemble → video-assembly(실 ffmpeg) → mp4. 상태 전이 관찰(AC2), ffprobe로 h264 1080×1920(AC3).
  - 차트 오버레이 수치 == PriceTick 종가·등락률(AC5). agent에서 DB 접속 코드 grep 0.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | 최초 설계 — 근거 기반 쇼츠 end-to-end 키 없는 배선(하이브리드 오케스트레이션·가격근거 `/search` 확장·로컬 배경/무음). 부품 재사용, 배선만. |
| 20260721 | /builder | 4서비스 배선: research `/search`에 `price`(PriceEvidence) · agent `Retriever.gather`(실 HTTP+HMAC)+`POST /agent/script` · content consumer 오케스트레이션(`handle_generate`→agent→`media.assemble`, `handle_assembled`→Content·ready)+Script/Content 모델 · video-assembly worker(`media.assemble`→render+`render_title_card`(로컬배경)+build_short→`content.assembled`). **전 스택 실서비스 e2e 관통**: generate→scripting(실 agent→실 Ollama qwen3:14b, 근거 인용)→`media.assemble`→실 ffmpeg→`content.assembled`→ready. **AC 전부 충족**: 상태전이(AC2), mp4 h264 1080×1920 6s+aac(AC3), 무출처 인용 0(AC4), 차트 254500·+4.30%=PriceTick 1:1(AC5), 외부 broll/TTS 없이 로컬배경+무음(AC6). mypy·contract-gate clean, 기존 단위(builder 3·render/assemble 3) 회귀 없음. **이탈/후속**: content_db `scripts`/`contents` 테이블은 dev create_all로 생성(Alembic 베이스라인 후속·`price_ticks`와 동일 갭), compose 미디어 공유 볼륨은 발행 라운드 후속(이번 검증은 로컬 프로세스), 가격근거 없으면 `/agent/script` 422(이슈 종목 전제). |
