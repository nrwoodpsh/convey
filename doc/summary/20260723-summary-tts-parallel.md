# 20260723 — 요약: 구간 TTS 병렬 합성 (성능)

- **Task**: `doc/design/media/20260723-task-tts-parallel.md` (라운드㉘)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료·검증. 구간 TTS를 직렬→병렬로. 승인→ready ~120초 초과 → ~45초. 결과 불변.

## 개요

구간별 TTS(㉕/C)가 edge-tts 온라인 호출을 **직렬**로 돌아 승인→ready가 ~2분 걸렸다. 각 구간 합성은 독립이므로 `asyncio.gather`로 **병렬화** — 합성 wall-time을 sum→max 수준으로. 결과 오디오·자막 싱크·폴백은 불변.

## 변경사항 (video-assembly)

- **tts.py**: `TtsEngine.synthesize_coro`(async 기본)·`NullEngine`/`EdgeEngine` 오버라이드(EdgeEngine은 `await Communicate.save`). 모듈 `synthesize_batch(engine, jobs)` — `asyncio.gather`로 동시 합성, 순서 보존.
- **worker.py**: `_segment_audio`를 분리 — `_synth_segments`(async, 병렬 합성 후 [(mp3,kind,text)], 하나라도 None이면 None) + `_concat_segments`(sync, ffprobe·무음·concat·타이밍, to_thread). `handle_assemble`가 둘을 연결(실패 시 단일 내레이션 폴백).

## API/타입 변경

- 없음(내부 성능 리팩터). media.assemble 이벤트·결과 mp4 형태 불변.

## 검증 (실 컨테이너 스택)

- job#35(analysis): 승인→ready **~45초**(이전 직렬 ~120초 초과), 구간 mp3 5개(병렬), mp4 정상.
- 결과 구조·자막 싱크 로직 불변(concat 인덱스 순 보존 — ㉖/㉗ 육안 검증분 유지).
- video-assembly 단위테스트 3 통과.

## 특이사항 (설계 대비·후속)

- edge-tts 동시 호출은 구간 수(3~7)라 무해. 대량 시 세마포어(후속).
- 남은 후속: 배경 컷/xfade 전환·수치 scale 팝(연출 심화), 종목 마스터 확대, 과거 기사 LLM 관계 백필, 배포(8091 비노출·C 인증).
- 커밋: 아직(사람 게이트 — `/commit`).