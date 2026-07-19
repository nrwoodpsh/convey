FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/news-feed/pyproject.toml /app/pyproject.toml
COPY services/news-feed/app /app/app
RUN pip install --no-cache-dir .
# 워커(HTTP 없음) — 뉴스·RSS 수집 + 종목·사건 태깅 → Kafka 발행
CMD ["python", "-m", "app.worker"]
