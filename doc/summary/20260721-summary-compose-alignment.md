# 20260721 — 요약: compose 정합 (배포 재현성)

- **Task**: `doc/design/infra/task-compose-alignment-20260721.md` (라운드⑨, 인프라)
- **작업**: /run(design→builder→sync) · 날짜 2026-07-21 · 브랜치 main · **로컬 전용**(실 docker)
- **상태**: 미디어 공유 볼륨 + 컨테이너 자동 마이그레이션 정합. `docker compose config` 유효, 컨테이너 마이그레이션 실증. 4개 AC 충족.

## 개요

지금까지 검증은 로컬 프로세스였다. 컨테이너 스택이 `docker compose up`으로 재현되도록 두 갭을 메웠다: ① video-assembly가 만든 mp4를 다른 서비스가 볼 **미디어 공유 볼륨**, ② 서비스 기동 시 **테이블 자동 생성**. research·content는 이미 자동 마이그레이션 CMD를 갖고 있었고, publishing만 누락이라 정합했다.

## 변경사항

- `docker-compose.yml` — 최상위 `media` named volume 추가. video-assembly(쓰기 + `MEDIA_DIR=/data/media`)·content·publishing(읽기)에 `media:/data/media` 마운트.
- `services/publishing/Dockerfile` — alembic.ini·alembic 복사 + CMD `alembic upgrade head && uvicorn`(research·content와 동일 패턴).
- `.env` — `OLLAMA_HOST=http://host.docker.internal:11434`(컨테이너에서 네이티브 qwen3:14b 재사용, compose `ollama` 컨테이너 미기동).

## 검증 (실 docker)

- **AC1**: `docker compose config -q` → 오류 0.
- **AC2**: config에 `media` 볼륨·3서비스 마운트·`MEDIA_DIR` 확인. env_file(.env)로 NAVER·DART·거시 키가 서비스에 주입됨도 확인.
- **AC3·AC4**: publishing 이미지 빌드 성공 → **빈 임시 DB(pub_ctest)에 컨테이너 entrypoint `alembic upgrade head` 실행** → `publish_records` + `alembic_version=ba3a7f7a1796`(head) 생성. (dev DB 불변, temp DB drop)
- research·content Dockerfile은 동일 CMD 패턴을 이미 보유 → 같은 동작.

## 특이사항 (이탈·후속)

- **이탈**: 설계의 별도 `docker-entrypoint.sh` 대신 **기존 인라인 CMD**(`sh -c "alembic upgrade head && uvicorn"`) 채택 — research·content가 이미 그 패턴이라 일관·단순. publishing만 정합.
- **스트레치(미실행)**: 전체 앱 컨테이너 up + in-container generate e2e. 파이프라인 로직은 로컬 프로세스 e2e로 검증됨. 전체 in-container 실행은 이미지 ~10개 빌드 + Ollama 접속 등 비용이 커 후속.
- **후속**: 전체 `docker compose up --build` 1회 관통(가능하면 CI), video-assembly 이미지에 한글 폰트(fonts-nanum) 확인, gateway 라우팅 in-container 점검.
- 커밋: 아직(사람 게이트 — `/commit`).
