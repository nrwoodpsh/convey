"""타입 계약 — 영상 배경 전략 + 가독성 개선. 라운드㊴. admin(㉝)·image-gen 연계.

검증: python -m mypy --strict --ignore-missing-imports api-contract-video-background.py

배경(§7 실측): job-45 프레임 — ①broll(Pexels)이 종목과 무관(현대차인데 아파트 배경) ②차트·수치가
배경과 겹쳐 가독성↓. 해결: **배경 소스를 운영자가 관리**(등록 라이브러리 + 생성 + Pexels) + 섹터 매칭,
그리고 차트·수치·자막 뒤 **반투명 패널**로 가독성 확보.

가드레일: 미디어 생성은 외부 API 허용(부패방지 계층), 원문 텍스트 전체는 안 넘김. 수치·차트는 여전히
결정론 렌더(알파③). 배경 자산도 생성 소스·라이선스 메타 계승·기록.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

# 배경 모드 — 운영자/템플릿이 선택. auto=우선순위 자동.
BackgroundMode = Literal["auto", "library", "generated", "stock"]


@dataclass
class BackgroundAsset:
    """운영자가 admin에 등록하는 배경 자산(영상/이미지). 섹터·무드 태그로 매칭."""

    id: int
    name: str
    tags: list[str]        # 예: ["자동차", "반도체", "우주", "귀여움"] — 섹터/무드 매칭
    path: str              # 공유 볼륨 경로(업로드본)
    kind: Literal["video", "image"]
    license: str           # 출처·라이선스(가드레일)
    enabled: bool = True


# ── 배경 선택 전략 (video-assembly) ──
# auto 우선순위: ①admin 라이브러리에서 섹터/태그 매칭  ②생성(image-gen)  ③Pexels(stock)  ④로컬 카드
class SelectBackground(Protocol):
    """job의 종목/섹터·모드로 배경 1개 결정. 실패 시 다음 우선순위로 폴백."""

    def __call__(
        self, ticker: str, sector: str, mode: BackgroundMode = "auto"
    ) -> BackgroundAsset | None: ...


# ── 생성 배경 (image-gen 래퍼, 옵션) ──
class GenerateBackground(Protocol):
    """프롬프트(섹터·무드)로 귀여운 이미지 배경 생성 — 외부 API(부패방지 계층). 원문 텍스트 미전달.

    반환 이미지는 켄번즈로 배경화. 생성 소스·라이선스 메타 기록. 키 없으면 skip(폴백).
    """

    def __call__(self, prompt: str, out_path: str) -> BackgroundAsset | None: ...


# ── 가독성 패널 (assemble.py ffmpeg) ──
@dataclass
class ReadabilityPanel:
    """차트·수치·자막 뒤 반투명 패널 — 배경과 분리해 가독성 확보."""

    opacity: float = 0.45   # 0~1 (어두운 패널)
    radius: int = 16        # 모서리
    pad: int = 24           # 여백


NOTE = (
    "배경 소스: admin 라이브러리(등록) → 생성(image-gen) → Pexels → 로컬카드. 섹터 매칭(broll 무관 해소). "
    "가독성 패널로 차트·수치·자막 배경 분리. 수치·차트는 결정론 렌더 불변(알파③). 자산 라이선스 메타 계승."
)
