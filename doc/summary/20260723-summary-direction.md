# 20260723 — 요약: 영상 연출 강화 (단일 배경 + 오버레이)

- **Task**: `doc/design/content/20260723-task-direction.md` (라운드㉖)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: 완료·검증. 정적 1화면 → 인트로 → 수치 팝 → 금색 강조 → 아웃트로. 배경은 1개 유지(안정).

## 개요

품질 라운드(㉕) 위에 **연출**을 얹었다. 배경 컷 전환 리스크를 피하고(단일 배경 유지), 오버레이로 리듬을 준다: 수치 팝(등장) · 금색 강조 · 인트로/아웃트로 카드. video-assembly만 변경.

## 변경사항 (video-assembly)

- **render.py**: `render_chart`를 `render_chart_base`(제목 + 종목 라벨 **금색** + 라인차트, 수치 제외) + `render_numbers`(종가·등락, 투명, 동일 위치)로 분리. `render_intro_card`(제목·종목·CONVEY)·`render_outro_card`(CONVEY·출처)·`_brand_card` 추가. 라벨 색 청록→금색.
- **assemble.py**: `_run` 공용 오버레이 체인 — 배경 → 차트base → 수치(`fade` st=chart_start) → 자막(구간 싱크·금색 플래그) → 신뢰 배지 → 인트로(`enable lt(t,0.8)`)/아웃트로(`gt(t,dur-0.8)`) 전면 카드. `build_short`·`build_short_video`에 `numbers_png`·`pop_start`·`intro_png`·`outro_png` 인자, captions 4-튜플(금색).
- **worker.py**: base/numbers/intro/outro 렌더 호출, `_segment_audio`가 kind 유지 → chart 구간 `pop_start`·chart/relation 자막 금색 플래그. segments 없으면 단일 자막 폴백.

## API/타입 변경

- 외부 API/DB/이벤트 변경 없음(video-assembly 내부 렌더/합성). 계약 `api-contract-direction.py`(내부 형태 문서).

## 검증 (실 컨테이너 스택)

- 현대차 job#31(analysis, real): mp4 31s.
- 프레임: 0.4s 인트로 카드(제목·금색 종목·CONVEY), 4s 수치 미표시→10s "416,500원 +4.39%" 팝 등장 + 자막 금색 "현대차 종가…", 라벨 금색, 배지 우상단, 30.6s 아웃트로(CONVEY·출처 news.einfomax.co.kr · 2026-07-23).
- 회귀: ready. video-assembly 단위테스트 3 통과.

## 특이사항 (설계 대비·후속)

- **이탈**: (1) 수치 scale 바운스·배경 컷 전환은 후속(이번은 fade 등장). (2) 자막/배지 shorten 말줄임(배지 34자·자막 30자) — 긴 텍스트. (3) 차트 자막 "416500.0원" 소수점.
- **후속**: 배경 컷/xfade 전환, 수치 scale 팝, 구간 TTS 병렬화(합성 ~2분), 자막 줄바꿈, 소수점 정리.
- 커밋: 아직(사람 게이트 — `/commit`).