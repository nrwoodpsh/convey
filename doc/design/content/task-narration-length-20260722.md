# task-narration-length-20260722.md

> 라운드 ⑮ (B2 — 내레이션 길이 조절). 쇼츠 완성도. ADR 0006.
> 계약 변경 없음. 자연어 설계만.

## 1. Requirements

- **결론**: 지금 내레이션이 **스크립트 전체**(hook + chart + 사실 전부 + 거시 5개)를 낭독해 음성이 ~38s로 길어진다. 쇼츠엔 다소 길다. **내레이션만 요약·축약**해 길이를 줄인다. 스크립트·자막·인용(근거)은 **전체 유지**.
- **Scenario**: content가 media.assemble에 넣는 `narration`을 **핵심만 뽑아 문자 예산 내로** 만든다. video-assembly는 그 짧은 음성으로 합성(길이 = 음성 길이).
- **Objective**: 쇼츠 적정 길이. 근거·자막은 온전, 음성만 간결.
- **Acceptance Criteria**:
  - [ ] AC1: 변경 파일 `mypy --strict` 통과(계약 변경 없음)
  - [ ] AC2: `_narration`이 **문자 예산(`narration_max_chars`) 이내** + 핵심 포함(hook + 종목 종가·등락률 + 대표 사실/거시 각 1)
  - [ ] AC3: 실 TTS로 **축약 내레이션 음성이 전체 낭독 대비 뚜렷이 짧음**(측정), mp4 길이 축소
  - [ ] AC4: **스크립트 sections·citations는 전체 유지**(근거·자막·인용 회귀 없음), mp4 정상 생성
  - [ ] AC5: mypy·content·va 단위 회귀 없음

## 2. 사각지대 & 핵심 결정 (수정 가능성 순)

- **사각지대**:
  - 축약과 근거 혼동 금지 — **자막/인용(citations)은 전체**여야 알파1(근거) 유지. 줄이는 건 **음성 낭독 텍스트뿐**.
  - 거시 5개 전부 읽으면 김 → 대표 1개만.
  - 문자 예산과 실제 음성 길이는 비례하나 정확 일치 아님(예산은 프록시).
  - 하드 길이 클램프(video duration cap)는 음성을 중간에 자름 → 금지.
- **핵심 결정**(택함 + 기각):
  - **결정 1 — 축약 방식**: 택함 = **핵심 섹션만 요약 낭독**(hook + chart 1문장 + 사실 1 + 거시 1) + 문자 예산 상한 / 기각 = 전체 낭독(김)·하드 duration 클램프(음성 잘림) / 사유 = 자연스러운 짧은 음성.
  - **결정 2 — 근거 보존**: 택함 = **Script sections·citations 전체 유지**, narration만 축약 / 기각 = 스크립트도 축약(근거 손실) / 사유 = 알파1(근거·자막)은 온전해야.
  - **결정 3 — 예산 위치**: 택함 = **content._narration에서 축약**(config `narration_max_chars`) / 기각 = video-assembly에서 자름 / 사유 = "무엇을 말할지"는 content(스크립트 소유)의 책임.

## 3. UI/UX
해당 없음. 결과 쇼츠 음성이 짧아짐.

## 4. Logic

```
content._narration(sections, max_chars):
  parts = [hook, chart(슬롯 해소 1문장), 첫 fact 1, 첫 macro 1]   # 대표만
  text = " ".join(parts)
  if len(text) > max_chars: text = text[:max_chars] 마지막 문장 경계에서 컷
  return text
# 자막(subtitle=hook)·Script(sections/citations 전체)는 불변
```
- 거시/사실이 여럿이어도 **각 1개**만 낭독 → 길이 안정.

## 5. Implementation Split (다음 /builder)

- **BE(content)**: `consumer._narration` 축약(대표 섹션 + 문자 예산·문장 경계 컷). `config.narration_max_chars`(예: 180).
- **FE 없음.**

## 6. File Map (기계적)

- `[Mod] services/content/app/consumer.py` — `_narration` 축약 로직
- `[Mod] services/content/app/config.py` — `narration_max_chars`

## 7. Verification (다음 /builder)

- 계약 변경 없음 → mypy (AC1)
- `_narration`(거시 5·사실 여럿 샘플) → 예산 이내, hook·종가·등락·대표 사실/거시 포함(AC2)
- 실 edge-tts: 축약 narration 음성 길이 << 전체 낭독(이전 ~38s), mp4 길이 축소(AC3)
- Script sections/citations 전체 유지 확인(AC4). content·va 단위 회귀(AC5)

## 8. History

| 일시 | 단계 | 내용 |
|:---|:---|:---|
| 20260722 | /design | 내레이션 축약(핵심 섹션 + 문자 예산) — 음성만 간결, 스크립트·자막·인용 전체 유지. 하드 클램프 금지(음성 잘림). |
| 20260722 | /builder | `_narration` 축약 — hook·chart·사실1·거시1 대표만 + `_clip`(문자 예산·문장/단어 경계 컷). config `narration_max_chars=180`. **검증**: 예산 이내+핵심(종목·종가·등락·대표 사실) 포함(AC2), **실 edge-tts 전체 35.7s→축약 20.4s(43%↓)**(AC3), Script sections·citations·subtitle 저장 경로 불변으로 전체 유지(AC4), mypy clean(AC5). **이탈/한계**: 거시 섹션이 한 줄에 다지표라 "대표 1개"가 실질 전체 거시 — 문자 예산이 실 상한(후속: 거시 섹션 분리 시 대표화 정밀도↑). |
