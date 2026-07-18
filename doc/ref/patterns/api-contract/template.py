"""
API 계약 템플릿 (Python / FastAPI · Pydantic 스택 기준)
─────────────────────────────────────────────
이 파일은 "프로젝트 확정층" 정본이다. 실제 도메인에 맞게 이름을 치환해 사용.
계약은 자연어가 아니라 타입으로 작성한다 — 타입체커가 환각·오타를 잡는다.
검증: workflow.config.json의 contract.gate (`python -m mypy --strict --ignore-missing-imports {file}`).

계약이 답해야 할 것 (필드명만 나열하면 서비스 간 다르게 해석 — 빠지기 쉬운 4가지):
  1) 검증 규칙 — 필드별 필수/선택·최대 길이·허용값 (Pydantic Field 제약으로 명시)
  2) 에러 — 권한 없음 403 vs 대상 없음 404 등. code·status·message를 에러 레지스트리에
  3) 페이징·정렬 — page가 0-based? 1-based? 정렬 가능한 필드는?
  4) 이벤트 — 발행/구독 Kafka 토픽명과 페이로드 스키마(MSA는 API만큼 이벤트 계약이 중요)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# 1) 엔드포인트 — method + path를 상수로 고정
EXAMPLE_ENDPOINT = ("GET", "/api/v1/examples")


# 2) 요청 DTO (Pydantic 제약으로 검증 규칙까지 표현)
class ExampleReq(BaseModel):
    page: int = Field(ge=0, description="0-based")
    size: int = Field(ge=1, le=100)
    keyword: str | None = Field(default=None, max_length=200)


# 3) 응답 DTO
class ExampleItem(BaseModel):
    id: int
    name: str
    created_at: datetime  # UTC ISO 8601


class ExampleRes(BaseModel):
    items: list[ExampleItem]
    total: int
    page: int


# 4) 에러 레지스트리 — code + HTTP status + message (libs/common/common/errors.py와 정합)
class ExampleError(tuple[str, int, str], Enum):
    NOT_FOUND = ("EX001", 404, "대상을 찾을 수 없습니다.")
    INVALID_PARAM = ("EX002", 400, "요청 파라미터가 유효하지 않습니다.")


# 5) (선택) 이벤트 계약 — 발행/구독 Kafka 토픽 + 페이로드
EXAMPLE_TOPIC = "sample-events"


class ExampleEvent(BaseModel):
    id: int
    action: str  # created | updated | deleted
    occurred_at: datetime  # UTC
