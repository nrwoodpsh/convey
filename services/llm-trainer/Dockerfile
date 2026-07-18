# torch 등 대용량 의존성 포함 — 빌드 시간·이미지 큼. GPU가 필요하면
# nvidia/cuda 베이스 이미지 + CUDA torch 휠로 교체할 것.
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/llm-trainer/pyproject.toml /app/pyproject.toml
COPY services/llm-trainer/app /app/app
RUN pip install --no-cache-dir .
# 워커(HTTP 서버 아님) — Kafka 잡 소비
CMD ["python", "-m", "app.worker"]
