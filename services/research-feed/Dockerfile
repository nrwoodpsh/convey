FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/research-feed/pyproject.toml /app/pyproject.toml
COPY services/research-feed/app /app/app
RUN pip install --no-cache-dir .
# 워커(HTTP 없음) — 리서치 소스 수집 → Kafka 발행
CMD ["python", "-m", "app.worker"]
