# task-ops-scripts-20260722.md

> 라운드 ⑳ (운영 스크립트 + 실기동 생성). 인프라·배포. ADR 0006·0008.
> Jenkins 배포 엔트리포인트 + 실 컨테이너에서 쇼츠 1건 산출.

## 1. Requirements

- **결론**: 실제 컨테이너로 스택을 **한 방에 기동·정지·재기동**(Jenkins), DB/Kafka 접속법 문서화, 그리고 **실 스택에서 쇼츠 mp4를 뽑아** 사람이 YouTube에 수동 업로드.
- **Acceptance Criteria**:
  - [ ] AC1: `up.sh`/`down.sh`/`restart.sh`/`status.sh`/`generate.sh` 제공, Jenkins 친화(실패 시 non-zero)
  - [ ] AC2: `up.sh` → 전 서비스 기동 + 게이트웨이 헬스 OK, `status.sh`가 도메인별 헬스 표시
  - [ ] AC3: DB(PG·Neo4j)·Kafka 접속 정보·조회법 문서화(`doc/ref/operations.md`)
  - [ ] AC4: `generate.sh` → 실 컨테이너 스택에서 쇼츠 mp4 생성·추출(out/)
  - [ ] AC5: 발행은 사람(가드레일) — 자동은 mp4까지

## 2. 핵심 결정
- **Ollama 컨테이너 프로필 격리**: 네이티브 재사용(11434 충돌 방지). `docker compose`가 기본 미기동, llm-inference의 ollama 의존 제거.
- **생성 트리거**: gateway 인증(Supabase 보류) 우회 위해 `issue.selected` 발행 → content 자동 양산(A1). mp4는 media 볼륨 → `docker compose cp`로 out/ 추출.
- **정지 = down(볼륨 보존)**: 데이터(pgdata·neo4jdata·media)는 유지, 컨테이너만 제거.

## 3. Logic — `doc/ref/operations.md` 참조(스크립트·접속·생성 절차).

## 4. File Map
- `[New] scripts/{up,down,restart,status,generate}.sh` + `scripts/trigger_generate.py`
- `[Mod] docker-compose.yml` — ollama 프로필 격리, llm-inference ollama 의존 제거
- `[Mod] services/research/app/consumer.py` — handle_ingested 동기 LLM·Neo4j를 to_thread(이벤트 루프 블로킹 해소)
- `[New] doc/ref/operations.md` — 운영 가이드

## 5. Verification (실 docker)
- `up.sh` → 14 서비스 running, gateway 헬스 OK, status.sh 8개 HTTP 서비스 `{"status":"ok"}`
- `generate.sh 035420` → job ready → `out/convey-035420-job16.mp4`(h264 1080×1920, 음성 -17.8dB, Pexels 영상 배경, 6 인용)

## 6. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /builder | 운영 스크립트 5종 + trigger 헬퍼. compose ollama 프로필 격리·llm-inference 의존 제거. **버그 발견·수정**: research `handle_ingested`의 동기 LLM 관계추출+Neo4j upsert가 이벤트 루프를 막아(news-feed 실수집 중) HTTP `/search`가 굶어 스크립트 타임아웃 → `asyncio.to_thread`로 오프로드. **실 컨테이너 스택 전체 기동 + 쇼츠 mp4 산출**(035420, 음성·Pexels 영상배경·근거 인용 6). `doc/ref/operations.md`. 발행은 사람 수동. |
