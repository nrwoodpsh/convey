"""로컬 TTS — macOS `say`(무료·오프라인). 없으면 무음 폴백. 라운드⑩.

외부 API·키 없음(커모디티를 로컬로). 컨테이너(Linux)엔 `say`가 없어 NullEngine(무음).
Piper 등 크로스플랫폼 엔진은 동일 인터페이스로 교체 가능(후속).
가드레일: 원문 전체를 외부로 넘기지 않음 — 로컬 프로세스로만 합성.
"""
from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger("video-assembly")


class TtsEngine:
    """텍스트 → 오디오 파일 경로(또는 None=무음). 실패해도 예외 대신 None(파이프라인 보호)."""

    def synthesize(self, text: str, out_path: str) -> str | None:
        raise NotImplementedError


class NullEngine(TtsEngine):
    """엔진 부재 폴백 — 항상 무음(None)."""

    def synthesize(self, text: str, out_path: str) -> str | None:
        return None


class SayEngine(TtsEngine):
    """macOS `say` — 한국어 음성(기본 Yuna). aiff 산출(ffmpeg가 aac로 합성)."""

    def __init__(self, voice: str = "Yuna") -> None:
        self._voice = voice

    def synthesize(self, text: str, out_path: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None
        aiff = out_path if out_path.endswith(".aiff") else f"{out_path}.aiff"
        try:
            subprocess.run(
                ["say", "-v", self._voice, clean, "-o", aiff],
                check=True, capture_output=True,
            )
        except (subprocess.CalledProcessError, OSError) as exc:  # 실패 → 무음 폴백
            logger.warning("say TTS 실패 → 무음: %s", exc)
            return None
        return aiff


def make_engine(voice: str = "Yuna") -> TtsEngine:
    """`say` 있으면 SayEngine, 없으면 NullEngine(무음). 파이프라인은 어느 쪽이든 동작."""
    return SayEngine(voice) if shutil.which("say") else NullEngine()
