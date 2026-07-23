# 20260723 — 요약: 확장 Phase D (연출 — 배경 컷 전환)

- **Task**: `doc/design/content/20260723-task-expansion.md` (라운드㉙ · Phase D)
- **작업**: /run(builder→sync) · 날짜 2026-07-23 · 브랜치 main · **로컬 전용**(실 컨테이너 스택)
- **상태**: Phase D 완료·검증. 배경이 구간마다 하드 컷으로 전환. (E 데이터·F 안정은 후속 /run)

## 개요

㉖의 단일 배경(ADR 0013로 대체)을 넘어, 배경을 **여러 Pexels 클립으로 하드 컷 전환**한다. xfade는 `stream_loop`+`trim` 조합에서 ffmpeg -22 오류가 나 **concat 하드 컷**으로 채택(견고). 실패 시 단일 배경 폴백.

## 변경사항

- **content(media.py)**: `broll_queries(ticker, background)` — 대표(산업/애니) + 보조 2개. `build_assemble_event`에 `broll_queries` 추가(단일 `broll_query`도 유지=폴백).
- **video-assembly(broll.py)**: `PexelsClient.fetch_many(queries, out_base, mode, n)` — 최대 n개 클립.
- **video-assembly(assemble.py)**: `build_bg_cuts(clips, out, duration)` — N클립 스트림루프+크롭+균등 트림 후 `concat`(하드 컷) → 배경 1개. 2개 미만/실패 시 None.
- **video-assembly(worker.py)**: `fetch_many`로 복수 클립 → video 2+개면 `build_bg_cuts`로 배경 합성 후 `build_short_video`. 아니면 단일(폴백). 수치 팝은 ㉖ fade 유지.

## API/타입 변경

- media.assemble 이벤트에 `broll_queries`(list) 추가(하위호환 — 없으면 단일). 외부 API 불변. 계약 `api-contract-expansion.py`.

## 검증 (실 컨테이너 스택)

- job#37: 배경 3클립(공장/스카이라인/파란 추상), `bgx.mp4` 28.5s 유효, 프레임 4s=공장 → 26s=파란 추상 배경(전환 확인). 금색 라벨·배지·2줄 자막·수치 등장 유지.
- 폴백: job#36에서 xfade(구버전) 실패 시 단일 bg0로 안전 강등 확인 → 현재 concat은 정상.
- va 단위테스트 3 통과.

## 특이사항 (설계 대비·후속)

- **이탈**: xfade(-22 오류) → concat **하드 컷**(더 견고, "컷 전환" 충족). 수치 **scale 바운스는 후속**(투명 오버레이 알파 이슈, ㉖ fade 등장 유지). 대용량 Pexels 클립(128MB)로 합성 ~84s → broll 파일 크기 상한 튜닝 후속.
- **다음**: Phase E(종목 마스터·수집 확대·DART 사건화·백필) → Phase F(재시도·자동양산 검증·/ui/stats).
- 커밋: 아직(사람 게이트 — `/commit`).