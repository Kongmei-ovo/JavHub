FROM node:20-alpine AS frontend-builder

ARG VITE_APP_VERSION=dev
ENV VITE_APP_VERSION=${VITE_APP_VERSION}

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM python:3.11-slim

ARG VITE_APP_VERSION=dev

LABEL org.opencontainers.image.title="JavHub"
LABEL org.opencontainers.image.description="JavHub web UI and FastAPI backend"
LABEL org.opencontainers.image.version="${VITE_APP_VERSION}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx postgresql-client gzip \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ .
COPY config.yaml.example /app/config.yaml.example

COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/data /run/nginx \
    && rm -f /etc/nginx/sites-enabled/default

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/health', timeout=5).read()" || exit 1

CMD ["sh", "/usr/local/bin/docker-entrypoint.sh"]
