# content (콘텐츠)

- **책임**: 이슈 종목/주제로 **근거에 못박은 스크립트 → 쇼츠**를 만드는 잡의 관리·상태·소유. 스크립트 생성은 `agent`(근거·인용, 알파1), 정확한 차트·수치 렌더+합성은 `video-assembly`(알파3), broll·TTS는 외부 API(커모디티). **content가 스크립트·자산·완성본 상태의 소유자**. 별도 media 도메인 없음. 양산 안정성(잡 재개)이 알파4. **발행은 다루지 않음** → `publishing`.
- **주요 엔티티(안)**: GenerationJob(단계 상태), Script(스크립트+**인용/출처 근거**), Asset(broll·음성 메타), Content(완성본 메타), ReviewStatus, ContentEmbedding(pgvector 히스토리 보조)
- **연동**: `research`/`agent`(근거 데이터·RAG), 미디어(외주 `image-gen`·`tts`), `video-assembly`(정확 렌더), `publishing`(승인본)
- **이벤트(안)**: 자기 큐 `content.generate` → consumer 픽업 / fan-out `image.generate`·`tts.generate` → 완료 join → 합성(내부 status=ready) → 【사람 승인】 → 발행 `content.approved`
- **경계**: 리서치 수집·저장 ✗ → `research`. 이슈 선별 ✗ → `issue-detector`. RAG·프롬프트 루프 ✗ → `agent`. 외부 배포 ✗ → `publishing`.
- **구현 위치(예정)**: `services/content/`(sample-domain 복제) + `content_db`. 미디어는 별도 서비스(외주 래퍼 / ffmpeg).

> 가드레일: **스크립트의 모든 수치는 출처 있는 데이터에 못박음**(환각 금지·알파1). 최종 발행은 **사람 승인 후에만**.
> `content.ready` 이벤트는 두지 않음(내부 상태). 엔티티·fan-out/join·잡 재개는 `/design` 확정. 스크립트·잡은 **빌드 ③**, 미디어·렌더는 **빌드 ④**.
