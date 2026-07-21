# task-compose-alignment-20260721.md

> 라운드 ⑨ (compose 정합 — 배포 재현성). 인프라 크로스커팅. ADR 0006·0008.
> 계약 파일 없음(API 아님). 게이트 = `docker compose config` 유효성.

## 1. Requirements

- **결론**: 지금까지 검증은 전부 **로컬 프로세스**(PYTHONPATH)로 했다. `docker compose up`으로 **컨테이너 스택이 한 번에 뜨는지**는 안 굳혔다. 두 갭을 메운다: ① video-assembly가 만든 mp4를 다른 서비스가 볼 **미디어 공유 볼륨**, ② 서비스 기동 시 **테이블 자동 생성**(마이그레이션). 그리고 실제 기동으로 확인.
- **Scenario**: `docker compose up`만 하면 인프라(PG·Neo4j·Kafka·Ollama) + DB 마이그레이션 + 앱이 순서대로 뜨고, video-assembly의 mp4가 공유 볼륨에 남아 publishing이 읽을 수 있다.
- **Objective**: "구현 끝"과 "돌아가는 시스템"의 간극 해소 — 재현 가능한 배포.
- **Acceptance Criteria**:
  - [ ] AC1: `docker compose config`가 유효(볼륨·env·depends_on 참조 정상)
  - [ ] AC2: named volume `media`가 **video-assembly(쓰기)·content·publishing(읽기)**에 마운트, `MEDIA_DIR` 일관(`/data/media`)
  - [ ] AC3: research·content·publishing 컨테이너가 **기동 시 `alembic upgrade head` 자동 실행** → 빈 DB에서도 테이블 생성 후 앱 기동
  - [ ] AC4: 실제 기동 검증 — 인프라 + 마이그레이션 대상 서비스가 뜨고, 해당 DB에 테이블·`alembic_version`(head) 확인

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대(부딪히면 배울 함정)**:
  - **이미지 빌드 비용/실패**: 앱 이미지 ~10개. 전체 빌드는 수 분 + 네트워크. Dockerfile이 최신 의존성(pykrx·alembic·google-auth-oauthlib 등)을 반영하는지 미확인.
  - **Ollama 컨테이너**: compose의 `ollama` 서비스는 모델(qwen3:14b ~9GB)이 없어 스크립트 생성이 실패할 수 있음. 네이티브 재사용(`host.docker.internal`)이 현실적 — 전체 in-container generate는 스트레치.
  - **마이그레이션 경쟁**: 한 DB에 여러 서비스가 upgrade하면 충돌. 다행히 DB↔서비스 1:1(research_db·content_db·publishing_db)이라 분리됨.
  - **기존 dev DB**: 이미 테이블 있음 → `upgrade head`는 멱등(스탬프 최신이라 no-op). 빈 DB에서만 실제 생성.
  - **KIS 잔재**: compose엔 KIS env 없음(이미 정리). market-feed는 pykrx.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 마이그레이션 실행 위치**: 택함 = **각 DB 앱 이미지 entrypoint에서 `alembic upgrade head && <앱 실행>`** / 기각 = 별도 one-shot `migrate` 서비스 3개(compose 복잡·이미지 중복)·수동 실행(자동 아님) / 사유 = 서비스 수 안 늘림, 자기 이미지의 자기 alembic 사용, DB별 분리라 경쟁 없음.
  - **결정 2 — 미디어 저장**: 택함 = **named volume `media`**(va 쓰기, content·publishing 읽기), `MEDIA_DIR=/data/media` / 기각 = bind mount(호스트 경로 종속)·MinIO(POC 과함) / 사유 = 컨테이너 간 공유 최소 구성(ADR 0006 로컬 볼륨).
  - **결정 3 — Ollama 접속**: 택함 = **네이티브 재사용**(`OLLAMA_HOST=http://host.docker.internal:11434`, compose `ollama` 컨테이너 미기동) / 기각 = 컨테이너 ollama + 모델 pull(9GB) / 사유 = 이미 네이티브 qwen3:14b 보유(메모리). `.env`로 전환.
  - **결정 4 — 검증 범위**: 택함 = **config + 빌드 + 인프라·마이그레이션 기동 확인**(AC1~4). 전체 앱 up + in-container generate e2e는 **스트레치**(로컬 프로세스 e2e로 이미 파이프라인 검증됨) / 기각 = 필수 전체 e2e / 사유 = compose 정합의 핵심은 빌드·기동·마이그레이션 자동화. 시간·ollama 비용 큰 전체 e2e는 후속.

## 3. UI/UX
해당 없음 (인프라).

## 4. Logic

**미디어 볼륨**
```yaml
volumes: { media: }              # 최상위
video-assembly: { volumes: [media:/data/media], environment: {MEDIA_DIR: /data/media} }
content:        { volumes: [media:/data/media] }   # 경로 기록·후속 읽기
publishing:     { volumes: [media:/data/media] }   # 업로드 시 읽기(후속)
```

**마이그레이션 자동 (entrypoint)**
```
services/<research|content|publishing>/ 에 docker-entrypoint.sh:
  alembic upgrade head        # 자기 DB (멱등)
  exec <원래 CMD: uvicorn ... 또는 python -m app...>
Dockerfile: ENTRYPOINT ["/app/docker-entrypoint.sh"]  (또는 CMD 래핑)
```
- research·content·publishing만 DB 사용 → 이 셋만 entrypoint 마이그레이션.
- news-feed·issue-detector·video-assembly·market-feed·agent·llm-inference·gateway는 DB 없음 → 변경 없음.

**Ollama**
- `.env` `OLLAMA_HOST=http://host.docker.internal:11434`(컨테이너에서 네이티브 접속). compose `ollama` 서비스는 선택 기동(기본 미기동 권장 주석).

## 5. Implementation Split (다음 /builder)

- **[Mod] docker-compose.yml**: `media` 볼륨 + va/content/publishing 마운트, va `MEDIA_DIR`.
- **[New] services/{research,content,publishing}/docker-entrypoint.sh**: `alembic upgrade head` 후 앱 실행.
- **[Mod] services/{research,content,publishing}/Dockerfile**: entrypoint 반영, alembic 포함 확인.
- **[Mod] .env / .env.example**: `OLLAMA_HOST` 네이티브 주석 안내.
- **검증**: `docker compose config`, `docker compose build <대상>`, `docker compose up -d postgres research`(등) → 로그에 `upgrade head`·앱 기동, DB에 테이블·버전 확인.

## 6. File Map (기계적) — 위 5와 동일

## 7. Verification (다음 /builder)

- `docker compose config -q` → 오류 0 (AC1)
- `docker compose config`에 media 마운트·MEDIA_DIR 확인 (AC2)
- 빈 임시 DB 대상으로 entrypoint 스크립트가 `upgrade head` 후 기동(또는 research 컨테이너 up 로그) (AC3)
- 인프라+research up → research_db 테이블·`alembic_version` head, 컨테이너 healthy (AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | compose 정합 설계 — 미디어 공유 볼륨 + entrypoint 마이그레이션(각 DB 앱) + Ollama 네이티브 접속. 검증은 config·빌드·기동(전체 in-container e2e는 스트레치). |
| 20260721 | /builder | **compose 정합**: `media` named volume + video-assembly(쓰기·`MEDIA_DIR=/data/media`)·content·publishing(읽기) 마운트. `.env` `OLLAMA_HOST`→`host.docker.internal`(네이티브 qwen3:14b 재사용). **이탈**: 별도 `docker-entrypoint.sh` 대신 **기존 인라인 CMD 패턴**(`alembic upgrade head && uvicorn`) 사용 — research·content Dockerfile은 **이미 그 패턴 보유**(자동 마이그레이션 됨), **publishing만** 누락이라 정합(alembic 복사 + CMD). 검증: `docker compose config -q` OK(AC1), media 마운트·MEDIA_DIR·키 주입 확인(AC2), publishing 이미지 빌드 성공, **빈 임시 DB에 컨테이너 entrypoint `upgrade head` 실행→`publish_records`+`alembic_version`(head) 생성**(AC3·AC4, dev DB 불변). 전체 앱 up + in-container generate는 스트레치(미실행 — 파이프라인은 로컬 e2e로 검증됨). |
