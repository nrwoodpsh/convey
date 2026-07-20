# 20260720 — 요약: 미디어·정확렌더 라운드④ (알파3)

- **Task**: `doc/design/media/task-media-render-20260720.md` (ADR 0003·0006)
- **작업**: /run(builder) · 2026-07-20 · main · **로컬 전용**
- **상태**: 정확 렌더+합성(알파③ 핵심) 실검증. 외부 미디어(image-gen·tts)·오케스트레이션 남음.

## 개요

생성형 영상이 못하는 **"정확한 숫자를 화면에 박기"를 결정론적으로**(알파③). matplotlib로 시세 차트+종가·등락률 오버레이 PNG를 렌더(수치는 입력 그대로), ffmpeg로 9:16 쇼츠 mp4로 합성.

## 변경사항 (BE, 신규 서비스)

- `services/video-assembly/app/render.py` — `render_chart(ChartOverlay)` + `format_price`(수치=입력 그대로)
- `services/video-assembly/app/assemble.py` — `compose`(ffmpeg: 차트+배경·음성 → 9:16 mp4)
- `services/video-assembly/app/worker.py`·`config.py` — 워커 진입·설정
- `services/video-assembly/{pyproject.toml,Dockerfile}` — matplotlib + ffmpeg·fonts-nanum
- `docker-compose.yml` — video-assembly 서비스

## 검증 (실서비스·로컬)

- **결정론 단위 2 pass**: `format_price(71900, 2.34) == ("71,900원","+2.34%")`(수치 불변), 실 PNG 산출(PNG 시그니처·크기)
- mypy --strict clean
- **실 matplotlib+ffmpeg**: 차트 PNG(21KB) → **h264 1080×1920 mp4**(9:16 쇼츠)

## 특이사항 (후속)

- **한글 폰트**: 로컬 기본 폰트(DejaVu)엔 한글 없어 `원`이 tofu — 컨테이너 Dockerfile에 `fonts-nanum` 포함(render.py에서 폰트 지정은 소폭 후속). **숫자(71,900/+2.34%)는 정확 렌더**됨.
- **남음**: `image-gen`·`tts`(외부 API 부패방지 계층 래퍼, 커모디티), content 미디어 fan-out join → `AssembleSpec` 오케스트레이션(전 스택 e2e).
- 생성형 영상은 POC 제외(ADR 0006). 미디어 바이너리는 로컬 볼륨(POC).
