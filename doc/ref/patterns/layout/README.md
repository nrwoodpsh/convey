# layout — 폴더 구조·계층 분리 규약 (프로젝트 확정)

> 이 프로젝트의 **실제** 폴더 구조와 계층 책임을 적는다. 프리셋을 복사한 뒤 실제에 맞게 조정할 것. AI는 이 문서를 참조해 파일을 어디에 만들지 결정한다.

## 백엔드 (예시 — 실제로 교체)

```
{{루트 패키지}}/{도메인}/
├── controller/   — HTTP 진입, 요청 검증, 응답 매핑 (비즈니스 로직 금지)
├── service/      — 비즈니스 로직, 트랜잭션 경계
├── repository/   — 데이터 접근
└── dto/          — 계약(api-contract)과 대응하는 요청·응답 타입
```

계층 규칙:
- 의존 방향: controller → service → repository (역방향 금지)
- 트랜잭션 경계: service 계층
- 도메인은 인프라를 직접 의존하지 않는다

## 프론트엔드 (예시 — 실제로 교체)

```
src/
├── views/{도메인}/        — 화면 (목록·상세·팝업)
├── components/common/     — 공통 컴포넌트 (여기 것만 사용)
├── api/                   — 계약 타입 import + 호출
└── stores/                — 상태
```

## 새 화면/모듈 만들 때 참조 대상

- 목록: `{{예: src/views/order/OrderList.vue}}`
- 상세: `{{예: src/views/order/OrderDetail.vue}}`
