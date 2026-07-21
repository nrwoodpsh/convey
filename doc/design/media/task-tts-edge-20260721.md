# task-tts-edge-20260721.md

> 라운드 ⑪ (TTS 엔진 edge-tts 통일 — 로컬·서버 공통 한국어). 라운드⑩ 후속. ADR 0006·0008.
> 계약 변경 없음(엔진 교체). 게이트 = 스파이크(설치·한국어 합성) + mypy.

## 1. Requirements

- **결론**: 라운드⑩ `say`는 macOS 전용. MeloTTS는 이 환경에서 의존성 충돌(torch·numpy 강등→pykrx 깨짐)로 기각. **edge-tts**(Microsoft Edge 뉴럴, 무료·키없음·한국어 우수·가벼움·크로스플랫폼)로 통일 — **로컬·서버 둘 다** 한국어 음성.
- **Scenario**: video-assembly가 `TtsEngine`을 edge-tts로 써서 내레이션→음성(mp3). 로컬(Mac)·컨테이너(Linux) 동일.
- **Objective**: 한 엔진으로 어디서나 한국어 음성. 무료·키 0. 보편적으로 많이 쓰는 것.
- **제약/가드레일**: edge-tts는 **온라인**(MS Edge 음성 서비스). TTS는 **커모디티(외주 허용)**이며 넘기는 건 **내레이션 텍스트만**(원문 전체 반출 아님). 네트워크·서비스 실패 시 **무음 폴백**(파이프라인 불변).
- **Acceptance Criteria**:
  - [ ] AC1: (선행 스파이크) `edge-tts` 설치 + 한국어 텍스트→오디오(길이>0) 성공. 실패 시 정지·보고.
  - [ ] AC2: `EdgeEngine.synthesize`가 한국어 내레이션→오디오, `TtsEngine` 인터페이스 유지
  - [ ] AC3: build_short(audio)로 mp4 비무음(mean_volume > -80dB)
  - [ ] AC4: import·네트워크·합성 실패 시 무음 폴백(mp4 정상 — 회귀 0)
  - [ ] AC5: mypy·va 단위 회귀 없음, video-assembly Dockerfile에 edge-tts 반영

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - edge-tts는 **async API**(`Communicate.save`) — 우리 `synthesize`는 동기(worker가 `to_thread`로 호출). 스레드 안에서 `asyncio.run`으로 감싸야.
  - **온라인 의존** — 오프라인/차단 환경에선 실패 → 반드시 무음 폴백.
  - 출력 mp3 → build_short(ffmpeg)가 aac로 합성(입력 포맷 무관).
  - 음성 이름(ko-KR-SunHiNeural 등) 유효성 — 스파이크로 확인.
  - 숫자("258000") 한국어 읽힘 — 스파이크 확인.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 엔진**: 택함 = **edge-tts(`EdgeEngine`)** / 기각 = MeloTTS(무거움·충돌)·Piper(한국어 공식無)·say(mac전용) / 사유 = 보편·무료·키없음·한국어 우수·가벼움·크로스플랫폼.
  - **결정 2 — async 처리**: 택함 = `synthesize`(동기) 내부에서 **`asyncio.run(Communicate.save)`** (worker의 to_thread 스레드에서 실행) / 기각 = 인터페이스를 async로 / 사유 = 기존 `TtsEngine`·worker 배선 불변.
  - **결정 3 — 폴백**: 택함 = import/네트워크/합성 실패 시 **None(무음)** / 기각 = 예외 / 사유 = 온라인이라 실패 가능성↑, 파이프라인 절대 안 깨짐(라운드⑩ 원칙).
  - **결정 4 — 음성**: 택함 = **ko-KR-SunHiNeural**(기본, 설정 가능) / 기각 = 고정 / 사유 = 화자 교체 여지.

## 3. UI/UX
해당 없음.

## 4. Logic

```
tts.py:
  class EdgeEngine(TtsEngine):
    def __init__(self, voice="ko-KR-SunHiNeural"): ...
    def synthesize(self, text, out):            # 동기
      if not text.strip(): return None
      mp3 = out(.mp3)
      try: asyncio.run(edge_tts.Communicate(text, voice).save(mp3))
      except Exception: return None             # 네트워크·서비스 실패 → 무음
      return mp3
  make_engine(): EdgeEngine() if edge_tts import 가능 else NullEngine()
worker: 변경 없음(make_engine().synthesize 호출 유지)
```

## 5. Implementation Split (다음 /builder)

- **선행**: 스파이크 — `pip install edge-tts` + 한국어 샘플(성공해야 진행).
- **BE(video-assembly)**: `tts.py`에서 SayEngine→`EdgeEngine`(동기 래퍼·폴백), `make_engine` edge 우선·Null 폴백. worker 변경 없음.
- **Dockerfile(video-assembly)**: `edge-tts` 설치(가벼움).
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/video-assembly/app/tts.py` — `EdgeEngine`(say 대체), `make_engine` edge 우선
- `[Mod] services/video-assembly/Dockerfile` — edge-tts 설치
- (참고) worker·build_short·계약 변경 없음

## 7. Verification (다음 /builder)

- 스파이크: edge-tts 한국어 오디오 길이>0, 숫자 읽힘 (AC1)
- `EdgeEngine.synthesize("...258000원...")` → 오디오 (AC2), build_short→mp4 비무음 (AC3)
- import 불가/네트워크 실패 모의 → Null/None 무음 폴백 (AC4)
- mypy·va 단위 회귀 (AC5). Dockerfile 반영.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | TTS 엔진 edge-tts 통일 — 보편·무료·키없음·한국어 우수·크로스플랫폼. MeloTTS(무거움·충돌)·Piper(한국어공식無)·say(mac전용) 기각. async→동기 래퍼, 온라인 실패 시 무음 폴백. 선행 스파이크로 설치·한국어 합성 검증 후 진행. |
| 20260721 | /builder | 스파이크 성공(edge-tts 설치·한국어 mp3 8.6s, torch 불요). `tts.py` SayEngine→**`EdgeEngine`**(동기 래퍼로 async `Communicate.save`, ko-KR-SunHiNeural), `make_engine` edge 우선·Null 폴백. worker 변경 없음(기존 배선). pyproject/Dockerfile에 `edge-tts`. **검증**: EdgeEngine 한국어 오디오(AC2), worker 통합 narration→음성 mp4 **mean_volume -18.3dB 비무음**·길이 음성 맞춤(AC3), NullEngine 무음 폴백(AC4), mypy·va 단위 3 회귀 없음(AC5). 로컬·서버(Linux) 동일 동작(say의 macOS 한계 해소). |
