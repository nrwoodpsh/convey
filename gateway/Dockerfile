FROM python:3.11-slim
WORKDIR /app

# 공통 라이브러리 먼저 설치
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common

# 서비스 설치
COPY gateway/pyproject.toml /app/pyproject.toml
COPY gateway/app /app/app
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
