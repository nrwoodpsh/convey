FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/market-feed/pyproject.toml /app/pyproject.toml
COPY services/market-feed/app /app/app
RUN pip install --no-cache-dir .
# 워커(HTTP 없음) — 외부 연동 → Kafka 발행
CMD ["python", "-m", "app.worker"]
