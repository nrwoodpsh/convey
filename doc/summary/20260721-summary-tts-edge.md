# 20260721 — 요약: TTS 엔진 edge-tts 통일 (로컬·서버 공통 한국어)

- **Task**: `doc/design/media/task-tts-edge-20260721.md` (라운드⑪, 라운드⑩ 후속)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용 검증**(실 edge-tts·ffmpeg)
- **상태**: TTS를 edge-tts로 통일. 로컬(Mac)·서버(Linux 컨테이너) 어디서나 한국어 음성. 5개 AC 충족.

## 개요

라운드⑩의 `say`는 macOS 전용이라 서버(Linux)에선 무음이었다. 후보를 재검토해 — MeloTTS는 이 환경에서 의존성 충돌(torch·numpy 강등→pykrx 깨짐)로 기각, Piper는 한국어 공식 음성 없음(+아카이브)으로 기각 — **edge-tts**(Microsoft Edge 뉴럴, 무료·키없음·한국어·가벼움·크로스플랫폼)로 통일했다. 보편적으로 많이 쓰이는 무료 TTS다.

## 변경사항 (BE)

- `services/video-assembly/app/tts.py` — `SayEngine` → **`EdgeEngine`**(동기 `synthesize` 내부에서 `asyncio.run(edge_tts.Communicate(text, "ko-KR-SunHiNeural").save(mp3))`). `make_engine`은 edge-tts 사용 가능 시 EdgeEngine, 아니면 NullEngine(무음). 실패(import·네트워크·합성)는 None(무음 폴백).
- `services/video-assembly/pyproject.toml` — `edge-tts>=6.1` 추가(torch 불요).
- worker·build_short·계약 **변경 없음**(엔진 교체만).

## 검증 (실 edge-tts·ffmpeg·로컬)

- **AC1 스파이크**: `pip install edge-tts`(가벼움) + 한국어 mp3 8.6s 생성(온라인 호출 성공).
- **AC2**: `EdgeEngine.synthesize(한국어)` → mp3.
- **AC3**: worker 통합 narration→음성 mp4 **mean_volume -18.3dB**(비무음), 길이 음성에 맞춤.
- **AC4**: `NullEngine` → None → 무음 폴백(회귀 0).
- **AC5**: mypy --strict clean, video-assembly 단위 3 회귀 없음. pyproject·Dockerfile(`pip install .`) 반영.

## 특이사항 (제약·후속)

- **온라인**: edge-tts는 MS Edge 음성 서비스 호출(오프라인 아님). TTS는 커모디티(외주 허용)이고 **내레이션 텍스트만** 전송(원문 전체 아님) — 가드레일 부합. 네트워크 실패 시 무음 폴백이라 파이프라인 불변.
- **환경 사고**: MeloTTS 시도가 numpy를 1.26으로 강등해 pykrx가 깨졌었음 → numpy>=2.0 재설치로 복구, MeloTTS 미채택. edge-tts는 torch 없어 충돌 없음.
- **say 대체**: 라운드⑩ `say`(macOS 전용)를 완전 대체(로컬·서버 통일). 라운드⑩ 요약은 이력으로 유지.
- **후속**: 화자·속도 옵션, 자막 타이밍 음성 싱크, 완전 오프라인 필요 시 대안 재검토.
- 커밋: 아직(사람 게이트 — `/commit`).
