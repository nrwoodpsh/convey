# 20260726 — 요약: 대시보드 리디자인 프런트 (라운드㊵ P2)

- **Task**: `doc/design/content/20260725-task-dashboard-redesign.md` · 계약 `api-contract-dashboard-redesign.py` · ADR 0010
- **작업**: /run(builder→sync) · 2026-07-26 · main · 로컬 검증(JS 구문·FE 셸·라우트 라이브)
- **상태**: AC1~AC5 완료. M2 대시보드 리디자인 종료 — 미뤄둔 관리 UI(설정·템플릿·배경)가 한 화면으로.

## 개요

P1에서 만든 백엔드 라우트를 소비하는 프런트를 구현한다(㊵ P2). 대시보드에 **설정 탭**(admin 중계 CRUD)·**품질 지표 카드**·**근거 패널**을 추가. 순수 프런트(index.html)라 서버 로직 변경 없음.

## 변경사항 (FE — services/content/app/static/index.html)

- **설정 탭(AC1·AC2)**: maintab 3번째 "설정" 추가 + 서브탭 6종 폼 — 종목(체크박스·검색, `/ui/settings/stocks` 토글) · 키워드(추가/삭제/토글) · 소스(naver·rss·dart 토글) · 기간(1w/1m/3m select) · 시나리오 템플릿(노브 편집·추가·삭제) · 배경 자산(이름·태그·경로·종류·라이선스 등록·삭제·토글).
- **품질 지표(AC4)**: 상단 지표 스트립(`#metrics`) 5카드 — 그래프 노드·관계·오늘 기사·오늘 이슈·완성 쇼츠. `loadMetrics`가 init·오늘자 탭 전환 시 `/ui/metrics` 갱신.
- **근거 패널(AC3)**: `renderEvidence(jobId)` — 시나리오 편집(step3)·완성본 미리보기에 `/ui/jobs/{id}/evidence`의 관계·출처(링크)·수치 표시.
- CSS: metrics·subtabs·setrow·sw(토글)·evi(근거) 스타일 추가. 기존 마법사·쇼츠 탭 불변(AC5).

## API 변경

- 없음(FE만). P1의 `/ui/settings/*`·`/ui/metrics`·`/ui/jobs/{id}/evidence` 소비.

## 검증

- JS 구문: 추출 스크립트 `node --check` 통과. HTML 균형(div 103/103·script 1/1).
- 재빌드 후 FE 셸: `data-tab="settings"`·`#metrics`·`#tab-settings`·`loadMetrics`·`renderStocks`·`renderEvidence`·`renderBackgrounds` 존재 확인.
- **FE 호출 경로 라이브 200**(재빌드 content): 설정 조회(stocks·templates·sources·period)·키워드 왕복(POST→admin_db→DELETE)·period `/_` PUT(1m→원복)·템플릿 전체 PUT·배경 POST/DELETE. P1에서 metrics·evidence 데이터 검증 완료.

## 특이사항 (설계 대비·후속)

- **검증 한계(정직)**: DOM 시각 렌더는 브라우저 수동 확인 영역 — 헤드리스 렌더는 미검증. 대신 셸 서빙·JS 구문·FE가 호출하는 라우트의 라이브 200으로 대체 검증(순수 FE 특성).
- **배경 업로드**: 배경은 메타(공유 볼륨 경로) 등록 — 파일 업로드(멀티파트)는 후속(admin 업로드 엔드포인트·볼륨 쓰기 필요).
- **지표 갱신**: 폴링(2.5s)에 묶지 않음(Neo4j 12k 노드 count 부담) — init·오늘자 탭 전환 시 갱신.
- **가드레일**: /ui 무인증 로컬(ADR 0010, M4에서 게이트웨이 뒤로). 설정 쓰기는 content→admin 중계(Database per Service). 수치·근거는 저장된 사실(환각 아님).
- 커밋: 아직(사람 게이트 — `/commit`).
