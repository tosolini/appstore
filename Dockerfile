# Stage 1: Build Vue 3 frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend dependencies  
COPY frontend/package.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/index.html ./index.html
COPY frontend/vite.config.js ./vite.config.js

# Build frontend
RUN npm run build

# Stage 2: Python runtime with FastAPI
FROM python:3.11.15-slim

WORKDIR /app

# Install system dependencies and apply security patches
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies.
# setuptools is uninstalled afterwards to drop its vendored wheel/jaraco
# packages (flagged by Trivy). This is safe: no runtime dependency uses
# pkg_resources/setuptools — verified by importing all app modules and
# booting the server (health check passes) without it.
RUN pip install --no-cache-dir -r requirements.txt \
    && (pip uninstall -y setuptools 2>/dev/null || true)

# Copy app code
COPY src/ src/

# Bundled default GitHub imports backup (used for fresh-install seed + full reset).
# Compressed tar.gz (the backend still accepts a legacy .json if provided).
COPY github-imports-backup.tar.gz ./github-imports-backup.tar.gz

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/dist /app/public

# Create cache and data directories
RUN mkdir -p cache data

# Non-root user (least privilege)
RUN useradd --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CACHE_DIR=/app/cache
ENV DATABASE_URL=sqlite:////app/data/appstore.db
ENV HOME=/home/appuser

# Copy entrypoint (fixes bind-mounted volume ownership, then drops privileges)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

USER appuser

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8888"]
