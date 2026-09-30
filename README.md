# Container AppStore Bridge

**v1.1.4** — A Docker app store with dual-backend support, resilient GitHub **and Docker Hub** app importing, full backup/restore, a tabbed imports management page, a "New apps" page with version snapshots, and a premium dark-first UI.

Browse and deploy containerized applications from CasaOS-compatible app stores (or any custom Git repository) to your chosen container management platform.

![Dashboard](docs/screenshots/dashboard.jpeg)

## Features

- Browse apps from multiple Git repositories (CasaOS AppStore, LinuxServer, BigBear, custom)
- Import standalone GitHub repositories and auto-generate app pages from `docker-compose.yml` or `Dockerfile`
- Import Docker Hub images (`hub.docker.com/r/{namespace}/{repo}`, official `hub.docker.com/_/{repo}`) — reuses an embedded compose snippet from the image description when available, otherwise generates a single-service stack with ports inferred from the image config
- Smart duplicate detection: URLs are canonicalized so `owner/repo`, `owner/repo.git/`, trailing slashes and case variants all resolve to the same import (GitHub and Docker Hub each have their own canonical form)
- Imports page (`/imports`) with **GitHub / Docker Hub tabs**, **search and pagination** for long catalogs, plus resync/delete/export workflows
- Floating **Back to top** button on Browse and New apps once the list gets long
- **New apps page** (`/new`) — shows apps added since the previous version, with a **NEW** badge on browse cards and a nav counter
- **Full backup export** — complete app snapshot (compose content, images, metadata) as a single archive; covers **both GitHub and Docker Hub imports**
- **One-click restore** from a backup without contacting GitHub or Docker Hub (no rate-limit issues)
- **Full Reset to Default** button in Settings — restores the bundled default catalog
- Fresh installs are **auto-populated from the bundled backup** (no GitHub calls on first boot)
- **Redeploys auto-merge newer bundled backups** — when a new image ships a new `github-imports-backup.tar.gz`, the catalog updates on boot (new apps added, existing updated, manual imports never deleted)
- Per-app **Resync button** on imported app detail pages (re-imports the repository from GitHub or the image from Docker Hub)
- Import error details modal showing exactly why a repository was skipped
- Import debug badges showing GitHub API, git fallback, Dockerfile fallback, or Docker Hub (description compose / generated image) strategy
- Architecture compatibility detection and warnings for container images that do not support the current host
- App favicon bundle (`favicon.ico`, SVG/PNG variants, apple-touch-icon, webmanifest) with a consistent branded mark
- Search, filter by category, paginated browsing
- Deploy to **Portainer** or **Arcane** with a single click
- Favorite apps for quick access
- Dynamic deploy form (env vars, volume bind mounts)
- **Premium dark-first UI** — glassmorphism design system with ambient glows, custom typography (Bricolage Grotesque + Manrope), glowing cards and micro-interactions
- Backend configuration (Portainer/Arcane) grouped into clean **tabs** in Settings
- **Broken-image fallback** — app icons/screenshots that 404 on the remote host automatically show a placeholder
- **SPA refresh support** — refreshing any route (`/settings`, `/app/...`, `/imports`, `/imports/github`, `/imports/dockerhub`) no longer returns a 404; deep links work directly
- Light/dark theme with improved screenshot lightbox controls
- Mock mode for development without real infrastructure
- Runs entirely in Docker

## Screenshots

| Dashboard | App Detail |
|-----------|------------|
| ![Dashboard](docs/screenshots/dashboard.jpeg) | ![App Detail](docs/screenshots/app-detail.jpeg) |

| Docker Compose | Cache Management |
|----------------|------------------|
| ![Docker Compose](docs/screenshots/docker-compose.jpeg) | ![Cache Management](docs/screenshots/cache.jpeg) |
| Deploy container | Check arch |
|----------------|------------------|
| ![Deploy container](docs/screenshots/deploy.jpeg) | ![Check arch](docs/screenshots/check-arch.jpeg) |
| GitHub Import |  Settings |
|---------------|----------|
| ![GitHub Import](docs/screenshots/github-import.jpeg) | ![Settings](docs/screenshots/settings.jpeg) |


Portainer API token setup: ![Portainer API Token](docs/screenshots/portainer_apitoken.jpeg)

## Quick Start

```bash
# Clone and start
git clone https://github.com/tosolini/appstore.git
cd appstore
cp .env.example .env

# Edit .env with your Arcane or Portainer details
# Then start:
docker compose up -d --build

# Open http://localhost:8888
```

On first boot the app auto-populates the catalog from the bundled default imports backup — no manual GitHub import needed.

## Common Commands (Makefile)

A `Makefile` wraps the most common Docker Compose tasks:

```bash
make up        # Start containers in background
make down      # Stop and remove containers
make build     # Build the image
make rebuild   # Build → down → up (full restart with fresh image)
make restart   # Restart containers
make logs      # Follow API logs
make shell     # Interactive shell in the API container
make ps        # Container status
make help      # List all commands
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

See [docs/wiki/Portainer-Setup.md](docs/wiki/Portainer-Setup.md).

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
# Development (build from source)
docker compose up -d --build

# Production (prebuilt image from GitHub Container Registry)
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

The production compose pulls `ghcr.io/tosolini/appstore:latest` (built automatically by CI on push to `main`/`master`) instead of building locally. Override the image via `APPSTORE_IMAGE` (e.g. `APPSTORE_IMAGE=ghcr.io/tosolini/appstore:v1.1.4`).

## Imports & Backup

The app can import any public GitHub repository that ships a `docker-compose.yml` or a `Dockerfile`, as well as any public Docker Hub image — persisting the generated app directly into the catalog. Both sources share the same catalog, snapshots ("New apps"), and full backup/restore.

> **Tip:** set `GITHUB_TOKEN` in `.env` to avoid GitHub API rate-limit `403`s during imports. Without a token the importer falls back to shallow `git clone` / HTML metadata, which still works but is slower and less reliable for large catalogs. Docker Hub imports need no token.

- **Import** — paste one URL per line (Settings or the matching Imports tab), or upload an exported list. URLs are canonicalized, so importing the same repo twice — even with a `.git` suffix or different case — updates the existing entry instead of duplicating it.
- **Resync** — every imported app has a Resync button on its detail page (after the Import row) to re-import the repository or image on demand.
- **Search & paginate** — both Imports tabs filter live by name/repo/URL and paginate long catalogs (20 per page).
- **Backup** — *Export Full Backup* downloads `github-imports-backup.tar.gz`, a compressed snapshot with compose content, images and metadata covering **both sources**. Restoring it requires **no GitHub or Docker Hub access**, so catalogs with 100+ apps restore instantly without hitting API rate limits. Legacy `.json` backups are still accepted on restore.
- **Reset** — *Full Reset to Default* in Settings wipes current imports and restores the bundled default set.
- **Auto-update on redeploy** — when a new image ships a newer bundled backup, startup merges it automatically (adds new apps, updates existing ones, never deletes manual imports or flags everything as NEW).

The GitHub importer:

- falls back to a shallow `git clone` when GitHub API metadata or tree listing is rate-limited
- accepts non-standard compose filenames such as `docker-compose.dev.yaml` and similar Docker YAML variants, plus any `*.yml`/`*.yaml` inside a `docker/` directory
- accepts `Dockerfile` variants (`Dockerfile.alpine`, `Dockerfile.custom`, `*.dockerfile`, …) anywhere in the repo, with an explicit fallback search inside the repo's `docker/` folder
- inspects container image manifests when possible so imported apps can warn when the current host architecture is not published by one or more referenced images
- records import debug metadata so you can tell whether an app came from the GitHub API, git fallback, docker-dir fallback, or Dockerfile fallback path

The Docker Hub importer (`hub.docker.com/r/{namespace}/{repo}`, official images via `hub.docker.com/_/{repo}`):

- reads public metadata from the Docker Hub API (description, categories, star/pull counts)
- reuses a compose snippet embedded in the image's full description when one parses as a compose file (e.g. multi-service stacks documented on the Hub page)
- otherwise generates a single-service compose for the image, inferring ports from the image config `ExposedPorts` and architectures from the registry manifest
- records `dockerhub-description-compose` / `dockerhub-generated` import strategies shown as Docker Hub badges in the UI

## Architecture

```
frontend/          ← Vue 3 SPA (Vite)
  ├── src/views/   ← Pages (Home, NewApps, AppDetail, Settings, Imports + GitHubImports/DockerHubImports tabs)
  ├── src/components/ ← Reusable components (DeployForm, AppCard, BackToTop)
  ├── src/directives/ ← Global directives (e.g. broken-image fallback)
  ├── src/styles/   ← Design system (theme.css, CSS variables, light/dark)
  └── public/       ← PWA icons (favicon, apple-touch-icon, webmanifest)
src/               ← Python FastAPI backend
  ├── main.py      ← API routes, backend dispatch, imports/backup/reset, SPA fallback
  ├── portainer/   ← Portainer client (kept for compat)
  ├── arcane/      ← Arcane client
  ├── github_import/ ← GitHub importer + metadata enrichment + URL canonicalization
  ├── dockerhub_import/ ← Docker Hub importer (Hub API metadata, compose extraction, registry inspection)
  ├── parsers/     ← Docker Compose parser
  ├── git_sync/    ← Repository sync
  ├── db/          ← SQLite + SQLAlchemy
  ├── models/      ← Pydantic models
  └── security/    ← Encryption (Fernet)
docs/              ← User documentation + screenshots
```

## API

- `GET /health` — Health check
- `GET /apps` — List apps
- `GET /apps/{id}` — App detail
- `POST /apps/{id}/deploy` — Deploy to active backend
- `GET /api/imports/github` — List imported GitHub apps
- `POST /api/imports/github` — Import GitHub repositories into the app catalog
- `GET /api/imports/github/export?format=json|urls|full` — Export imported apps (JSON list, URL list, or full backup)
- `POST /api/imports/github/restore` — Restore a full backup (multipart file upload, no GitHub calls)
- `POST /api/imports/github/reset` — Reset imports to the bundled default set
- `POST /api/imports/github/{id}/resync` — Refresh one imported GitHub app
- `POST /api/imports/github/by-app/{app_id}/resync` — Refresh one imported GitHub app by app_id (used by the detail page)
- `POST /api/imports/github/snapshot` — Record the catalog baseline for a frontend version
- `GET /api/imports/github/new` — Apps added since the previous version
- `GET /api/imports/github/new-ids` — IDs of new apps (for NEW badges)
- `DELETE /api/imports/github/{id}` — Delete one imported GitHub app
- `GET /api/imports/dockerhub` — List imported Docker Hub apps
- `POST /api/imports/dockerhub` — Import Docker Hub image pages into the app catalog
- `POST /api/imports/dockerhub/{id}/resync` — Refresh one imported Docker Hub app
- `POST /api/imports/dockerhub/by-app/{app_id}/resync` — Refresh one imported Docker Hub app by app_id (used by the detail page)
- `DELETE /api/imports/dockerhub/{id}` — Delete one imported Docker Hub app
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

### Docker Hub image import

You can paste Docker Hub page URLs in the Docker Hub tab of the Imports page, or call the API directly:

```bash
curl -X POST http://localhost:8888/api/imports/dockerhub \
  -H 'Content-Type: application/json' \
  -d '{
    "repositories": [
      "https://hub.docker.com/r/msdeluise/plant-it-server",
      "https://hub.docker.com/_/nginx"
    ]
  }'
```

If the image description documents a compose stack, it is reused as-is; otherwise a single-service stack is generated for the image (`latest` tag) with ports detected from the image itself.

## Author
Walter Tosolini https://www.tosolini.info


## License

MIT — see [LICENSE](LICENSE).