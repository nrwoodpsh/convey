FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/publishing/pyproject.toml /app/pyproject.toml
COPY services/publishing/app /app/app
RUN pip install --no-cache-dir .
# API(상태 조회) + content.approved 소비(업로드) 동거
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
