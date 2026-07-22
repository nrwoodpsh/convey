# task-broll-pexels-20260722.md

> 라운드 ⑫ (broll 배경 — Pexels 무료 스톡, 사진·영상 둘 다). 커모디티(외주→무료 스톡). ADR 0006·0008.
> 계약 정본 = `doc/design/content/api-contract-pipeline-keyless.py`(MediaAssembleEvent·ContentAssembledEvent 확장).

## 1. Requirements

- **결론**: 배경을 로컬 타이틀 카드 대신 **Pexels 무료 스톡**(사진=B-1, 영상=B-2)으로. 유료 생성형 대체(무료·상업사용). broll은 커모디티(장식)라 실패 시 **로컬 카드 폴백** — 알파(차트·근거)는 불변. **전제**: 차트 오버레이를 **투명 PNG**로 바꿔야 배경이 보인다.
- **Scenario**: video-assembly가 종목/섹터 키워드로 Pexels 사진 또는 영상을 받아 배경으로 깔고, 그 위에 (투명)차트·자막·음성을 합성한다. 받은 자산의 출처·라이선스를 기록한다.
- **Objective**: 무료로 배경 품질↑. B-1·B-2 모두 지원, 실패해도 안전(로컬 카드). 출처·라이선스 메타 계승(가드레일).
- **Acceptance Criteria**:
  - [ ] AC1: 계약(`MediaAssembleEvent.broll_query`·`ContentAssembledEvent` broll 메타) contract-gate 통과
  - [ ] AC2: `PexelsClient`가 키워드로 **사진·영상 각각** 받아 로컬 저장 + 메타(source_url·author·license) 반환(실 Pexels)
  - [ ] AC3: **B-1 사진 배경** 켄번즈 합성 → 9:16 mp4, **배경이 실제로 보임**(차트 오버레이 투명)
  - [ ] AC4: **B-2 영상 배경** 합성 → 9:16 mp4(배경 모션 + 차트·자막·음성)
  - [ ] AC5: Pexels 실패/키없음 → **로컬 카드 폴백**(회귀 0), **broll 출처·라이선스 메타 기록**(가드레일)
  - [ ] AC6: mypy --strict clean, video-assembly 단위 회귀 없음

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **차트 불투명 문제**: 현재 `render_chart`가 흰 배경 full-frame → 배경 가림. **`transparent=True`** + 차트를 하단/일부 영역으로 해야 broll이 보임.
  - **9:16 크롭**: Pexels 사진·영상은 가로도 많음 → `orientation=portrait` 우선 + scale/crop 1080×1920.
  - **영상 길이 < 내레이션**: 배경 영상이 짧으면 `-stream_loop`로 반복.
  - **온라인·용량**: 영상 다운로드는 수 MB·네트워크. 실패 폴백 필수.
  - **라이선스 기록**: 가드레일 — 미디어 자산 출처·라이선스 계승. Content에 broll 메타 저장.
  - Pexels 무료 한도(200/시간) — 잡당 1~2요청이라 여유.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 배경 모드**: 택함 = **B-1·B-2 둘 다 구현 + `broll_mode`(video|photo|off) 설정 + 폴백 사슬**(video→photo→로컬카드) / 기각 = 하나만 / 사유 = 사용자 요구(둘 다). 모드로 택하고 실패 시 안전 강등.
  - **결정 2 — 차트 오버레이**: 택함 = **투명 PNG**(`savefig(transparent=True)`) + 차트를 화면 하단부 패널로(배경 상단 노출) / 기각 = 현행 불투명 / 사유 = broll 가시성(안 그러면 broll 무의미).
  - **결정 3 — Pexels 계층**: 택함 = **`PexelsClient` 부패방지 계층**(video-assembly 내) — 검색·다운로드·메타 격리, 실패 시 None / 기각 = 워커 직접 호출 / 사유 = 격리·폴백·테스트 용이.
  - **결정 4 — 메타 기록**: 택함 = `ContentAssembledEvent`에 broll 메타(source_url·author·license) → **Content에 저장**(컬럼 추가·마이그레이션) / 기각 = 로그만 / 사유 = 가드레일(출처·라이선스 계승은 기록이어야).
  - **결정 5 — 검색어**: 택함 = content가 `broll_query` 전달(종목/섹터/일반 금융 키워드), 없으면 video-assembly가 title/기본어 / 기각 = 고정 / 사유 = 종목 맥락 배경.

## 3. UI/UX
해당 없음. 산출 mp4 배경이 스톡 사진/영상.

## 4. Logic

```
content.handle_generate: media.assemble에 broll_query 추가(예: "반도체"/"stock market")

video-assembly.handle_assemble:
  bg = fetch_broll(query, mode)          # PexelsClient: 모드별 사진/영상 다운로드 + 메타
     ├ 성공(photo) → build_short(photo, chart_t, ...)          # B-1 켄번즈
     ├ 성공(video) → build_short_video(video, chart_t, ...)    # B-2 영상 배경
     └ 실패/off   → render_title_card → build_short(card,...)  # 폴백(현행)
  content.assembled { ok, mp4_path, broll_source_url?, broll_author?, broll_license? }

PexelsClient(부패방지):
  search_photo(q)/search_video(q) → 첫 세로 결과 → 파일 다운로드(media_dir) → (path, meta) | None
render_chart: savefig(transparent=True), 차트를 하단 패널로(배경 상단 노출)
build_short_video: 배경=영상(scale/crop 1080x1920, -stream_loop) + 투명차트 overlay + 자막 + 음성
```

## 5. Implementation Split (다음 /builder)

- **BE(video-assembly)**: `broll.py`(PexelsClient: photo/video 검색·다운로드·메타·폴백 None). `render.py` `render_chart` 투명화·레이아웃. `assemble.py` `build_short_video`(영상 배경) 추가. `worker.handle_assemble` broll 분기·폴백·메타 회신. `config.py` `pexels_api_key`·`broll_mode`.
- **BE(content)**: `handle_generate` `broll_query` 세팅. `handle_assembled`가 broll 메타 → `Content` 저장. `models.Content` broll 컬럼 + 마이그레이션.
- **계약**: `MediaAssembleEvent.broll_query`, `ContentAssembledEvent` broll 메타.
- **.env.example**: `PEXELS_API_KEY`.
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] doc/design/content/api-contract-pipeline-keyless.py` — broll_query·broll 메타
- `[New] services/video-assembly/app/broll.py` — PexelsClient
- `[Mod] services/video-assembly/app/render.py` — 투명 차트
- `[Mod] services/video-assembly/app/assemble.py` — build_short_video(영상 배경)
- `[Mod] services/video-assembly/app/worker.py` — broll 분기·폴백·메타
- `[Mod] services/video-assembly/app/config.py` — pexels_api_key·broll_mode
- `[Mod] services/content/app/consumer.py` — broll_query·broll 메타 저장
- `[Mod] services/content/app/domains/content/models.py` — Content broll 컬럼
- `[New] services/content/alembic/versions/{rev}_content_broll.py` — 마이그레이션
- `[Mod] .env.example` — PEXELS_API_KEY

## 7. Verification (다음 /builder)

- 계약: mypy (AC1)
- `PexelsClient` 실 Pexels: 사진·영상 다운로드 + 메타(AC2)
- B-1 mp4: 배경 사진 보임 + 차트 투명 오버레이(AC3). B-2 mp4: 영상 배경(AC4)
- 키없음/실패 모의 → 로컬 카드 폴백, mp4 정상(AC5). broll 메타 Content 저장(AC5)
- mypy·va 단위 회귀(AC6)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | Pexels broll(사진 B-1·영상 B-2 둘 다) — 부패방지 PexelsClient, 투명 차트(배경 가시), 폴백 사슬(video→photo→로컬카드), 출처·라이선스 메타 Content 기록. 유료 생성형 → 무료 스톡 대체(ADR 기록 예정). |
| 20260722 | /builder | `broll.py`(PexelsClient: 사진·영상 검색·다운로드·메타·폴백None) + `render_chart` **투명 RGBA 1080×1920**(하단 배치·반투명 박스) + `build_short_video`(영상 배경) + worker broll 분기·폴백·메타 + config(pexels·broll_mode). content: `broll_query`(_BROLL_QUERY="stock market") + `handle_assembled` broll 메타→Content 저장, Content broll 컬럼 3 + Alembic `7598c32287dd`(**실 content_db 적용**). 계약 `broll_query`·broll 메타. `.env.example` PEXELS_API_KEY. **ADR 0009** 기록. **검증(실 Pexels·ffmpeg)**: 사진(Markus Spiske)·영상(Kampus 32MB) 다운로드+메타(AC2), 차트 RGBA 투명(AC3 배경노출), B-1 사진·B-2 영상 mp4 h264 1080×1920(AC3·AC4), 키없음→None 폴백(AC5), worker 통합 broll 메타(source·author·license=Pexels) content.assembled 회신(AC5). mypy·contract-gate clean, va 단위 3 회귀 없음(AC6). **이탈**: broll_query는 Pexels 커버리지상 영문 "stock market" 고정(POC) — 섹터→영문 매핑 후속. |
