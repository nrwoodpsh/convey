# 20260723-task-polish.md

> 라운드 ㉗ (품질 마감 — 수치 표기·근사 중복·거시 정리·자막 줄바꿈). ADR 불요(History).
> 계약: `api-contract-polish.py`. 작고 가시적인 거슬림 정리. 외부 API/DB 변경 없음.

## 1. Requirements

- **결론**: 파이프라인·연출은 완성. 남은 **작은 거슬림 4가지**를 정리한다: ① 시나리오/음성 수치 표기(`416500.0원`→`416,500원`), ② 근사 중복 헤드라인(같은 사건 다른 표현) 제거, ③ 거시 문장의 기준연도 단위 노이즈·긴 지표명 정리, ④ 긴 자막 말줄임 → 2줄 줄바꿈.
- **Acceptance Criteria**:
  - [x] AC1: chart 문장 **"현대차 종가 416,500원, 등락률 +4.39%"**(천단위·부호·`.0` 없음). 값 불변. **검증됨.**
  - [x] AC2: 근사 중복 헤드라인 제거(말줄임 앞 토큰 자카드 ≥ **0.4**, 최신 우선). **검증: UX 상하이 중복 2건→1건.**
  - [x] AC3: 거시 노이즈 단위(`1982-84=100`) 생략 + 지표명 축약(`미 CPI`). **검증됨.**
  - [x] AC4: 긴 자막 **2줄 줄바꿈** + 배지 전체 표기. **검증: 프레임 "…생산 차질 / 발생" 2줄, 배지 미절단.**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **수치=사실 불변**: P1은 표기(포맷)만. 값·근거 결속 불변(알파1·3). 슬롯 값은 사람이 읽는 문자열로만 바뀜.
  - **자카드 임계(P2)**: 0.6은 경험값 — 너무 낮으면 다른 사건 병합, 높으면 중복 잔존. 최신 우선 유지. 종목 태깅 기사 우선 순서 보존.
  - **거시 지표명 매핑(P3)**: 사전에 없는 지표는 원명 유지(임의 축약 금지). 단위 노이즈만 규칙 제거.
  - **drawtext 개행(P4)**: ffmpeg drawtext는 실제 개행 문자를 줄바꿈으로 렌더. 한국어는 공백이 적어 **글자 수 기준** 줄바꿈. 2줄 초과분은 말줄임. escape와 개행 공존 주의.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 수치 표기 위치**: 택함 = **agent builder chart 슬롯 포맷**(시나리오·음성 동시 해결) / 기각 = 표시단 각각 / 사유 = 단일 소스.
  - **결정 2 — 근사 중복**: 택함 = **토큰 자카드 dedup**(research service, 완전일치 다음 단계) / 기각 = 임베딩 유사도(ADR 0006 벡터 제외)·LLM 판정(비용) / 사유 = 가볍고 규칙적.
  - **결정 3 — 거시 정리**: 택함 = **노이즈 단위 규칙 제거 + 지표명 축약 사전** / 기각 = 전체 지표 마스터(과함) / 사유 = 최소 작업으로 가독성.
  - **결정 4 — 자막**: 택함 = **글자 수 줄바꿈(최대 2줄)** / 기각 = 말줄임 유지(정보 손실)·자동 폰트 축소(가독성 저하) / 사유 = 정보 보존.

## 3. UI/UX

- 영상·시나리오 텍스트만 바뀜(레이아웃 불변). 예: 자막 "현대차 노사 대립 종식 필요," / "생산차질 지속"(2줄). 거시 "미 CPI 332.6, 한은 기준금리 2.5% 수준입니다."

## 4. Logic

- **P1 (agent builder)**: chart 슬롯 `close = f"{round(price['close']):,}"`, `change_pct = f"{price['change_pct']:+.2f}"`. chart 문장 "…종가 {close}원, 등락률 {change_pct}%". 인용 claim도 정합.
- **P2 (research service.search)**: 완전일치 dedup 뒤, **토큰 자카드**(공백/조사 제거 후 char-3gram 또는 단어 집합) ≥ 0.6이면 기존 유지분과 중복으로 제거. 최신순 유지.
- **P3 (agent builder `_macro_sentence`)**: 단위가 `MACRO_UNIT_DROP` 포함이면 생략, 지표명은 `MACRO_NAME_SHORT`로 축약(없으면 원명). 값 슬롯 불변.
- **P4 (video-assembly assemble `_wrap`)**: 자막 텍스트를 `CAPTION_WRAP_WIDTH`(≈18자) 기준 2줄로 줄바꿈(초과 말줄임). drawtext 실제 개행. 배지 shorten 한도 상향.

## 5. Implementation Split (다음 /builder)

- **agent**: `script/builder.py`(P1 슬롯 포맷 · P3 거시 정리 사전).
- **research**: `domains/research/service.py`(P2 자카드 dedup).
- **video-assembly**: `assemble.py`(P4 `_wrap`·배지 한도).

## 6. File Map (기계적)

- `[Mod] services/agent/app/script/builder.py` — P1 수치 표기 · P3 거시 정리
- `[Mod] services/research/app/domains/research/service.py` — P2 근사 중복 dedup
- `[Mod] services/video-assembly/app/assemble.py` — P4 자막 줄바꿈·배지
- `[New] doc/design/content/api-contract-polish.py` — 표기/정리 규칙 계약

## 7. Verification (다음 /builder)

- 시나리오 조회로 chart 문장 표기(AC1)·거시 정리(AC3)·중복 제거(AC2) 확인.
- 실 mp4 프레임으로 자막 2줄(AC4).
- 단위테스트(builder·tagging) 회귀 통과. 값 불변(수치=사실) 확인.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260723 | /builder | 구현·검증. **P1**(builder): chart 슬롯 `close=f"{round():,}"`·`change=f"{v:+.2f}"`(값 불변). **P2**(research service): 말줄임 앞 토큰 자카드 dedup, 임계 0.4(전체 원제목→핵심부 비교로 조정, 패러프레이즈 포착). **P3**(builder): `_macro_disp`·`_MACRO_NAME_SHORT`·`_MACRO_UNIT_DROP`(지표명 축약·노이즈 단위 생략). **P4**(assemble): `_wrap`(2줄·말줄임), `_esc` 개행 유지, 배지 한도 44. **검증(실 스택)**: job#34 시나리오 "416,500원, +4.39%"·UX 중복 1건·"미 CPI 332.568"; 프레임 자막 "…생산 차질/발생" 2줄·배지 전체. 단위테스트 builder 3(수치 표기 기대값 갱신 — 의도 불변)·va 3·news-feed 통과. **이탈**: 자카드 임계 0.6→0.4(핵심부 비교), 동의어 의미중복은 임베딩 필요(ADR 0006 제외·후속). |
| 20260723 | /design | 품질 마감 — 수치 표기(천단위·부호), 근사 중복 헤드라인 자카드 dedup, 거시 단위 노이즈 제거·지표명 축약, 자막 2줄 줄바꿈. 값=사실 불변(표기만). 계약 `api-contract-polish.py`(mypy 통과). API/DB 변경 없음. |
