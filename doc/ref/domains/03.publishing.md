# publishing (발행)

- **책임**: 승인된 완성 콘텐츠(쇼츠 mp4·이미지)를 외부 채널로 배포하고 발행 이력·채널 상태를 관리. **1차 채널은 YouTube Shorts**(업로드 API + OAuth). 채널이 여러 개로 늘 수 있어 content에서 분리한 별도 도메인.
- **주요 엔티티(안)**: Channel(발행 채널 정의 — YouTube 등), Publication(발행 이력·플랫폼 ID), PublishRequest(발행 요청·사람 승인)
- **연동**: `content`(승인본 수신), 외부 채널 어댑터(부패방지 계층 — YouTube Data API), (향후) Notion/SNS
- **이벤트(안)**: 구독 `content.approved` / 발행 `content.published`
- **경계**: 콘텐츠 생성·초안·미디어 조립 ✗ → `content`. 리서치 수집 ✗ → `research`.
- **구현 위치(예정)**: `services/publishing/`(sample-domain 복제·개명) + `publishing_db`. 외부 채널은 `app/external_client.py` 부패방지 계층에 가둠(참고: `market-feed`).

> **가드레일: 콘텐츠 자동 발행 금지 — 사람 승인 필수.** `PublishRequest` 승인(`content.approved`) 없이는 YouTube 업로드 금지. OAuth 토큰은 `.env`.
> Notion 발행은 현재 Notion MCP 미승인(도구 정책) — 활성화 후 채널로 추가 가능.
> 엔티티·이벤트 토픽은 설계(`/design`) 시 확정. **후속 라운드**(코어 이후).
