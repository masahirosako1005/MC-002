FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    APP_DB_PATH=/app/data/community.db MEDIA_DIR=/app/data/media \
    SEED_ASSET_DIR=/app/seed-assets STATIC_DIR=/app/static \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: pip==26.2 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -c "import fastapi, PIL" \
    && groupadd --gid 10001 traveler \
    && useradd --uid 10001 --gid traveler --no-create-home traveler \
    && mkdir -p /app/data/media /app/seed-assets \
    && chown -R traveler:traveler /app/data
COPY backend/app ./app
COPY --from=frontend /build/dist ./static
USER 10001:10001
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-access-log", "--no-proxy-headers"]
