# Container AppStore Bridge

**v1.0.7** — A Docker app store with dual-backend support, resilient GitHub app importing, and dedicated imports management.

Browse and deploy containerized applications from CasaOS-compatible app stores (or any custom Git repository) to your chosen container management platform.

## Features

- Browse apps from multiple Git repositories (CasaOS AppStore, LinuxServer, BigBear, custom)
- Import standalone GitHub repositories and auto-generate app pages from `docker-compose.yml` or `Dockerfile`
- Export imported GitHub sources as a distributable URL list or JSON bundle
- Dedicated GitHub Imports page for resync/delete/export workflows
- Import debug badges showing GitHub API, git fallback, or Dockerfile fallback strategy
- Architecture compatibility detection and warnings for container images that do not support the current host
- Search, filter by category, paginated browsing
- Deploy to **Portainer** or **Arcane** with a single click
- Favorite apps for quick access
- Dynamic deploy form (env vars, volume bind mounts)
- Light/dark theme with improved screenshot lightbox controls
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
  ├── arcane/      ← Arcane client
  ├── github_import/ ← GitHub importer + metadata enrichment
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
- `GET /api/imports/github` — List imported GitHub apps
- `POST /api/imports/github` — Import GitHub repositories into the app catalog
- `GET /api/imports/github/export` — Export imported GitHub repositories as JSON or URL list
- `POST /api/imports/github/{id}/resync` — Refresh one imported GitHub app
- `DELETE /api/imports/github/{id}` — Delete one imported GitHub app
- `GET /api/settings/backend` — Backend status
- `POST /api/settings/backend/select` — Switch backend

Full API docs available at `/docs` (Swagger) when the server is running.

### GitHub repo import

You can paste GitHub repository URLs in the Settings page, then manage large import lists from the dedicated Imports page, or call the API directly:

```bash
curl -X POST http://localhost:8888/api/imports/github \
  -H 'Content-Type: application/json' \
  -d '{
    "repositories": [
      "https://github.com/mostafa-wahied/portracker",
      "https://github.com/gamosoft/NoteDiscovery"
    ]
  }'
```

Imported repositories are persisted and merged into the normal app list, so they appear in browse/search/detail pages like any other app.

The importer also:

- falls back to a shallow `git clone` when GitHub API metadata or tree listing is rate-limited
- accepts non-standard compose filenames such as `docker-compose.dev.yaml` and similar Docker YAML variants
- inspects container image manifests when possible so imported apps can warn when the current host architecture is not published by one or more referenced images
- records import debug metadata so you can tell whether an app came from the GitHub API, git fallback, or Dockerfile fallback path

## License

MIT — see [LICENSE](LICENSE).
