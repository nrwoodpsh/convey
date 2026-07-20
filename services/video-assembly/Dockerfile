# ffmpeg(합성) + fonts-nanum(한글 자막·단위 렌더) 포함
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-nanum \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/video-assembly/pyproject.toml /app/pyproject.toml
COPY services/video-assembly/app /app/app
RUN pip install --no-cache-dir .
# 워커(HTTP 없음) — 정확 렌더 + ffmpeg 합성
CMD ["python", "-m", "app.worker"]
