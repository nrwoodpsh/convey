# ADR 0009 — broll 배경: 유료 생성형 → 무료 스톡(Pexels)

- **상태**: 채택 (2026-07-22)
- **맥락**: 쇼츠 배경(broll)은 알파가 아니라 커모디티(장식)다(ADR 0004). 초기엔 유료 생성형 이미지(나노바나나/Gemini Image류)를 상정했으나, 생성형 영상은 POC 제외(ADR 0006)이고 유료다. 배경은 "무료로 충분히 좋게"면 된다.
- **결정**:
  - broll 배경을 **Pexels 무료 스톡**(이미지 + 영상)으로 조달. 상업사용 OK·출처표기 불요, 무료 API 키.
  - **사진(B-1, 켄번즈)·영상(B-2, 배경 클립) 둘 다** 지원. `broll_mode`(video|photo|off)로 선택, 실패 시 폴백 사슬(video→photo→**로컬 타이틀 카드**).
  - 조달은 **부패방지 계층**(`video-assembly/broll.py` PexelsClient)에 격리. 받은 자산의 **출처·작가·라이선스 메타를 Content에 기록**(가드레일: 미디어 자산 출처 계승).
  - 차트 오버레이를 **투명 PNG**로 바꿔 배경이 보이게 함(전제).
- **트레이드오프**: Pexels는 **온라인**(스톡 다운로드) — 완전 오프라인 아님. 대신 무료·상업사용·인기(업계 표준). 네트워크/키 실패 시 로컬 카드로 안전 강등(파이프라인 불변).
- **대안(기각)**:
  - 유료 생성형 이미지/영상(나노바나나·Sora류) — 유료 + 생성형 영상은 ADR 0006 제외.
  - Unsplash — 사진만(영상 없음), API 규칙 까다로움.
  - 완전 오프라인(로컬 절차적/번들) — "실사 배경" 품질 포기. 로컬 카드가 이미 그 폴백.
- **영향**: `video-assembly`에 PexelsClient·영상 배경 합성(`build_short_video`)·투명 차트. `content`에 broll 메타 컬럼(Content). 계약 `MediaAssembleEvent.broll_query`·`ContentAssembledEvent` broll 메타. `.env` `PEXELS_API_KEY`(무료).
- **관련**: [0004](알파 — broll은 커모디티), [0006](생성형 영상 제외), [0008](무료 소스 지향). broll 유료 상정을 대체.
