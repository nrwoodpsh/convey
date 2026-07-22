# 20260722 — 요약: 전체 컨테이너 기동 검증 + 의존성 버그 수정 (B4)

- **Task**: `doc/design/infra/task-compose-e2e-20260722.md` (라운드⑱, 인프라)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-22 · 브랜치 main · **로컬 전용**(실 docker)
- **상태**: `docker compose`로 전 앱 이미지 빌드·스택 기동·마이그레이션·Kafka 배선 실검증. **검증 중 배포 결함 발견·수정**. AC1~4 충족(AC5 스트레치).

## 개요

지금까지 전부 로컬 프로세스로 검증했다. `docker compose`로 실제 이미지가 빌드되고 스택이 뜨는지 검증하다가, **컨테이너의 깨끗한 의존성 폐쇄**가 로컬 공유 env에 은폐돼 있던 **선언 누락 의존성 2건**을 잡아 수정했다.

## 발견·수정 (버그)

- **research**: `pyproject.toml`에 `neo4j`가 주석 처리(round① 이후 미활성)되고 `httpx`(consumer의 llm-inference 호출)가 누락 → 컨테이너 크래시(`No module named 'neo4j'`).
- **video-assembly**: `httpx`(broll Pexels 호출) 누락 → 크래시(`No module named 'httpx'`).
- **수정**: research에 `neo4j>=5.0`·`httpx>=0.27`, video-assembly에 `httpx>=0.27` 선언 추가.

## 변경사항

- `services/research/pyproject.toml` — `neo4j`·`httpx` 추가.
- `services/video-assembly/pyproject.toml` — `httpx` 추가.

## 검증 (실 docker)

- **AC1**: `docker compose build` — 앱 이미지 11개 전부 빌드 성공(pykrx·edge-tts·alembic·matplotlib·neo4j·httpx 등 정합).
- **AC2**: 수정·재빌드 후 `docker compose up -d` → 앱 서비스 **전부 running**(gateway·research·content·publishing·video-assembly·news-feed·issue-detector·market-feed·agent·llm-inference).
- **AC3**: DB 서비스 엔트리포인트 `alembic upgrade head` 실행 → research_db `bbba385fe7b9`·content_db `7598c32287dd`·publishing_db `ba3a7f7a1796`(head).
- **AC4**: research(research.ingested)·video-assembly(media.assemble)·content(issue.selected)·issue-detector(market.ticks) Kafka 소비 조인, news-feed·market-feed 실 수집(RSS·KRX) 기동.
- **AC5**: in-container generate는 설계상 스트레치 — 미실행(파이프라인 로직은 로컬 프로세스 e2e로 관통 검증됨). 스택 up+배선으로 B4 목표 달성.

## 특이사항 (이탈·후속)

- **B4의 소득**: 검증 라운드가 배포 결함(선언 누락 의존성) 2건을 잡아 수정. 컨테이너 재현성 확보.
- Ollama는 네이티브 재사용(`host.docker.internal`) — compose `ollama` 컨테이너는 llm-inference depends_on로 뜨나 실제 추론은 네이티브 qwen3:14b.
- 검증 후 앱 컨테이너 정리(인프라 pg·neo4j·kafka 유지). 재기동: `docker compose up -d <app 서비스>`(ollama 제외 권장).
- 커밋: 아직(사람 게이트 — `/commit`).
