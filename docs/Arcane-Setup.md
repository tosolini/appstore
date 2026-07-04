# Arcane Integration Setup

This guide walks through configuring the AppStore Bridge to use **Arcane** as the deployment backend.

## Prerequisites

- A running [Arcane](https://getarcane.app) instance (main server or agent)
- An Arcane API key with deploy permissions
- The Arcane environment ID (usually `0`)

## Step 1: Get Your Arcane API Key

1. Open your Arcane instance in a browser (e.g., `http://arcane:3552`)
2. Go to **Settings → API Keys**
3. Click **Add API Key**
4. Enter a name (e.g., "AppStore Bridge")
5. Optional: set an expiration date
6. Click **Create API Key**
7. **Copy the key immediately** — it will not be shown again

## Step 2: Configure Environment Variables

Edit your `.env` file or `docker-compose.yml`:

```yaml
# Required Arcane configuration
ARCANE_BASE_URL=http://arcane:3552
ARCANE_API_KEY=arc_your_api_key_here
ARCANE_ENVIRONMENT_ID=0

# Optional
ARCANE_VERIFY_SSL=false        # Set true in production with HTTPS
ARCANE_MODE=auto               # auto | real | mock

# Select Arcane as active backend (or "auto" to detect)
ACTIVE_BACKEND=arcane
```

## Step 3: Deploy the AppStore

```bash
docker compose up -d --build
```

Check the logs to verify Arcane connection:

```bash
docker compose logs appstore-api | grep Arcane
```

Expected output:
```
Arcane client (REAL) initialized and validated
Active backend: arcane
```

## Step 4: Verify in UI

1. Open `http://localhost:8888/settings`
2. You should see **Arcane** highlighted as the active backend with status **REAL**
3. Browse apps and click **Deploy to Arcane** on any app

## Arcane API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/environments` | Validate connection |
| `POST /api/environments/{id}/projects` | Create and deploy a project |
| `GET /api/environments/{id}/projects` | List projects |
| `POST /api/environments/{id}/projects/{pid}/destroy` | Destroy a project |

## Troubleshooting

### Connection Refused

```
ARCANE_BASE_URL=http://arcane:3552
```

Verify the URL is reachable from inside the Docker container:

```bash
docker exec -it container-appstore-api curl -s http://arcane:3552/api/environments
```

### Invalid API Key

```
ERROR: Arcane connection validation failed: 401
```

Regenerate the API key in Arcane **Settings → API Keys** and update `ARCANE_API_KEY`.

### Wrong Environment ID

```
ERROR: 404 on /api/environments/1/projects
```

List available environments:

```bash
curl -s http://arcane:3552/api/environments \
  -H "X-Api-Key: your-key"
```

Set `ARCANE_ENVIRONMENT_ID` to the correct `id` from the response.

## Switching Between Backends

In the UI, go to **Settings → Deployment Backend** and click on the desired backend.

Or set via env var:

```yaml
ACTIVE_BACKEND=arcane   # or portainer, auto
```

Restart to apply:
```bash
docker compose restart appstore-api
```
