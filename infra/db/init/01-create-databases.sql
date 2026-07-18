-- 서비스별 DB 분리 (proper MSA — 각 서비스는 자기 DB만 소유)
-- 단일 Postgres 인스턴스 안에서 논리적으로 분리. 운영에선 인스턴스 자체 분리 권장.
CREATE DATABASE auth_db;
CREATE DATABASE sample_db;
-- CONVEY 도메인 DB
CREATE DATABASE research_db;
CREATE DATABASE content_db;
-- TODO(후속): CREATE DATABASE publishing_db;
