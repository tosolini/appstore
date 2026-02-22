# Stage 1: Build Vue 3 frontend
FROM node:20.11-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend dependencies  
COPY frontend/package.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/src ./src
COPY frontend/index.html ./index.html
COPY frontend/vite.config.js ./vite.config.js

# Build frontend
RUN npm run build

# Stage 2: Python runtime with FastAPI
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY src/ src/

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/dist /app/public

# Create cache and data directories
RUN mkdir -p cache data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CACHE_DIR=/app/cache
ENV DATABASE_URL=sqlite:////app/data/appstore.db

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

# Run FastAPI with SPA fallback
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8888"]
