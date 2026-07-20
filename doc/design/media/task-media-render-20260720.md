# task-media-render-20260720.md

> 라운드 ④ (정확 렌더, 알파3 + 커모디티). 계약 정본 = `api-contract.py`. 자연어 설계만.
> **커모디티는 얇게, 정확 렌더만 우리 것.**

## 1. Requirements

- **Scenario**: 스크립트가 준비된 잡에서 `content`가 미디어를 fan-out한다. 외부 API가 broll·음성을 만들고, `video-assembly`가 **정확한 차트·수치를 화면에 박아** ffmpeg로 합성한다.
- **Objective**: 생성형 영상이 못하는 **정확한 종가·등락률·차트**를 결정론적으로 렌더·합성한다(알파3). 배경·음성은 외주.
- **Acceptance Criteria**:
  - [ ] AC1: `api-contract.py`가 contract-gate(`mypy --strict`) 통과 — ✅
  - [ ] AC2: `video-assembly`가 `ChartOverlay`의 값을 **research 사실과 1:1 일치**하게 렌더(수치 오차 0)
  - [ ] AC3: 외부 image/tts 호출이 **부패방지 계층** 경유, 원문 전체 반출 없음(프롬프트·에셋만)
  - [ ] AC4: 완성본 mp4 생성 → 잡 status=ready (내부 상태, 이벤트 아님)

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - 미디어 fan-out/join(여러 자산 완료 대기) 방식 미정 — content consumer가 join.
  - ffmpeg 컨테이너·폰트(한글 자막) 준비 필요.
- **핵심 결정**:
  - **결정 1 — 정확 렌더 소유**: 택함 = **화면 위 수치·차트는 우리(matplotlib/ffmpeg drawtext)** / 기각 = 외부 생성형 영상 / 사유 = 알파3(생성형은 숫자 못 박음, ADR 0006)
  - **결정 2 — 생성형 영상**: 택함 = **POC 제외**(배경=스톡/모션) / 기각 = Sora류 도입 / 사유 = 정확성·복잡도(ADR 0006)
  - **결정 3 — 미디어 바이너리 저장**: 택함 = **로컬 볼륨(POC)**, content_db엔 경로·메타만 / 기각 = MinIO/S3 / 사유 = POC 단순. 확장 시 오브젝트 스토리지로 (미결→POC 잠정)

## 4. Logic

1. content: 스크립트 준비 → `image.generate`·`tts.generate` fan-out (asset_key로 추적)
2. `image-gen`/`tts`: 외부 API 부패방지 계층 호출 → 자산 저장(로컬 볼륨) → 완료 신호
3. content: 자산 join 완료 → `AssembleSpec` 구성(사실 overlays 포함) → `video-assembly`
4. `video-assembly`: 배경 + 음성 + **정확 차트·수치 오버레이** + 자막 → ffmpeg → mp4 → status=ready

## 6. File Map (기계적)

- `[New] doc/design/media/api-contract.py` — 계약 (작성 완료·mypy 통과)
- `[New] services/image-gen/`, `services/tts/` — 외부 API 래퍼 워커(부패방지 계층, market-feed 패턴)
- `[New] services/video-assembly/` — ffmpeg 합성 + 정확 렌더(차트·drawtext). ffmpeg 포함 Dockerfile
- `[Mod] services/content/app/consumer.py` — 미디어 fan-out/join → assemble 트리거
- `[Mod] docker-compose.yml` — image-gen·tts·video-assembly 추가, 미디어 볼륨
- `[Mod] .env.example` — 미디어 API 키(이름만)

## 7. Verification

- 계약: `mypy --strict` → Exit 0 (AC1) ✅
- 구현 후(`/builder`): 사실값과 렌더된 오버레이 수치 일치(AC2), 외부 호출 페이로드에 원문 전체 없음(AC3)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260720 | /design | 최초 설계 — 정확 렌더 자체·커모디티 외주, 생성형영상 제외 (알파3) |
