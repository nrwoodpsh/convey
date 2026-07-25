# 20260725-task-video-background.md

> 라운드 ㊴ (영상 배경 전략 + 가독성 개선). 알파③. admin(㉝)·image-gen 연계.
> 계약: `api-contract-video-background.py`. video-assembly(`worker`·`assemble`·`broll`) + admin(자산) + image-gen(생성).

## 1. Requirements
- **문제(§7 실측, job-45 프레임)**: ① broll(Pexels)이 종목과 **무관**(현대차 영상인데 아파트 배경) — 검색어 기반이라 엉뚱. ② 차트·수치·자막이 **배경과 겹쳐 가독성↓**(뒤 패널 없음).
- **목표**: 배경을 **운영자가 관리**(등록 라이브러리 + 생성 + Pexels) + **섹터 매칭**으로 관련성↑, 차트·수치·자막 뒤 **반투명 패널**로 가독성↑.
- **가드레일**: 미디어 생성은 외부 API 허용(부패방지 계층·원문 미전달). 수치·차트는 결정론 렌더(알파③) 불변. 배경 자산 라이선스 메타 계승·기록.
- **Acceptance Criteria**:
  - [ ] AC1: **배경 라이브러리** — 운영자가 admin에 배경(영상/이미지) 등록(태그) → video-assembly가 **섹터/태그 매칭**으로 선택. **검증: 자동차 태그 배경 등록 → 현대차 job이 그 배경 사용.**
  - [ ] AC2: **배경 우선순위(auto)** — 라이브러리 매칭 → 생성 → Pexels → 로컬카드, 실패 시 다음. **검증: 라이브러리 없을 때 Pexels 폴백.**
  - [ ] AC3: **생성 배경(옵션)** — image-gen으로 귀여운 이미지 생성·켄번즈. 키 없으면 skip(폴백). **검증: 키 있을 때 생성물 사용, 없을 때 폴백.**
  - [ ] AC4: **가독성 패널** — 차트·수치·자막 뒤 반투명 패널. **검증: 합성 프레임에서 텍스트 뒤 패널 존재·가독성.**
  - [ ] AC5: 가드레일 — 수치·차트 결정론 렌더 불변, 배경 라이선스 메타 기록, 원문 텍스트 외부 미전달.

## 2. 핵심 결정 & 사각지대
- **결정 1 — 배경 소스 = 전략**: admin 라이브러리(등록) + 생성(image-gen) + Pexels(stock) + 로컬. auto 우선순위. broll 무관 해소.
- **결정 2 — 라이브러리 우선**: 운영자 등록 배경이 있으면 최우선(관련성·일관성·무료·통제). 생성은 옵션(비용·API).
- **결정 3 — 생성 배경 포함(확정)**: 사용자 확정 — 브랜드 톤 우려(금융 신뢰 vs 귀여움)를 인지한 뒤 **귀여운 생성 배경을 정식 모드로 포함**. 방식 = **귀여운 이미지 + 켄번즈**(영상 생성은 무겁고 비쌈 → 진짜 애니 영상은 후속). image-gen 래퍼로 외부 이미지 API 호출(부패방지·원문 미전달).
- **사각지대**:
  - **자산 저장·업로드**: 배경 파일은 **공유 볼륨**, admin_db엔 경로·태그·라이선스 메타만(대용량은 볼륨). 업로드 UI 필요.
  - **섹터 매칭 정밀도**: 태그가 부실하면 매칭 실패 → Pexels 폴백. 태그 큐레이션은 운영.
  - **의존**: ㉝ admin(자산 저장)·image-gen(생성) 선행. image-gen은 신규 래퍼(미구축).
  - **가독성 패널 위치**: 인트로/아웃트로 카드엔 불필요(이미 카드). 본편 오버레이에만.
  - **생성 프롬프트**: 섹터·무드만(원문 텍스트 미전달 — 가드레일).

## 3. UI/UX
- 대시보드 **설정 > 배경 자산**: 업로드·태그·토글·삭제. 템플릿/모드에서 배경 전략 선택(auto/library/generated/stock).

## 4. Logic
- **admin**: `background_asset` 테이블 + 업로드 API + CRUD. 파일은 공유 볼륨.
- **video-assembly `worker`**: `select_background(ticker, sector, mode)` → 우선순위 폴백. 기존 `broll.fetch_many`(Pexels)는 stock 단계로.
- **image-gen(신규 래퍼, 확정)**: `generate_background(prompt, out)` — 외부 이미지 생성 API(부패방지 계층). **프롬프트 = 섹터·무드 + "귀여운/심플" 스타일**(원문 텍스트 미전달). 결과 이미지 → 켄번즈 배경. 생성 소스·라이선스 메타 기록. 키 없으면 skip(폴백).
- **assemble.py**: 차트·수치·자막 오버레이 앞에 `ReadabilityPanel`(ffmpeg drawbox 반투명) 추가.

## 5. File Map
- `[Mod] services/video-assembly/app/worker.py` — 배경 선택 전략(우선순위)
- `[Mod] services/video-assembly/app/assemble.py` — 가독성 패널(반투명 박스)
- `[Mod] services/video-assembly/app/broll.py` — Pexels를 stock 단계로 정리
- `[New] services/image-gen/` — 생성 배경 래퍼(외부 이미지 API·부패방지, 귀여운/심플 스타일)
- `[Mod] services/admin/…` — `background_asset` 모델·업로드·CRUD (㉝ 위에)
- `[Mod] services/content 대시보드` — 배경 자산 설정 화면
- `[New] doc/design/video-assembly/api-contract-video-background.py`

## 6. Verification
- 단위: 배경 선택 우선순위(라이브러리→생성→stock→로컬)·태그 매칭. 가독성 패널 삽입.
- 통합: 자동차 배경 등록 → 현대차 job 프레임에 그 배경 + 텍스트 뒤 패널 확인(가독성). 생성 키 유무 폴백.
- 가드레일: 수치 결정론·라이선스 메타·원문 미전달. mypy·계약.

## 7. History
| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260725 | /design | 영상 배경 전략 + 가독성. §7 실측(broll 무관·가독성↓). 결정: 배경 = admin 라이브러리(등록)+**생성(image-gen 정식 포함)**+Pexels+로컬, auto 우선순위·섹터 매칭. 생성은 귀여운 이미지+켄번즈(영상생성 후속). 가독성 패널(반투명). 자산은 공유 볼륨+메타. 의존 ㉝(admin)·image-gen(신규). 수치·차트 결정론 불변(알파③). 계약 mypy 통과. |
| 20260725 | /design(추가) | 사용자 결정 — 브랜드 톤 우려(금융 신뢰 vs 귀여움) 인지 후 **귀여운 생성 배경을 정식 모드로 확정**(옵션/후속 격하 없이). image-gen 래퍼를 정식 구성요소로. |
