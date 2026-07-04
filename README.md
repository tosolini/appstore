# Container AppStore Bridge

**v1.0.0** — A Docker app store with dual-backend support: **Portainer** and **Arcane**.

Browse and deploy containerized applications from CasaOS-compatible app stores (or any custom Git repository) to your chosen container management platform.

## Features

- Browse apps from multiple Git repositories (CasaOS AppStore, LinuxServer, BigBear, custom)
- Search, filter by category, paginated browsing
- Deploy to **Portainer** or **Arcane** with a single click
- Favorite apps for quick access
- Dynamic deploy form (env vars, volume bind mounts)
- Light/dark theme
- Mock mode for development without real infrastructure
- Runs entirely in Docker

## Quick Start

```bash
# Clone and start
git clone https://github.com/your-org/container-appstore.git
cd container-appstore
cp .env.example .env

# Edit .env with your Arcane or Portainer details
# Then start:
docker compose up -d --build

# Open http://localhost:8888
```

## Backend Selection

The app supports two deployment backends. Configure via env vars:

| Backend | Env Vars |
|---------|----------|
| **Arcane** | `ARCANE_BASE_URL`, `ARCANE_API_KEY`, `ARCANE_ENVIRONMENT_ID` |
| **Portainer** | `PORTAINER_BASE_URL`, `PORTAINER_API_KEY`, `PORTAINER_ENDPOINT_ID` |

Set `ACTIVE_BACKEND=auto` to auto-detect, or `arcane`/`portainer` to force.

### Arcane Setup

See [docs/Arcane-Setup.md](docs/Arcane-Setup.md).

### Portainer Setup

See [docs/Portainer-Setup.md](docs/wiki/Portainer-Setup.md).

## Persistent Data

Data persists across restarts and image updates via bind mounts and volumes:

| Mount | Path in container | Stores |
|-------|-------------------|--------|
| `./data/` | `/app/data` | SQLite database (settings, repos, deploy logs, encryption key, favorites) |
| `appstore_cache` | `/app/cache` | Cloned Git repositories (app metadata) |

The database file lives at `./data/appstore.db` on your host — you can inspect or back it up directly.

To reset everything:
```bash
docker compose down -v
rm -rf data/
```

## Deployment

```bash
# Development
docker compose up -d --build

# Production (with custom env)
docker compose --env-file .env.production up -d
```

## Architecture

```
frontend/          ← Vue 3 SPA (Vite)
src/               ← Python FastAPI backend
  ├── main.py      ← API routes, backend dispatch
  ├── portainer/   ← Portainer client (kept for compat)
  ├── arcane/      ← Arcane client (new in v1.0.0)
  ├── parsers/     ← Docker Compose parser
  ├── git_sync/    ← Repository sync
  ├── db/          ← SQLite + SQLAlchemy
  ├── models/      ← Pydantic models
  └── security/    ← Encryption (Fernet)
docs/              ← User documentation
```

## API

- `GET /health` — Health check
- `GET /apps` — List apps
- `GET /apps/{id}` — App detail
- `POST /apps/{id}/deploy` — Deploy to active backend
- `GET /api/settings/backend` — Backend status
- `POST /api/settings/backend/select` — Switch backend

Full API docs available at `/docs` (Swagger) when the server is running.

## License

MIT — see [LICENSE](LICENSE).
