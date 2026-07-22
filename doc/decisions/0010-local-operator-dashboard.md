# ADR 0010 — 로컬 운영 대시보드: content 직접 서빙(gateway 우회·무인증)

- **상태**: 채택 (2026-07-22)
- **맥락**: CONVEY는 API 전용 BE였다(사람이 보는 화면 = 쇼츠 영상뿐, task-video-layout ㉑). 하지만 운영자는 브라우저에서 ① 생성 버튼 클릭 → 제작 시작 ② 결과(제목·미리보기) 확인 ③ 이전 것까지 목록 확인을 원한다. 최초 프론트엔드 도입이다. 그런데 gateway(단일 진입)는 모든 비공개 경로를 Supabase JWT로 검증하는데(ADR 0007), 로컬엔 Supabase 프로젝트도 로그인 UI도 없다. 유튜브 업로드는 사람이 수동으로 한다(자동 발행 = C, 연기).
- **결정**:
  - content 서비스가 **정적 대시보드(index.html) + 운영 API(`/ui/*`) + mp4 스트리밍**을 **새 호스트 포트**(예 8091)에 노출한다.
  - `/ui/*`·`/`는 **gateway·Supabase 인증을 거치지 않는다**(HMAC `gateway_user` 의존성 없음). **로컬 운영 콘솔**이다.
  - 기존 `/content/*`(gateway·HMAC 보호)는 **그대로 둔다** — 서비스 간 east-west·gateway 경유 외부 진입은 불변.
  - 대시보드→생성은 기존 `start_generation`으로 위임(owner_id="dashboard"). 잡 상태머신·환각금지·**발행은 사람 승인** 가드레일 전부 불변.
- **트레이드오프**: "gateway 단일 진입" 원칙에 로컬 예외를 둔다(무인증 포트). → **로컬 바인드 전용**으로 한정하고, 운영 배포 시엔 이 포트를 열지 않거나 gateway+Supabase 뒤로 옮긴다(후속). 원문·자격증명은 노출하지 않음(대시보드는 잡 메타·완성 mp4만).
- **대안(기각)**:
  - gateway 경유(인증 필요) — Supabase 프로젝트·로그인 UI·JWKS 선구축 필요. 로컬 POC엔 과함. (운영 지향이나 지금 아님)
  - 별도 FE 컨테이너(nginx) — 정적 서빙만이면 컨테이너 +1의 이점 적음. content가 직접 서빙이 더 얇음.
- **영향**: content에 `/ui` 라우터(무인증) + 정적 파일 + `list_jobs`·`get_content` 저장소. docker-compose content에 호스트 포트 노출(mp4 공유 볼륨 이미 있음). 계약 `api-contract-dashboard.py`(DashboardGenerateReq·JobListRes). BE-only→FE 도입.
- **관련**: [0007](Supabase 인증 — 이 대시보드는 로컬 예외), [0006](POC 로컬 볼륨 mp4), [0004](알파 — 대시보드는 커모디티·운영 편의). 자동 발행(YouTube)은 별도 후속(C).
