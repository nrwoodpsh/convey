# task-local-tts-20260721.md

> 라운드 ⑩ (로컬 TTS — 무음→음성). 알파3 완성도 · 커모디티(로컬·무료). ADR 0006·0008.
> 계약 정본 = `doc/design/content/api-contract-pipeline-keyless.py`(MediaAssembleEvent.narration 추가).

## 1. Requirements

- **결론**: 지금 쇼츠는 **무음**(anullsrc). 무료·키 없이 완성도를 올린다 — **로컬 TTS**(macOS `say`)로 스크립트를 읽어 음성 트랙을 넣는다. 외부 API·비용 0. 엔진 없으면(컨테이너 Linux 등) **무음 폴백**(파이프라인 불변).
- **Scenario**: content가 스크립트를 **내레이션 문장**으로 조립해 `media.assemble`에 실어 보낸다. video-assembly가 로컬 TTS로 음성(wav)을 만들고, build_short가 그 음성을 mp4에 싣는다. 음성 길이에 맞춰 영상 길이를 잡는다.
- **Objective**: 무음→음성으로 시청 완성도↑. 키·비용 0. 실패해도 무음으로 안전.
- **Acceptance Criteria**:
  - [ ] AC1: 계약(`MediaAssembleEvent.narration`) contract-gate(`mypy --strict`) 통과
  - [ ] AC2: 로컬 TTS 엔진(`say`)이 내레이션 텍스트 → 오디오 파일(길이>0) 생성
  - [ ] AC3: 완성 mp4의 오디오가 **비무음**(ffmpeg `volumedetect` mean_volume > -80dB; 무음 anullsrc는 ~-91dB), 영상 길이가 내레이션에 맞춰짐
  - [ ] AC4: 엔진 미가용/실패 시 **무음 폴백**(mp4 정상 생성 — 회귀 0)
  - [ ] AC5: e2e `generate` → 음성 있는 mp4 `ready`

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - `say`는 **macOS 전용** — video-assembly **컨테이너(Linux)엔 없음**. 폴백 필수(무음).
  - `say`는 aiff 출력 → ffmpeg가 aac로 변환(build_short는 이미 aac). 포맷 변환 경로 확인.
  - 내레이션 길이 > 고정 6s면 `-shortest`로 잘림 → **영상 길이를 음성 길이에 맞춰야** 전체가 들림.
  - 스크립트 `chart`/`macro` 섹션은 슬롯(`{close}`) 포함 — 내레이션은 **슬롯 해소된 읽을 문장**이어야(숫자 그대로 읽힘).
  - TTS 텍스트 이스케이프(따옴표·특수문자)로 `say` 인자 깨짐 방지.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 엔진**: 택함 = **로컬 `say` + 무음 폴백**(엔진 추상화 `TtsEngine`; `say` 없으면 audio=None) / 기각 = 외부 TTS API(유료·키)·Piper(모델 다운로드·설정) / 사유 = 무료·즉시·Mac 검증. Piper는 컨테이너용 후속(같은 인터페이스로 교체).
  - **결정 2 — 내레이션 출처**: 택함 = **content가 스크립트 섹션에서 조립**(슬롯 해소, `hook→chart→fact→macro` 순 자연문) → `MediaAssembleEvent.narration` / 기각 = subtitle(hook)만 읽기 / 사유 = 완성도(내용 전체를 읽어야 의미). 슬롯 숫자는 사실이라 그대로 읽어도 안전(환각 무관).
  - **결정 3 — 영상 길이**: 택함 = **음성 있으면 duration = 음성 길이(ffprobe), 없으면 event.duration** / 기각 = 고정 6s(내레이션 잘림) / 사유 = 전체 내레이션이 들려야.
  - **결정 4 — 폴백 안전**: 택함 = TTS 실패/부재 시 **무음(audio=None)으로 계속** / 기각 = 실패 처리 / 사유 = 음성은 완성도이지 필수 아님. 파이프라인 절대 안 깨짐.
  - **결정 5 — 위치**: 택함 = **video-assembly 내 로컬 처리**(새 서비스 없음) / 기각 = 별도 `tts` 서비스(외부 API 래퍼 — 키 발급 후 라운드) / 사유 = 로컬 엔진은 합성 직전 단계라 video-assembly가 자연.

## 3. UI/UX
해당 없음 (BE). 산출물 mp4에 음성 포함.

## 4. Logic

**content (내레이션 조립)**
```
handle_generate: 스크립트 저장 후
  narration = 섹션들을 읽을 문장으로 (hook 텍스트 + chart 슬롯 해소("삼성전자 종가 258000원 등락률 4.30%")
             + fact 텍스트 + macro 요약). 슬롯은 data_slots로 치환.
  media.assemble {..., subtitle, narration}
```

**video-assembly (TTS + 합성)**
```
handle_assemble:
  audio = TtsEngine.synthesize(narration) → wav/aiff (say -v Yuna narration -o out; ffmpeg→wav) 또는 None
  dur = ffprobe(audio) if audio else event.duration
  build_short(bg, chart, out_mp4, duration=dur, audio_path=audio, subtitle=subtitle)
```
- `TtsEngine`: `say` 있으면 SayEngine, 없으면 NullEngine(None 반환→무음). 텍스트 이스케이프.

## 5. Implementation Split (다음 /builder)

- **BE(content)**: `handle_generate`가 `narration` 조립(슬롯 해소) → `media.assemble`에 추가.
- **BE(video-assembly)**: `tts.py`(TtsEngine: SayEngine + NullEngine, 텍스트→오디오). `worker.handle_assemble`가 TTS→duration→build_short(audio). (build_short는 audio_path 이미 지원)
- **계약**: `MediaAssembleEvent.narration: str = ""` 추가.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] doc/design/content/api-contract-pipeline-keyless.py` — `MediaAssembleEvent.narration`
- `[New] services/video-assembly/app/tts.py` — `TtsEngine`(say/null), `synthesize(text)->path|None`
- `[Mod] services/video-assembly/app/worker.py` — TTS 호출 + duration 산출 + build_short(audio)
- `[Mod] services/content/app/consumer.py` — narration 조립 → media.assemble
- (참고) `services/video-assembly/app/assemble.py` `build_short` — audio_path 이미 지원(변경 최소)

## 7. Verification (다음 /builder)

- 계약: `mypy --strict` → Exit 0 (AC1)
- 구현 후:
  - `TtsEngine('say').synthesize("...")` → 오디오 파일 길이>0 (AC2)
  - build_short(audio=wav) → mp4 `volumedetect` mean_volume > -80dB, duration≈음성 (AC3)
  - `say` 미가용 모의(NullEngine) → audio=None → 무음 mp4 생성(AC4)
  - (전 스택) generate → 음성 mp4 ready (AC5)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260721 | /design | 로컬 TTS 설계 — macOS `say`(+무음 폴백), content 내레이션 조립(슬롯 해소), 음성 길이에 영상 맞춤. 무료·키 0. video-assembly 내 처리(새 서비스 없음). Piper·외부 TTS는 후속. |
| 20260721 | /builder | `tts.py`(TtsEngine: SayEngine `say -v Yuna`·NullEngine 폴백) + worker(TTS→음성길이로 duration→build_short audio) + content `_narration`(섹션 조립·chart 슬롯 해소) + 계약 `MediaAssembleEvent.narration`. **검증(실 say·ffmpeg)**: say 오디오 13.53s(AC2), voiced.mp4 **mean_volume -17.4dB(비무음)**·길이 음성에 맞춤(AC3), NullEngine→무음 mp4(AC4), worker 통합 narration→음성 mp4→content.assembled(AC5)+content._narration 슬롯 해소·전체 섹션. mypy·contract-gate clean, va 단위 3 회귀 없음. **한계**: `say`는 macOS 전용 → 컨테이너(Linux)는 무음 폴백(Piper 후속). |
