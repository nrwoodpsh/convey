# 20260725 — 요약: 영상 배경 라이브러리 + 가독성 패널 (라운드㊴ P1)

- **Task**: `doc/design/video-assembly/20260725-task-video-background.md` · 계약 `api-contract-video-background.py`
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: AC1·AC2·AC4·AC5 완료·검증. AC3(생성 배경 image-gen)·업로드 UI는 P2/M2 이관(사용자 결정: 검증가능 핵심 우선).

## 개요

broll(Pexels)이 종목과 무관하던 문제(§7 실측: 현대차 영상에 아파트 배경)와 차트·수치가 배경과 겹쳐 가독성↓ 문제를 해소한다(㊴ P1). 운영자가 admin에 **배경 자산(태그)**을 등록하면 video-assembly가 **섹터/태그 매칭**으로 관련 배경을 우선 선택하고, 차트·수치 뒤에 **반투명 패널**을 깔아 가독성을 확보한다.

## 변경사항 (BE)

- **admin**: `background_asset` 모델(name·tags(JSON)·path·kind·license·enabled) + repository·service·router CRUD(`GET/POST/PUT/DELETE /admin/backgrounds`) + 마이그레이션 `0003_background_asset`. 파일 본체는 공유 볼륨, DB엔 경로·태그·라이선스 메타만.
- **video-assembly `background.py`**(신규): `fetch_backgrounds()`(GET /admin/backgrounds, HMAC) · `match_background(assets, ticker)`(섹터/태그 교집합 + 파일 존재, 순수 함수) · `select_library_background(ticker)`.
- **video-assembly `worker.py`**: 배경 선택 우선순위(㊴) — auto: **라이브러리 매칭 → Pexels(stock) → 로컬 카드**, `composed` 플래그로 폴백. 공용 오버레이 kwargs를 `_Overlay` TypedDict로 정리(배경만 교체).
- **video-assembly `assemble.py`**: 가독성 패널(`panel`·`panel_opacity`) — 중앙 밴드에 `drawbox` 반투명 어둠 박스. `build_short`/`build_short_video`에 전파(기본 ON).
- **video-assembly `config.py`**: `admin_url`·`background_mode`(auto|library|stock) 추가.

## API 변경

- **admin 신규**: `GET /admin/backgrounds`·`GET /{id}`·`POST`·`PUT`·`DELETE`(east-west HMAC).
- video-assembly → admin `GET /admin/backgrounds` 소비. Kafka 이벤트(media.assemble·content.assembled) 불변. 단 `content.assembled` 회신 메타에 라이브러리 배경 시 `bg_source`·`bg_name`·`bg_license` 추가.

## 검증

- 단위: video-assembly 7(매칭 4 — 섹터매칭·무관·비활성/파일없음·종목명매칭 + 기존 회귀 3), admin 2. mypy `--strict` 0(admin 5·video-assembly 4). 계약 mypy 0.
- **mypy 부채 해소**: worker.py의 `**common`(dict) 언패킹이 baseline에서 이미 12건 오류였음 → `_Overlay` TypedDict로 정리해 0.
- **실스택**(재빌드 admin·video-assembly):
  - 마이그레이션 0003 → `background_asset` 생성.
  - CRUD `POST /admin/backgrounds` 200(자동차 배경).
  - 라이브 매칭: 현대차(005380·섹터 자동차) → 자동차 배경 선택(라이선스 CC0 계승) / 삼성전자(반도체) → 무관 None.
  - 가독성 패널 실측: 흰 배경 합성 프레임에서 코너 밝기 253 vs 중앙 139 → 패널이 중앙(차트 영역)을 어둡게.

## 특이사항 (설계 대비·후속)

- **P2 이관(AC3)**: 생성 배경(image-gen 신규 래퍼·귀여운 이미지+켄번즈)은 다음 라운드. 우선순위 체인(auto: 라이브러리→**[생성]**→Pexels→로컬)에 삽입 지점만 확보.
- **M2 이관**: 배경 자산 업로드·태그·토글 대시보드 UI(공유 볼륨 멀티파트)는 M2 대시보드 리디자인으로(㉝ P2·㊳ 편집 UI와 함께).
- **가드레일**: 선택 배경 license를 회신 메타에 기록(출처 계승), render.py 결정론 렌더 불변(알파③), admin_db는 API로만 접근.
- **패널 모서리 라운드**: 계약의 `ReadabilityPanel.radius`는 drawbox가 사각이라 미적용(직사각 패널). 라운드 처리는 후속 미세조정.
- 커밋: 아직(사람 게이트 — `/commit`).
