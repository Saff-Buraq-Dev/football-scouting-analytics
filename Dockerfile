# syntax=docker/dockerfile:1
# One image for the web app (API + built frontend) and the one-shot data bootstrap.
# It contains code only: football data is downloaded at runtime on the host (D004).

# --- Frontend build (platform-independent output, so it runs on the build machine's platform) ---
FROM --platform=$BUILDPLATFORM node:24-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST=/app/frontend/dist
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
# Editable install keeps the project layout (data/ next to src/) that the pipeline expects.
RUN pip install -e .
COPY deploy/bootstrap.sh deploy/bootstrap.sh
COPY --from=frontend /frontend/dist frontend/dist
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data \
    && chown app /app/data \
    && chmod +x deploy/bootstrap.sh
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["uvicorn", "football_platform.api.app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
