# Deployment Guide

## Development

```bash
# Clone the repository
git clone https://github.com/your-org/container-appstore.git
cd container-appstore

# Create the branch for v1.0.0
git checkout 1.0.0

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, configure one backend (Arcane or Portainer)

# Build and start
docker compose up -d --build

# View logs
docker compose logs -f appstore-api

# Open in browser
open http://localhost:8888
```

## Production

### With Arcane (Recommended)

1. Configure `.env.production`:

```bash
HOST=0.0.0.0
PORT=8888
CACHE_DIR=/app/cache
GIT_SYNC_INTERVAL=604800

# Arcane backend
ARCANE_BASE_URL=http://arcane:3552
ARCANE_API_KEY=arc_your_api_key_here
ARCANE_ENVIRONMENT_ID=0
ARCANE_VERIFY_SSL=false
ARCANE_MODE=real

# Active backend
ACTIVE_BACKEND=arcane

# Repositories (CasaOS AppStore)
REPOSITORIES=[{"name":"CasaOS AppStore","url":"https://github.com/IceWhaleTech/CasaOS-AppStore.git","branch":"main","enabled":true}]
```

2. Deploy:

```bash
docker compose --env-file .env.production up -d --build
```

### With Portainer

1. Configure `.env.production`:

```bash
PORTAINER_BASE_URL=https://portainer.example.com:9443
PORTAINER_API_KEY=ptr_your_api_key_here
PORTAINER_ENDPOINT_ID=3
PORTAINER_VERIFY_SSL=true

ACTIVE_BACKEND=portainer
```

2. Deploy:

```bash
docker compose --env-file .env.production up -d --build
```

## Docker Commands Reference

```bash
# Build and start
docker compose up -d --build

# Stop
docker compose down

# View logs
docker compose logs -f appstore-api

# Restart
docker compose restart appstore-api

# Rebuild without cache
docker compose build --no-cache appstore-api
docker compose up -d

# Clean up volumes (cache, DB)
docker compose down -v
```

## Health Check

```bash
curl http://localhost:8888/health
```

Response:
```json
{
  "status": "ok",
  "service": "AppStore Bridge API",
  "version": "1.0.0",
  "active_backend": "arcane",
  "portainer_connected": false,
  "arcane_connected": true,
  "apps_loaded": 42
}
```

## CI/CD (GitHub Actions)

The repository includes CI/CD workflows in `.github/workflows/`:

- **ci.yml** — Runs tests on push
- **docker-publish.yml** — Builds and pushes Docker image to GHCR on tagged releases

To create a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Changelog

### v1.0.0

- Added Arcane backend support (dual-backend with Portainer)
- Backend selector in Settings UI
- Arcane API client with mock mode
- New environment variables: `ARCANE_*`, `ACTIVE_BACKEND`
- Updated documentation

### v0.2.0

- Initial release with Portainer integration
- CasaOS AppStore repository support
- Mock mode for development
