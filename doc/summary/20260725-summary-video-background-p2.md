# 20260725 — 요약: 생성 배경(image-gen) (라운드㊴ P2)

- **Task**: `doc/design/video-assembly/20260725-task-video-background.md` (AC3) · 계약 `api-contract-video-background.py`
- **작업**: /run(builder→sync) · 2026-07-25 · main · 로컬 단위 + 실스택
- **상태**: AC3 완료·검증. ㊴ 배경 전략 전 우선순위 체인 완성(라이브러리→생성→Pexels→로컬).

## 개요

배경 우선순위 체인에 **생성 배경**을 삽입한다(㊴ P2). image-gen 래퍼가 섹터·무드 기반 프롬프트로 귀엽고 심플한 배경 이미지를 외부 API로 생성해 켄번즈 배경으로 쓴다. 키가 없으면 생성 단계를 건너뛰고 Pexels로 폴백(파이프라인 보호). 원문 텍스트는 외부로 넘기지 않는다(프롬프트=섹터·무드·스타일만).

## 변경사항 (BE)

- **video-assembly `imagegen.py`**(신규, in-process 래퍼): `build_prompt(ticker)`(섹터→무드 사전 + "귀여운/심플" 스타일, 원문 미전달) · `ImageGenClient`(외부 호출을 `_call_api`에 격리 — OpenAI images 호환, 키·URL 없으면 None) · `generate(ticker, out)`(키 없으면 skip=None, 성공 시 `GeneratedBackground`(path·prompt·source·license="generated")) · `make_client()`.
- **video-assembly `worker.py`**: 배경 우선순위에 생성 단계 삽입 — auto: 라이브러리 → **생성** → Pexels → 로컬. mode 게이팅 정리(library/generated/stock 각 전용 경로). 생성 배경 시 회신 메타 `bg_source=generated`·`bg_prompt`·`bg_model`·`bg_license`.
- **video-assembly `config.py`**: `image_gen_api_key`·`image_gen_api_url`(기본 OpenAI images 호환)·`image_gen_model`, `background_mode`에 generated 추가.
- **video-assembly `background.py`**: 우선순위 주석을 현재(생성 포함)로 정정.

## API 변경

- 없음(외부 이미지 생성 API 호출은 video-assembly 내부, 부패방지 계층). Kafka 이벤트·계약 불변. `content.assembled` 회신 메타에 생성 배경 필드 추가.

## 검증

- 단위: video-assembly 11(imagegen 4 — 프롬프트 섹터-only·미상 섹터 기본·키없음 skip·`_call_api` 키없음 None + 기존 회귀 7). mypy `--strict` 0(3파일).
- **실스택**(재빌드 video-assembly): 프롬프트 = "도로와 자동차 모티프의 귀엽고 심플한… 9:16 …글자 없음"(현대차 종목명·원문 미포함). `image_gen_api_key` 미설정 → `generate` None(skip → Pexels 폴백).

## 특이사항 (설계 대비·후속)

- **이탈(구조)**: File Map은 `services/image-gen/`(별도 마이크로서비스)였으나, 기존 미디어 래퍼(`broll.py` Pexels·`tts.py` edge-tts)와 일관되게 **video-assembly in-process 래퍼**로 구현. 이유: 워커 우선순위 체인에서 **동기 호출**, 신규 서비스(FastAPI·compose·게이트웨이 라우트) 오버헤드 회피, 부패방지 경계(격리 모듈·프롬프트 only·키 게이팅)는 그대로. `image.generate` 토픽 async fan-out 도입 시 별도 서비스 승격이 후속.
- **범위**: 키 있는 생성물 사용 경로는 키 미보유로 라이브 불가 — 설계상 "키 없으면 skip" 폴백 경로를 검증. 키 발급 후 생성물 품질·비용은 후속 튜닝.
- **가드레일**: 원문 텍스트 미전달(프롬프트=섹터·무드·스타일), 생성물 license="generated" 메타 기록, 수치·차트 결정론 렌더 불변(알파③).
- 커밋: 아직(사람 게이트 — `/commit`).
