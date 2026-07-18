-- pgvector 확장 — RAG 임베딩(분리 인덱스: research_db=원문, content_db=콘텐츠 히스토리)
-- pgvector/pgvector 이미지에 확장 바이너리가 포함됨. DB별로 CREATE EXTENSION 필요.
\connect research_db
CREATE EXTENSION IF NOT EXISTS vector;

\connect content_db
CREATE EXTENSION IF NOT EXISTS vector;
