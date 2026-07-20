FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/issue-detector/pyproject.toml /app/pyproject.toml
COPY services/issue-detector/app /app/app
RUN pip install --no-cache-dir .
# 워커(스트림 집계) + 조회 API 동거
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
