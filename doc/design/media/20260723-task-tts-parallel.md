# 20260723-task-tts-parallel.md

> 라운드 ㉘ (성능 — 구간 TTS 병렬 합성). ADR 불요(History). video-assembly 국한.
> 계약 변경 없음(내부 성능 리팩터). 결과(오디오·자막 싱크) 불변.

## 1. Requirements

- **결론**: 구간별 TTS(㉕/C)가 **직렬**로 합성돼 승인→ready가 ~2분 걸린다(edge-tts 온라인 5~7회 순차). 각 구간 합성은 서로 독립이므로 **병렬(asyncio.gather)**로 바꿔 합성 시간을 `sum` → `max` 수준으로 줄인다.
- **불변**: 구간 순서·타이밍·자막 싱크·폴백은 그대로. 결과 mp4 동일(속도만).
- **Acceptance Criteria**:
  - [x] AC1: 구간 TTS **병렬 합성**(asyncio.gather). **검증: 승인→ready ~45초(이전 직렬 ~120초 초과), 구간 5개.**
  - [x] AC2: 결과 동일 — concat 인덱스 순 보존(자막 싱크 로직 ㉖/㉗ 검증분 불변). seg mp3 5개.
  - [x] AC3: 폴백 불변 — gather 중 하나라도 None이면 단일 내레이션(계약 동일).
  - [x] AC4: 실 mp4 정상 생성(job#35 ready). va 단위테스트 3 통과.

## 2. 사각지대 & 핵심 결정

- **사각지대**:
  - **edge-tts 동시 호출**: 온라인(MS Edge) 독립 요청 — 동시성 OK. 다만 과도한 동시수는 레이트리밋 위험 → 구간 수(3~7)라 무해. 필요 시 세마포어.
  - **현재 sync 구조**: `EdgeEngine.synthesize`가 `asyncio.run(save)` — worker `to_thread`에서 직렬. 병렬화하려면 **async로 gather** 후 concat(sync)만 스레드.
  - **실패 처리**: gather에서 하나라도 None/예외면 (None,[]) → 단일 폴백(현행과 동일 계약).
  - **결정론**: 오디오 concat 순서는 세그먼트 인덱스 순 유지(병렬 합성해도 순서 보존).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 병렬화 방식**: 택함 = **asyncio.gather로 edge-tts save 동시 실행**(네이티브 async) / 기각 = ThreadPoolExecutor(각 asyncio.run — 스레드 오버헤드)·프로세스풀(과함) / 사유 = edge-tts가 async라 가장 자연스럽고 가벼움.
  - **결정 2 — concat 위치**: 택함 = **합성=async gather, concat/ffprobe=to_thread(sync)** / 기각 = 전부 스레드 / 사유 = I/O 바운드 합성은 async, CPU/subprocess는 스레드.

## 3. UI/UX

- 없음(백엔드 성능). 사용자 체감 = 승인→ready 시간 단축.

## 4. Logic

- **tts.py**: `EdgeEngine`에 `async def synthesize_coro(text, out) -> str|None`(실제 await save) 추가, 기존 sync `synthesize`는 유지. 모듈 헬퍼 `async def synthesize_batch(engine, jobs: list[(text,out)]) -> list[str|None]` — EdgeEngine이면 gather, NullEngine이면 [None]*n.
- **worker.py**: `_segment_audio`를 분리 —
  - `async def _synth_segments(segments, base) -> list[(mp3,kind,text)] | None`: 각 구간 (text,out) 모아 `synthesize_batch` gather. 하나라도 None이면 None 반환(폴백).
  - `def _concat_segments(parts, base) -> (audio, caps)`: 기존 ffprobe·무음·concat(동일).
  - `handle_assemble`: `parts = await _synth_segments(...)`; parts면 `audio, caps = await asyncio.to_thread(_concat_segments, parts, base)`; 아니면 단일 내레이션 폴백(현행).

## 5. Implementation Split (다음 /builder)

- **video-assembly**: `tts.py`(async 배치)·`worker.py`(_synth_segments/_concat_segments 분리·gather). content/agent 무관.

## 6. File Map (기계적)

- `[Mod] services/video-assembly/app/tts.py` — async 배치 합성
- `[Mod] services/video-assembly/app/worker.py` — 구간 합성 병렬화(gather) + concat 분리

## 7. Verification (다음 /builder)

- 동일 잡 생성 → 승인→ready 시간 전후 비교(단축). 로그로 구간 합성이 겹쳐 실행되는지 확인.
- 결과 mp4: 구간 자막 싱크·타이밍 이전과 동일(육안). 폴백(무음 엔진 시) 단일 자막.
- video-assembly 단위테스트 통과.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260723 | /builder | 구현·검증. tts.py: `EdgeEngine.synthesize_coro`(async)·`NullEngine.synthesize_coro`·`synthesize_batch`(gather, 순서 보존). worker.py: `_segment_audio`→`_synth_segments`(async 병렬)+`_concat_segments`(sync, to_thread), handle_assemble 연결. **검증(실 스택)**: job#35 승인→ready **~45초**(이전 ~120초 초과), seg mp3 5, 결과 정상; va 단위테스트 3 통과. 계약·결과 불변. |
| 20260723 | /design | 구간 TTS 병렬화 — edge-tts save를 asyncio.gather로 동시 실행(sum→max), concat은 스레드. 결과·자막 싱크·폴백 불변. 계약 변경 없음. video-assembly 국한. |
