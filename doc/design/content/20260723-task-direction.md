# 20260723-task-direction.md

> 라운드 ㉖ (영상 연출 강화 — 단일 배경 + 오버레이). ADR 0012 연장선.
> 계약: `api-contract-direction.py`. 배경 방식은 **단일 배경 유지**(사용자 확정) — 컷 전환 리스크 회피.

## 1. Requirements

- **결론**: 정적이던 화면을 **오버레이 연출**로 살린다(배경은 1개 유지, 안정·빠름). ㉕ Phase C(구간 자막 싱크·배지) 위에: ① **수치 팝**(종가·등락률이 chart 구간에 등장), ② **금색 강조**(종목 라벨·핵심 구간 자막), ③ **인트로/아웃트로 카드**(0.8s 전면).
- **범위 밖**(후속): 세그먼트별 배경 컷/xfade 전환, 수치 scale 바운스(이번은 fade 등장).
- **Acceptance Criteria**:
  - [x] AC1: **수치 팝** — chart 구간 start에 fade-in 등장. **검증: 4s 미표시 → 10s "416,500원 +4.39%" 등장.**
  - [x] AC2: **금색 강조** — 종목 라벨 금색 + chart·relation 구간 자막 금색. **검증: "현대차(005380)" 금색, 10s 자막 금색.**
  - [x] AC3: **인트로/아웃트로** 전면 카드. **검증: 0.4s 인트로(제목·금색 종목·CONVEY), 30.6s 아웃트로(CONVEY·출처).**
  - [x] AC4: 단일 배경·안정 — 폴백 불변. **검증: job#31 ready, va 단위테스트 3 통과.**

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - **수치 팝 구현**: 차트를 **2장으로 분리**(base=제목·라벨·라인차트 / numbers=종가·등락) 해야 수치만 따로 등장 가능. numbers 오버레이에 `fade=in:alpha=1:st=<chart_start>`. scale 바운스는 ffmpeg 시간식 제약으로 이번 제외(fade로 등장감).
  - **chart 구간 타이밍**: numbers fade 시점 = segments의 chart 항목 (start). worker가 captions(kind 보유) 에서 계산 — 이벤트 계약 불변.
  - **인트로/아웃트로 = 전면 오버레이**(concat 아님): 전면 카드 PNG를 `enable='lt(t,0.8)'`·`gt(t,dur-0.8)`로 배경 위 덮음. concat 재인코딩 리스크 회피. 오디오는 밑에서 계속(인트로 동안 음성 시작 겹침 → 인트로 0.8s로 짧게).
  - **금색 인라인 강조 불가**: drawtext는 문장당 단색 → 종목명만 금색으로 인라인 강조는 어려움. 대신 **구간 단위 색**(핵심 구간 자막 전체 금색) + 종목 라벨 금색으로 대체.
  - **오버레이 개수↑ → 필터 체인 길이**: base·numbers·intro·outro·captions·badge. escape·라벨 관리 주의(실패 시 폴백).
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 배경**: 택함 = **단일 배경 유지 + 오버레이 연출**(사용자 확정) / 기각 = 세그먼트 컷 전환(ffmpeg concat 리스크·합성 시간↑) / 사유 = 안정·빠름.
  - **결정 2 — 수치 팝**: 택함 = **차트 base/numbers 분리 + numbers fade-in**(chart 구간) / 기각 = 단일 차트 PNG(수치만 애니 불가)·scale 바운스(시간식 제약) / 사유 = 등장 타이밍만으로도 리듬, 리스크 최소.
  - **결정 3 — 인트로/아웃트로**: 택함 = **전면 오버레이 enable 시간창** / 기각 = 별도 클립 concat(재인코딩·정렬 리스크) / 사유 = 단순·안정.
  - **결정 4 — 강조**: 택함 = **구간 단위 금색 자막 + 라벨 금색** / 기각 = 인라인 키워드 강조(drawtext 단색 한계) / 사유 = 실현 가능·충분한 체감.

## 3. UI/UX (영상)

```
[0~0.8s]  인트로 카드(전면): 제목 + 종목(금색) · CONVEY.
[본편]    단일 배경 + 차트 base(라인·라벨 금색) 상시
          + 수치(종가·등락) chart 구간에 fade-in 팝
          + 구간 자막(핵심=금색, 그 외 흰색, 시간 싱크) + 신뢰 배지(우상단)
[끝 0.8s] 아웃트로 카드(전면): 출처·날짜 · CONVEY.
```

## 4. Logic

- **render.py**:
  - `render_chart` → `render_chart_base`(제목 + 종목 라벨 **금색** + 라인차트, 수치 제외) + `render_numbers`(종가·등락만, 투명, 동일 위치).
  - `render_intro_card(title, stock_label)` / `render_outro_card(badge_text)` — 다크 브랜드 전면 카드(1080×1920, 불투명).
- **assemble.py** (`_text_layer` 확장 + 오버레이):
  - 오버레이 순서: 배경 → chart_base → numbers(`fade` st=chart_start) → intro(`enable lt(t,INTRO)`) → outro(`enable gt(t,dur-OUTRO)`) → captions(구간, 금색 플래그) → badge.
  - captions: `list[tuple[text,start,end,gold]]`. gold면 fontcolor=금색.
- **worker.py**: chart_base·numbers·intro·outro 렌더 호출; captions에 kind 기반 gold 플래그(chart·relation)와 chart_start 산출해 assemble에 전달. 실패/무 segments면 기존 단일 경로(폴백).

## 5. Implementation Split (다음 /builder)

- **video-assembly**: `render.py`(base/numbers 분리·intro/outro·라벨 금색), `assemble.py`(오버레이·자막 색·인트로/아웃트로 enable), `worker.py`(렌더 호출·타이밍/색 전달·폴백). content/agent 변경 없음.

## 6. File Map (기계적)

- `[Mod] services/video-assembly/app/render.py` — render_chart_base·render_numbers·render_intro_card·render_outro_card·라벨 금색
- `[Mod] services/video-assembly/app/assemble.py` — numbers/intro/outro 오버레이 + 자막 금색 플래그
- `[Mod] services/video-assembly/app/worker.py` — 렌더 호출·chart_start·gold 전달·폴백
- `[New] doc/design/content/api-contract-direction.py` — 내부 렌더 형태 계약

## 7. Verification (다음 /builder)

- 프레임 0.3s=인트로 카드, chart 구간 직전/직후=수치 미표시→등장(팝), 핵심 구간 자막 금색, 마지막=아웃트로.
- segments 없는 경로(자동양산 등) 회귀: 기존 단일 자막·차트 정상.
- video-assembly 단위테스트(build_short* 시그니처 확장 하위호환) 통과. 실 컨테이너 mp4 육안.

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260723 | /builder | 구현·검증(video-assembly). render.py: `render_chart_base`(제목·금색 라벨·라인)/`render_numbers`(수치 분리)·`render_intro_card`/`render_outro_card`·라벨 금색. assemble.py: `_run` 공용 오버레이 체인(배경→차트→수치 fade→자막(금색 플래그)→배지→인트로/아웃트로 enable 시간창), `build_short`·`build_short_video`에 numbers/pop/intro/outro 인자. worker.py: base·numbers·intro·outro 렌더 + `_segment_audio`가 kind 유지 → chart 구간 pop_start·chart/relation 자막 금색. **검증(실 스택)**: 현대차 job#31 프레임 — 0.4s 인트로 카드, 4s 수치 미표시→10s 팝 등장 "416,500원 +4.39%", 라벨·핵심 자막 금색, 30.6s 아웃트로(출처·날짜); ready; va 단위테스트 3 통과. **이탈**: (1) scale 바운스·배경 컷 전환은 후속(fade 등장으로 대체), (2) 자막/배지 shorten으로 긴 텍스트 말줄임(배지 34자·자막 30자), (3) 차트 자막 "416500.0원" 소수점(후속). |
| 20260723 | /design | 연출 강화(단일 배경 + 오버레이) — 수치 팝(차트 base/numbers 분리·fade 등장), 금색 강조(라벨·핵심 구간 자막), 인트로/아웃트로 전면 카드(0.8s). 배경 컷 전환·scale 바운스는 후속(사용자 확정: 안정·빠름). 계약 `api-contract-direction.py`(mypy 통과). video-assembly 국한. |
