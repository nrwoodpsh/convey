# ADR 0011 — 대시보드: 기사 기반 시나리오 승인 워크플로우 + 다크 테마

- **상태**: 채택 (2026-07-22)
- **맥락**: 운영 대시보드(ADR 0010) 초판은 "제목 자유 입력 → 즉시 생성"이었다. 사용자는 (1) **근거(기사) 있는 것만** 만들고, (2) 영상 만들기 **전에 시나리오를 사람이 승인**하고, (3) 오늘자 수집 기사에서 골라 시작하는 흐름을 원한다. 또한 화이트 브랜드(brandlogy 템플릿)는 우리 제품 브랜드가 아니므로 제거하고, 다크(검정+레드+금색)로 바꾼다.
- **결정**:
  - 대시보드 흐름 = **오늘자 수집 기사 목록 → 선택 → 진행(초안) → 시나리오 제시 → 승인 → 쇼츠 생성**. 자유 입력 제거(근거 없는 생성 차단 — 알파1).
  - **잡 상태머신에 승인 게이트**: 수동(대시보드) 잡은 `scripting → scenario_ready(승인 대기) → assembling → ready`. 승인 전엔 영상 합성 안 함. **자동양산(알파4·issue.selected)은 승인 없이 `ready`까지 무정지**(알파4 유지).
  - 기사 회수는 **research 신규 `GET /research/articles`**(도메인 경계 — 수집·기사=research), content가 east-west(HMAC)로 호출. content가 research_db 직접접근 금지.
  - 시나리오/내레이션/자막에서 **종목코드 노출 제외** — agent가 chart 문장을 한글명("현대차 종가 …")으로 생성(공유 `common.stocks`).
  - **테마**: 검정 배경 + 레드 + 금색, `brandlogy` 워드마크·용어 제거(제품명 CONVEY), 영상 미리보기 **상단** 배치.
- **트레이드오프**: 승인 게이트로 수동 제작은 한 단계(사람 개입) 늘지만, 품질·근거 통제 확보. 자동양산은 무정지라 알파4 양산성 유지(발행만 사람 승인 — 불변). research 신규 엔드포인트/east-west 1개 추가.
- **대안(기각)**: 전건 승인(자동양산 약화) / content가 기사 DB 직접 조회(경계 위반) / 표시단 정규식으로 코드 제거(내레이션·자막엔 잔존) / 화이트 브랜드 유지(사용자 거부).
- **영향**: research 기사 목록 API. content `research_client`·`/ui/articles`·`/ui/jobs/{id}/script`·`approve-scenario`·`start_generation(auto)`·`handle_generate` 분기·`JobStatus.SCENARIO_READY`·`GenerationJob.chart`(마이그레이션). agent `builder` chart 문장. FE 전면 재작성(다크·워크플로우), brandlogy 자산 삭제. 계약 `api-contract-dashboard.py` 확장.
- **관련**: [0010](운영 대시보드 — 이 워크플로우의 토대), [0004](알파1 근거·알파4 자동양산), [0007](발행=사람 승인 — 별개 게이트 유지). ㉒의 "자유 입력 즉시 생성"을 대체.
