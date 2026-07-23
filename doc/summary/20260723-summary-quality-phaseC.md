# 20260723 — 요약: 품질 향상 Phase C (연출)

- **Task**: `doc/design/content/20260723-task-quality.md` (라운드㉕ · Phase C, 마지막)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: Phase C 완료·검증. 정적 1화면 → **구간 자막 싱크 + 신뢰 배지**. 품질 라운드㉕(A·B·C) 전부 완료.

## 개요

Phase A(데이터)·B(문장) 위에 **연출**을 얹었다. 구간별 TTS로 음성을 나눠 만들고, 자막을 그 타이밍에 싱크시켜 화면이 리듬을 갖는다. "정확 데이터" 알파를 시청자가 체감하도록 **출처·날짜 신뢰 배지**를 표시. ADR 0012.

## 변경사항

- **content** (`domains/content/media.py`, 호출부):
  - `select_segments` — 훅→수치→인과→사실→거시 순 구간 {kind,text}(chart 슬롯 해소). `build_narration`도 이 소스 사용.
  - `build_trust` — 첫 뉴스 출처 호스트+날짜(krx 시세 제외, 무출처면 None).
  - `build_assemble_event`에 `segments`·`trust` 추가. 호출부(consumer auto·service approve)가 citations·date 전달.
- **video-assembly**:
  - `worker._segment_audio` — 구간별 edge-tts → 무음(0.35s) 연결 오디오 + 구간 타이밍. 실패 시 (None,[])로 **단일 내레이션 폴백**.
  - `assemble._text_layer` — 구간 자막 `drawtext ... enable='between(t,start,end)'`(시간 싱크) + 신뢰 배지(우상단 상시). `build_short`/`build_short_video`에 `captions`·`badge` 인자.
  - `worker.handle_assemble` — segments 있으면 구간 오디오·자막, 없으면 기존 단일.

## API/타입 변경 (계약 `api-contract-quality.py`)

- `media.assemble` 이벤트에 `segments`([{kind,text}])·`trust`({source_host,published_date}) 추가(하위호환 — 없으면 단일 자막). 외부 엔드포인트 없음.

## 검증 (실 컨테이너 스택 — localhost:8091)

- 현대차 job#30(analysis, real): mp4 31s, 구간 TTS 5개.
- 프레임 육안: 1초 자막 "현대차 노사 갈등 지속, 주가 부담"(훅) → 12초 "현대차는 자동차 관련주"(관계) — **자막 시간 전환**. 배지 "출처 ddaily.co.kr · 2026-07-23"(우상단). 종목·수치·차트 정상.
- 회귀: ready(content 21). video-assembly 단위테스트 3 통과.

## 특이사항 (설계 대비·후속)

- **이탈**: (1) 진짜 배경 컷 전환은 미구현 — 단일 배경 + 싱크 자막으로 리듬 확보(ffmpeg concat/xfade 리스크 회피). (2) 구간 TTS 직렬 5회로 합성 ~2분(병렬화 후속). (3) 계약 `SceneSegment`(caption/narration/emphasize)는 impl에서 `{kind,text}`로 단순화(caption=narration=text).
- **후속(품질 더)**: 배경 컷 전환·수치 팝 애니메이션, 구간 TTS 병렬화, 근사 중복 헤드라인 dedup, 거시 지표명 정리.
- **라운드㉕ 완료**: Phase A(그래프 인과)·B(문장)·C(연출) — 헤드라인 리더 → 근거·맥락·리듬 있는 쇼츠.
- 커밋: 아직(사람 게이트 — `/commit`).