# 20260722 — 요약: broll 배경 — Pexels 무료 스톡 (사진·영상)

- **Task**: `doc/design/media/task-broll-pexels-20260722.md` (라운드⑫). ADR **0009** 신설.
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 Pexels·ffmpeg·content_db)
- **상태**: 배경을 로컬 카드 → Pexels 무료 스톡(사진 B-1·영상 B-2)으로. 6개 AC 충족. 유료 생성형 대체(무료).

## 개요

쇼츠 배경(broll, 커모디티)을 유료 생성형 대신 **Pexels 무료 스톡**으로 조달한다. 종목/섹터 키워드로 세로 사진(켄번즈) 또는 영상 클립을 받아 배경으로 깔고, 그 위에 **투명** 차트·자막·음성을 합성한다. 받은 자산의 출처·라이선스를 기록(가드레일). 실패 시 로컬 카드로 폴백.

## 변경사항 (BE)

**video-assembly**
- `broll.py` (신규) — `PexelsClient`(부패방지): 사진/영상 검색·다운로드 + 메타(source_url·author·license), 실패 None. `fetch(mode)` 폴백(video→photo).
- `render.py` — `render_chart` **투명 RGBA 1080×1920**로 변경, 차트·수치를 하단부 배치(상단 배경 노출), 수치는 반투명 다크 박스(가독성).
- `assemble.py` — `build_short_video`(영상 배경: scale/crop·`-stream_loop` + 투명 차트 오버레이 + 자막 + 오디오).
- `worker.py` — broll 조달 → video/photo/폴백 분기, broll 메타를 `content.assembled`에 회신.
- `config.py` — `pexels_api_key`·`broll_mode`(video|photo|off).

**content**
- `consumer.py` — `handle_generate`가 `broll_query` 전달(_BROLL_QUERY="stock market"), `handle_assembled`가 broll 메타 → `Content` 저장.
- `models.py` — `Content`에 `broll_source_url`·`broll_author`·`broll_license` 컬럼.
- Alembic `7598c32287dd`(contents broll 3컬럼, `aa3ccec70626` 다음, **실 content_db 적용**).

**계약/문서**
- `api-contract-pipeline-keyless.py` — `MediaAssembleEvent.broll_query`, `ContentAssembledEvent` broll 메타.
- `.env.example` — `PEXELS_API_KEY`. **ADR 0009**(broll 유료→무료 Pexels).

## 검증 (실 Pexels·ffmpeg·로컬)

- **AC2**: 사진(Markus Spiske) + 영상(Kampus, 32MB) 다운로드 + 메타(출처·작가).
- **AC3**: `render_chart` **RGBA 투명**(배경 노출), B-1 사진 배경 mp4 h264 1080×1920.
- **AC4**: B-2 영상 배경 mp4 h264 1080×1920.
- **AC5**: 키없음/실패 → None → 로컬 카드 폴백(회귀 0). worker 통합에서 broll 메타(license=Pexels) `content.assembled` 회신.
- **AC1/AC6**: contract-gate·mypy --strict clean, video-assembly 단위 3 회귀 없음.

## 특이사항 (이탈·후속)

- **이탈**: `broll_query`를 Pexels 커버리지상 영문 **"stock market" 고정**(POC) — 한국어 종목명은 스톡 검색 결과가 희박. 섹터→영문 키워드 매핑은 후속.
- **온라인**: Pexels는 스톡 다운로드(오프라인 아님). 커모디티라 허용(ADR 0009), 실패 시 로컬 카드.
- **영상 broll 용량**: 클립이 수십 MB — 미디어 볼륨/정리 정책 후속.
- 커밋: 아직(사람 게이트 — `/commit`).
