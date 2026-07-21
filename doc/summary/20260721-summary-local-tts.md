# 20260721 — 요약: 로컬 TTS (무음 → 음성)

- **Task**: `doc/design/media/task-local-tts-20260721.md` (라운드⑩, 알파3 완성도)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 say·ffmpeg)
- **상태**: 쇼츠에 음성 트랙 추가(무료·키 0). macOS `say`로 스크립트 내레이션. 5개 AC 충족.

## 개요

무음이던 쇼츠에 음성을 넣었다. content가 스크립트를 내레이션 문장으로 조립(chart 슬롯 해소)하고, video-assembly가 **로컬 `say`**로 음성을 만들어 mp4에 싣는다. 외부 API·비용 0. 엔진 없으면(컨테이너 Linux) 무음으로 폴백 — 파이프라인 불변.

## 변경사항 (BE)

- `services/video-assembly/app/tts.py` (신규) — `TtsEngine`(추상) · `SayEngine`(macOS `say -v Yuna`, aiff) · `NullEngine`(무음) · `make_engine`(say 있으면 Say, 없으면 Null). 실패도 None(파이프라인 보호).
- `services/video-assembly/app/worker.py` — `handle_assemble`가 TTS 호출 → 음성 있으면 `duration`을 음성 길이(ffprobe)로 → `build_short(audio_path=…)`. `_audio_duration` 헬퍼.
- `services/content/app/consumer.py` — `_narration`(섹션 조립, chart 슬롯 `{close}` 등 사실값 해소) → `media.assemble`에 `narration` 추가.
- `doc/design/content/api-contract-pipeline-keyless.py` — `MediaAssembleEvent.narration` 추가.

## API/계약 변경

- `MediaAssembleEvent.narration: str = ""` 추가(비면 무음). contract-gate 통과.

## 검증 (실 say·ffmpeg·로컬)

- **AC2**: `SayEngine.synthesize` → aiff 13.53s.
- **AC3**: build_short(audio) → voiced.mp4 **mean_volume -17.4dB**(무음 anullsrc ~-91dB 대비 명백히 음성), 영상 길이 음성에 맞춤.
- **AC4**: `NullEngine` → None → 무음 mp4 정상 생성(폴백·회귀 0).
- **AC5**: `worker.handle_assemble`(narration 포함 이벤트) → 음성 mp4 → `content.assembled(ok)`. `content._narration` 슬롯 해소·전체 섹션 포함.
- mypy --strict clean, contract-gate clean, video-assembly 단위 3 회귀 없음.

## 특이사항 (한계·후속)

- **한계**: `say`는 **macOS 전용**. video-assembly **컨테이너(Linux)에선 무음** 폴백 — 이번 음성은 로컬(Mac) 실행 시. **Piper**(크로스플랫폼, 동일 `TtsEngine` 인터페이스로 교체)가 컨테이너 음성 후속.
- 음성 있으면 영상 길이 = 음성 길이(내레이션 잘림 방지) → 쇼츠가 6s보다 길어질 수 있음(내레이션량 의존).
- **후속**: Piper 엔진, 음성 속도·보이스 설정, 자막 타이밍을 음성에 싱크.
- 커밋: 아직(사람 게이트 — `/commit`).
