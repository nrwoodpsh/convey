FROM python:3.11-slim
WORKDIR /app
COPY libs/common /tmp/common
RUN pip install --no-cache-dir /tmp/common
COPY services/admin/pyproject.toml /app/pyproject.toml
COPY services/admin/app /app/app
RUN pip install --no-cache-dir .
COPY services/admin/alembic.ini /app/alembic.ini
COPY services/admin/alembic /app/alembic
EXPOSE 8000
# 마이그레이션 적용 → 시드 → 기동 (스키마 SSOT = Alembic)
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
