# ADR 0016 — 운영자 설정 admin 서비스 + admin_db 신설 (종목 마스터 DB 승격)

- **상태**: 채택 (2026-07-24)
- **맥락**: 수집이 코드에 박힌 46종목·5피드에 갇혀 운영자가 못 바꿈. 종목 마스터가 `common.stocks`(코드) 하드코딩이라 대시보드 편집 불가. 목표는 "넓게 수집(경제·주식·사회·정치) + 운영자가 관심(종목·키워드)·소스·기간을 설정"인데, 이 **운영자 설정을 담을 곳**이 없었다. 대시보드는 `content` 서비스지만 설정은 content 도메인 것이 아니고, 여러 워커(news-feed·issue-detector)가 읽어야 한다.
- **결정**:
  - **전용 `admin` 서비스 + `admin_db` 신설** — 운영자 설정(종목 on/off·키워드·소스 토글·기간)과 **종목 마스터**를 소유. 대시보드가 쓰고, 워커가 `GET /admin/config`로 읽는다(**Database per Service** — admin_db 직접접근은 admin만).
  - **종목 마스터를 admin_db로 승격** — `common.stocks`(코드 46) → `admin_db.stock`(코스피200). 운영자가 대시보드에서 편집. **소비처 이관은 Phase로 점진**(news-feed→issue-detector, research 그래프는 후속).
  - **신규 도메인 `admin`** — research/content/publishing과 별개인 크로스커팅(운영자 설정).
  - **코스피200 시드는 네이버 증권 스크래핑 기본(계정 불필요) + pykrx 대안 + 정적 fallback** — pykrx 1.2.8은 `data.krx.co.kr` 로그인(KRX_ID/KRX_PW) 필요(계정 신청, 활성 대기). 반면 finance.naver.com 코스피200은 계정 없이 컨테이너에서 접근·코드추출 확인됨. pluggable(`source=naver|pykrx|static`), 네이버는 비공식(취약)이라 KRX 계정 활성 시 갱신·검증 대안으로.
  - **단계(Phase) 분할** — P1 admin+db+시드 · P2 대시보드 설정 UI · P3 news-feed 광역수집·연동 · P4 issue-detector 연동. 각 독립 커밋.
- **트레이드오프**: 새 서비스·새 DB = 인프라·운영 부담↑. 하지만 관리자 기능이 계속 늘 것이므로 **설정의 단일 홈**이 장기적으로 값이 크다(매번 어디 둘지 고민 제거). 이관 중 종목 마스터 이중 진실 구간 발생 → Phase 순서·fallback으로 통제.
- **대안(기각)**:
  - content_db에 설정 얹기 — content 도메인 오염, 워커가 남 DB 직접접근 유혹.
  - common.stocks 공존(코드 유지) — 대시보드 편집 불가·이중 진실.
  - Kafka 이벤트로 설정 전파 — 조회(질의)엔 과함. 설정은 API 조회가 자연스러움.
- **영향**: 신규 `services/admin/` + `admin_db` + gateway `/admin` + content 대시보드 설정 UI + news-feed·issue-detector 설정 소비. `common.stocks` 점진 이관(research 그래프는 후속). 계약 `api-contract-admin.py`. 자격증명(KRX_ID/KRX_PW)은 `.env`(커밋 금지).
- **관련**: [0010](운영 대시보드), [0008](데이터 소스), [0014](개방형 NER)·[0004](알파 — 이슈 선별). 라운드㉝. 대형이라 Phase별 진행.
