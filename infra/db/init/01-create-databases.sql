-- 서비스별 DB 분리 (proper MSA — 각 서비스는 자기 DB만 소유)
-- 단일 Postgres 인스턴스 안에서 논리적으로 분리. 운영에선 인스턴스 자체 분리 권장.
-- 인증은 Supabase(외부)로 위임 — auth_db 없음 (ADR 0007)
CREATE DATABASE sample_db;
-- CONVEY 도메인 DB
CREATE DATABASE research_db;   -- 시세·기사·출처(사실). 관계·인과는 Neo4j research_graph(round①)
CREATE DATABASE content_db;    -- 잡·스크립트·자산·완성본 상태
-- TODO(후속): CREATE DATABASE publishing_db;
