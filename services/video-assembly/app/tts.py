"""TTS — edge-tts(Microsoft Edge 뉴럴, 무료·키없음·한국어). 로컬·서버 공통. 라운드⑪.

보편적으로 쓰이는 무료 TTS. torch 등 무거운 의존성 없음. 크로스플랫폼(Mac·Linux 동일).
온라인(MS Edge 음성 서비스) — TTS는 커모디티(외주 허용), 내레이션 텍스트만 전송(원문 전체 아님).
가드레일: import·네트워크·합성 실패 시 예외 대신 None(무음) — 파이프라인 절대 안 깨짐.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("video-assembly")


class TtsEngine:
    """텍스트 → 오디오 파일 경로(또는 None=무음)."""

    def synthesize(self, text: str, out_path: str) -> str | None:
        raise NotImplementedError

    async def synthesize_coro(self, text: str, out_path: str) -> str | None:
        """async 합성(구간 병렬용, ㉘). 기본은 sync를 그대로(엔진별 오버라이드)."""
        return self.synthesize(text, out_path)


class NullEngine(TtsEngine):
    """엔진 부재 폴백 — 항상 무음(None)."""

    def synthesize(self, text: str, out_path: str) -> str | None:
        return None

    async def synthesize_coro(self, text: str, out_path: str) -> str | None:
        return None


class EdgeEngine(TtsEngine):
    """edge-tts — 한국어 뉴럴 음성(기본 ko-KR-SunHiNeural). mp3 산출(ffmpeg가 aac로 합성)."""

    def __init__(self, voice: str = "ko-KR-SunHiNeural") -> None:
        self._voice = voice

    def synthesize(self, text: str, out_path: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None
        import edge_tts  # 지연 import(미설치·모듈오류 시 make_engine에서 이미 Null 선택)

        mp3 = out_path if out_path.endswith(".mp3") else f"{out_path}.mp3"
        try:
            # 동기 컨텍스트(worker의 to_thread 스레드)에서 async save 실행
            asyncio.run(edge_tts.Communicate(clean, self._voice).save(mp3))
        except Exception as exc:  # noqa: BLE001 — 온라인 실패도 무음 폴백(파이프라인 보호)
            logger.warning("edge-tts 합성 실패 → 무음: %s", exc)
            return None
        return mp3

    async def synthesize_coro(self, text: str, out_path: str) -> str | None:
        """async 합성 — 이벤트 루프에서 직접 await(gather로 구간 병렬, ㉘)."""
        clean = text.strip()
        if not clean:
            return None
        import edge_tts

        mp3 = out_path if out_path.endswith(".mp3") else f"{out_path}.mp3"
        try:
            await edge_tts.Communicate(clean, self._voice).save(mp3)
        except Exception as exc:  # noqa: BLE001 — 온라인 실패도 무음 폴백(파이프라인 보호)
            logger.warning("edge-tts 합성 실패 → 무음: %s", exc)
            return None
        return mp3


async def synthesize_batch(
    engine: TtsEngine, jobs: list[tuple[str, str]]
) -> list[str | None]:
    """구간 병렬 합성(㉘) — 각 (text, out)을 동시에 합성. 순서 보존."""
    return list(await asyncio.gather(*(engine.synthesize_coro(t, o) for t, o in jobs)))


def make_engine(voice: str = "ko-KR-SunHiNeural") -> TtsEngine:
    """edge-tts 사용 가능하면 EdgeEngine, 아니면 NullEngine(무음). 어느 쪽이든 파이프라인 동작."""
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return NullEngine()
    return EdgeEngine(voice)
