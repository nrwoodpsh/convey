# 20260722 — 요약: 영상 화면 — 한글·레이아웃·길이 (1·2)

- **Task**: `doc/design/media/task-video-layout-20260722.md` (라운드㉑)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 영상 화면의 한글 깨짐·짧음·작은 차트 해소. 실 mp4 육안 검증. (웹 대시보드 3은 다음 라운드)

## 개요

생성 영상의 결함 3종을 고쳤다: (1) **한글 깨짐** → 번들 NanumGothic를 matplotlib·ffmpeg drawtext 공용으로, (2) **너무 짧음** → 목표 ~30s(clamp 24~55) + 내레이션 280자, (3) **차트·수치 작음/레이아웃 없음** → 존 레이아웃(제목·큰 차트·대형 수치·자막). CONVEY의 유일한 "화면" = 쇼츠 영상.

## 변경사항 (BE, video-assembly + content)

- `services/video-assembly/app/assets/NanumGothic.ttf` (신규, OFL 4.5M) — 로컬·컨테이너 공용 한글 폰트.
- `render.py` — 폰트 등록(`font_manager.addfont`+`rcParams`) + **레이아웃 재설계**: 상단 제목(52pt)·중앙 큰 라인차트(lw6, 42~76%)·대형 종가(76pt)·등락(46pt), 투명 오버레이·반투명 패널.
- `assemble.py` — drawtext `fontfile=<번들>`(자막 한글, 48pt), build_short·build_short_video 둘 다.
- `worker.py`·`config.py` — duration `clamp(min_duration 24, max_duration 55)`.
- `content/config.py` — `narration_max_chars` 180→280(≈30s 분량).

## 검증 (실 컨테이너 스택)

- render_chart 한글 PNG **glyph-missing 경고 0**(UserWarning→error에도 통과).
- 실 생성 `out/convey-005380-job18.mp4`: h264 **1080×1920 · 43.3s** · aac.
- **미리보기 프레임 육안**: "005380 / 416,500원 / +4.39%"·한글 자막 정상(tofu 없음), 상단 제목·중앙 차트·대형 수치·하단 자막 레이아웃, Pexels 영상 배경.
- 스크립트 7섹션·10인용(근거). mypy --strict clean.

## 특이사항 (후속)

- **웹 대시보드(3)**: 사용자 요청(생성 버튼·결과 제목 확인·이전 목록) — **다음 라운드 `/design`**(BE-only→FE 도입 = ADR, 새 API: 잡 목록·mp4 서빙).
- 제목이 티커 코드(005380) — 종목명(현대차) 매핑 후속. 목표 30s 대비 현재 43s(narration_max_chars/max_duration로 튜닝 가능).
- 커밋: 아직(사람 게이트 — `/commit`). `out/`(mp4·프레임)은 gitignore.
