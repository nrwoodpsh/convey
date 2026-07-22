# task-video-layout-20260722.md

> 라운드 ㉑ (영상 "화면" — 한글 폰트·레이아웃·길이). 알파3(정확 렌더) 완성도. ADR 0006.
> 계약 변경 없음. 자연어 설계만. **사람이 보는 유일한 화면 = 쇼츠 영상**(CONVEY는 API 전용 BE).

## 1. Requirements

- **결론**: 생성 영상을 틀면 (1) **한글이 전부 깨짐**(matplotlib 차트·ffmpeg 자막에 한국어 폰트 미지정 → tofu), (2) **너무 짧음**(내레이션 길이=영상 길이라 ~7~20s), (3) **차트·수치가 작음**(하단 15%에 몰림), (4) **레이아웃 부재**. 영상 화면을 제대로 만든다.
- **목표 화면**: 9:16 쇼츠에 **제목(종목) · 큰 차트 · 큰 수치 · 자막**이 명확한 레이아웃, **한글 정상**, **~30초**(1분 이내).
- **Acceptance Criteria**:
  - [ ] AC1: 차트·자막 **한글 정상 렌더**(matplotlib "missing glyph" 경고 0 + drawtext `fontfile` 지정). **로컬·컨테이너 공통**(번들 폰트).
  - [ ] AC2: 영상 길이 **~30초**(24~55s, 1분 이내) — 내레이션이 짧아도 목표 길이 확보.
  - [ ] AC3: **레이아웃 존**(제목/차트/수치/자막) 적용 + 차트·수치 **크게**(하단 몰림 해소).
  - [ ] AC4: 실 mp4로 한글 정상·길이 ~30s·요소 크기 확인.

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **폰트 이식성**: 컨테이너는 `fonts-nanum`, 로컬(Mac)은 AppleGothic — 경로 다름. drawtext는 `fontfile` 절대경로 필요. matplotlib은 `font.family` 이름 필요. **로컬·컨테이너 동일 동작**하려면 폰트를 **레포에 번들**.
  - 번들 폰트 라이선스: NanumGothic = **OFL**(재배포 가능). 컨테이너 `/usr/share/fonts/truetype/nanum/NanumGothic.ttf`를 레포로 복사.
  - 길이 늘리기: 내레이션만 늘리면 장황. 배경(broll)·차트는 유지하고 **영상 길이 목표(~30s)**를 두되 음성이 짧으면 뒷부분은 배경만.
  - 차트 투명 오버레이(라운드⑫) 위에 큰 요소 재배치 — 배경 가시성과 가독성 균형.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 한글 폰트**: 택함 = **NanumGothic.ttf 레포 번들** → matplotlib `addfont`+`font.family`, drawtext `fontfile=`(동일 파일) / 기각 = OS 폰트 의존(로컬·컨테이너 경로 갈림·자막 tofu) / 사유 = 이식성·재현성. OFL이라 번들 가능.
  - **결정 2 — 길이**: 택함 = **목표 ~30s**: `duration = clamp(narration_audio, min≈24, max≈55)`. 음성 짧으면 배경 지속(무음 tail) / 기각 = 음성 길이=영상(너무 짧음)·하드 60s 고정 / 사유 = 1분 이내·30초 지향.
  - **결정 3 — 레이아웃**: 택함 = **존 템플릿**(상단 제목 / 중앙 큰 라인차트 / 그 아래 큰 종가·등락률 / 하단 자막), 반투명 패널로 가독성 / 기각 = 현행(하단 15% 몰림·작음) / 사유 알파3(정확 수치를 **크고 명확히**).
  - **결정 4 — 내레이션 길이**: 택함 = `narration_max_chars` **상향(~280)**(≈30s 분량) + 길이 목표와 정합 / 기각 = 180 유지(20s) / 사유 = 30초 지향(라운드⑮ 상한은 유지, 값만 상향).

## 3. UI/UX (영상 화면 = 유일한 화면)

```
┌──────────── 1080×1920 (9:16) ────────────┐
│  [상단 20%]  종목명·티커 (큰 제목)          │  ← 반투명 바
│                                           │
│  [중앙 45%]  큰 라인차트(시계열)            │  ← 배경 broll 위, 큰 선
│                                           │
│  [하단중앙 20%] 종가 258,000원  +4.30%     │  ← 아주 큰 수치(색: 등락)
│                                           │
│  [하단 15%]  자막(내레이션 요약)            │  ← drawtext, 한글
└───────────────────────────────────────────┘
배경: Pexels broll(영상/사진) · 음성: edge-tts
```
- 운영 대시보드/웹 UI는 범위 밖(별도 FE). 본 라운드는 **영상 화면**만.

## 4. Logic

- **폰트**: `services/video-assembly/app/assets/NanumGothic.ttf` 번들. render.py 시작 시 `font_manager.addfont(path)` + `rcParams["font.family"]="NanumGothic"`. assemble.py drawtext에 `fontfile=<assets 경로>`.
- **render_chart**(재설계): 투명 1080×1920, 상단 제목 바 + 중앙 큰 라인차트 + 그 아래 대형 종가/등락 텍스트(fontsize↑, 반투명 패널). render_title_card도 한글 폰트.
- **길이**: worker `duration = min(max(audio_dur or event.duration, MIN=24), MAX=55)`. build_short/build_short_video는 이미 `-t duration`·배경 루프 → 음성보다 길면 배경만 지속.
- **내레이션**: content `narration_max_chars` 180→280(≈30s).

## 5. Implementation Split (다음 /builder)

- **BE(video-assembly)**: 폰트 번들 + render.py(폰트 등록·레이아웃 재설계) + assemble.py(drawtext fontfile) + worker(duration clamp MIN/MAX). config에 `min/max_duration`.
- **BE(content)**: `narration_max_chars` 280.
- **FE 없음**(영상 화면만).

## 6. File Map (기계적)

- `[New] services/video-assembly/app/assets/NanumGothic.ttf` — 번들 한글 폰트(OFL)
- `[Mod] services/video-assembly/app/render.py` — 폰트 등록 + 레이아웃(제목/큰 차트/큰 수치)
- `[Mod] services/video-assembly/app/assemble.py` — drawtext `fontfile`
- `[Mod] services/video-assembly/app/worker.py` + `config.py` — duration clamp(min≈24·max≈55)
- `[Mod] services/content/app/config.py` — `narration_max_chars` 280

## 7. Verification (다음 /builder)

- 렌더 PNG에 한글 정상(matplotlib glyph 경고 0), drawtext fontfile 적용 → 실 mp4에서 자막 한글 정상(AC1)
- `generate.sh` → mp4 길이 ~30s(24~55, AC2), 레이아웃 존·큰 차트/수치 확인(AC3)
- 실 컨테이너 스택 재생성으로 육안 대체(glyph 경고·길이·크기) (AC4)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 영상 화면 — 한글 폰트 번들(NanumGothic OFL, matplotlib+drawtext 공통), 레이아웃 존(제목·큰 차트·큰 수치·자막), 길이 ~30s(clamp), 내레이션 280자. 웹 대시보드는 범위 밖(별도 FE). |
| 20260722 | /builder(1·2) | NanumGothic.ttf 번들(4.5M, OFL) → render.py 폰트 등록+레이아웃 재설계(제목 52pt·중앙 큰 라인차트 lw6·종가 76pt·등락 46pt, 투명), assemble.py drawtext `fontfile`(자막 48pt), worker duration clamp(min24·max55), content narration 280. **실 컨테이너 재생성 검증**: `out/convey-005380-job18.mp4` h264 1080×1920 **43.3s**(AC2), **한글 정상**(미리보기 프레임 육안: 416,500원·+4.39%·한글 자막, glyph 경고 0)(AC1), 레이아웃 존·대형 차트/수치(AC3), 근거 7섹션·10인용. mypy clean. **웹 대시보드(3)는 다음 라운드 /design.** 후속: 제목이 티커(현대차 등 이름 매핑), 목표 30s 튜닝(현 43s). |
