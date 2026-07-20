# ref/domains — 도메인 경계·맵 (입력 정본, 상시 참조 인덱스)

이 프로젝트에 **어떤 도메인이 있고, 각자 무엇을 책임지며, 서로 어떻게 얽히는지**를 담는다. `/design`이 신규 작업을 시작할 때 **가장 먼저 참조**해 (1) 기존 도메인 재사용, (2) 중복 도메인 생성 방지에 쓴다.

> `ref/domains/`(경계·정의, 사람이 관리) ≠ `design/{domain}/`(그 도메인의 task별 설계 산출물, AI가 생성). 혼동 주의.

## 인덱스 (파이프라인 순)

| 도메인 | 파이프라인 | 책임 |
|:---|:---|:---|
| [01. research](01.research.md) | 축적 | 시세·뉴스 → 관계·인과 지식 그래프 + 사실 (**알파1의 심장**) |
| [02. content](02.content.md) | 제작 | 근거 스크립트 → 미디어 → 쇼츠 완성본 · 승인 |
| [03. publishing](03.publishing.md) | 발행 | YouTube Shorts 업로드 (**사람 승인 후**) |

> `issue-detector`·`image-gen`·`tts`·`video-assembly`는 도메인이 아니라 **컴포넌트**(`architecture/04` 참조).

## 작성 방식

도메인당 1파일: `domains/{NN}.{domain}.md` (번호 = 파이프라인 순서: 01 research → 02 content → 03 publishing, architecture 문서 번호와 정합). 예:

```markdown
# user (회원)

- **책임**: 인증(로그인/토큰), 프로필, 권한
- **주요 엔티티**: User, Role, Token
- **연동**: order(주문자 조회), notification(알림 수신자)
- **경계**: 결제 정보는 다루지 않음 → payment 도메인
```

## 인덱스 원칙

위 인덱스 표가 "무엇이 있는지"를 보여준다. 각 파일은 **짧게** 유지 — 상세 설계는 `design/`에, 상세 스키마는 `db-schema/`에 둔다. 도메인을 추가·삭제하면 인덱스 표도 함께 갱신한다.
