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
    && apt-get install -y --no-install-recommends nginx postgresql-client gzip ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Bundle the current stable sing-box core. The release is resolved per target
# architecture while building, so deployed JavHub containers need no client.
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in amd64) sb_arch=amd64;; arm64) sb_arch=arm64;; *) echo "Unsupported sing-box architecture: $arch"; exit 1;; esac; \
    version="$(curl -fsSL https://api.github.com/repos/SagerNet/sing-box/releases/latest | sed -n 's/.*"tag_name": "v\([^"]*\)".*/\1/p' | head -1)"; \
    test -n "$version"; \
    curl -fsSL "https://github.com/SagerNet/sing-box/releases/download/v${version}/sing-box-${version}-linux-${sb_arch}.tar.gz" -o /tmp/sing-box.tgz; \
    tar -xzf /tmp/sing-box.tgz -C /tmp; \
    install -m 0755 "/tmp/sing-box-${version}-linux-${sb_arch}/sing-box" /usr/local/bin/sing-box; \
    rm -rf /tmp/sing-box*

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
