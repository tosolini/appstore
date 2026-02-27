# Portainer Setup Guide

This guide explains how to set up Portainer integration with Container AppStore, including how to generate an API key.

## What is Portainer?

Portainer is a lightweight management UI for Docker. It allows you to manage containers, images, networks, and volumes through a web interface, or via their REST API.

The Container AppStore can deploy applications to Portainer automatically through its REST API.

## Prerequisites

- Portainer running and accessible (e.g., `https://localhost:9443`)
- Admin or appropriate permissions in Portainer

## Step 1: Access Portainer

1. Open your browser and navigate to your Portainer instance
2. Default: `https://localhost:9443` (if running locally)
3. Log in with your credentials

## Step 2: Create an API Token

### Via Portainer Web UI

1. Click on your **user profile** (top-right corner)
2. Select **"My Account"** or **"User Settings"**
3. Scroll down to **"API tokens"** section
4. Click **"Generate an API token"** or **"Add API token"**
5. Enter a name for the token (e.g., "AppStore Integration")
6. Click **"Generate"**

![Portainer API Key Generation](https://imgur.com/example.png)

7. **Copy the token immediately** - you won't be able to see it again!
8. Store it securely (e.g., in a password manager)

### Example Token Format
```
ptr_eKkTnro5Q57fTUxcCtj7CZRiap/TV2uJ376PH0VI174=
```

## Step 3: Find Your Endpoint ID

Portainer uses "endpoints" to refer to Docker hosts. You need to identify which endpoint ID to use.

### Find Endpoint ID

1. In Portainer, go to **Settings** → **Environments** (or **Endpoints**)
2. Look at your Docker environment
3. The endpoint ID is displayed in the list (usually `1`, `2`, or `3` for Docker Desktop)

On **Docker Desktop**:
- Click on the endpoint
- The URL might look like: `https://localhost:9443/#/endpoints/3`
- Your endpoint ID is `3` (the number at the end)

You can also query via APIn (example, change host and api key):
```bash
curl -k -X GET "https://localhost:9443/api/endpoints" \
  -H "X-API-Key: ptr_eKkTnro5Q57fTUxcCtj7CZRiap/TV2uJ376PH0VI174="
```

Look for the `"Id"` field of your endpoint.

## Step 4: Configure Container AppStore

### For Docker Compose

Edit your `docker-compose.yml`:

```yaml
services:
  appstore-api:
    environment:
      # Portainer Configuration
      PORTAINER_BASE_URL: https://host.docker.internal:9443 #or your ip:port
      PORTAINER_API_KEY: ptr_eKkTnro5Q57fTUxcCtj7CZRiap/TV2uJ376PH0VI174= #change to your api key
      PORTAINER_ENDPOINT_ID: 3
      PORTAINER_VERIFY_SSL: "false"  # For self-signed certificates
      MOCK_MODE: "false"
```

**Important Notes:**
- Use `host.docker.internal` on macOS/Windows or `172.17.0.1` on Linux
- Replace with your actual API key
- Set `PORTAINER_VERIFY_SSL: "false"` if using self-signed certificates (development only)

### For Local Development (.env file)

```
PORTAINER_BASE_URL=https://localhost:9443
PORTAINER_API_KEY=YOUR_API_KEY_HERE
PORTAINER_ENDPOINT_ID=3
PORTAINER_VERIFY_SSL=false
MOCK_MODE=false
```

## Step 5: Verify Connection

### Via API

```bash
# Check Portainer configuration
curl http://localhost:8888/api/settings/portainer

# Check Portainer mode (mock or real)
curl http://localhost:8888/api/settings/portainer-mode

# Expected response with REAL mode:
{
  "current_mode": "real",
  "force_mock_mode": false,
  "can_switch_to_real": true,
  "portainer_configured": true
}
```

### Via Docker Logs

```bash
docker compose logs appstore-api | grep -i portainer
```

Expected output:
```
INFO:src.main:✓ SSL verification DISABLED for Portainer (dev mode)
INFO:src.main:✓ Connected to Portainer successfully
INFO:src.main:Portainer client (REAL) initialized and validated
```

## Step 6: Deploy Your First App

Once connected, you can deploy apps from AppStore directly to Portainer:

```bash
# Deploy Syncthing to Portainer
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "my-syncthing",
    "portainer_endpoint_id": 3,
    "env_overrides": {
      "PUID": "1000",
      "PGID": "1000"
    }
  }'
```

The stack will be created in Portainer and you can monitor it through the Portainer UI.

## Troubleshooting

### "Connection refused" error

**Problem:** `Connection refused` when trying to connect to Portainer

**Solutions:**
- Verify Portainer is running: `docker ps | grep portainer`
- Check if using correct URL with `host.docker.internal` on macOS/Windows
- On Linux, use `172.17.0.1` instead of `localhost`
- If running Portainer outside Docker, use the actual IP address

### SSL Certificate errors

**Problem:** `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`

**Solutions:**
- Set `PORTAINER_VERIFY_SSL: "false"` for self-signed certificates
- Use valid SSL certificates in production
- Update `PORTAINER_BASE_URL` to match certificate hostname

### Invalid API Key

**Problem:** `401 Unauthorized` or `403 Forbidden`

**Solutions:**
- Verify API key is correct and hasn't expired
- Check for trailing spaces in the key
- Generate a new API token in Portainer

### Wrong Endpoint ID

**Problem:** Stack deploys to wrong Docker host or fails

**Solutions:**
- Verify endpoint ID in Portainer settings
- List endpoints via API to confirm ID
- Test with a known working endpoint ID

## Advanced Configuration

### Production Setup

For production with valid SSL certificates:

```yaml
PORTAINER_BASE_URL: https://portainer.example.com:9443
PORTAINER_API_KEY: your_secure_api_key
PORTAINER_ENDPOINT_ID: 1
PORTAINER_VERIFY_SSL: "true"
MOCK_MODE: "false"
```

### Multiple Endpoints

To deploy to different Portainer endpoints, specify the endpoint ID in the deploy request:

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "syncthing-prod",
    "portainer_endpoint_id": 2  # Different endpoint
  }'
```

### Mock Mode (Testing)

To test without a real Portainer instance:

```yaml
MOCK_MODE: "true"
```

This will simulate Portainer responses without actually deploying anything.

## Security Best Practices

1. **Never commit API keys** to version control
2. Use `.env` files (listed in `.gitignore`)
3. Rotate API tokens regularly
4. Use different tokens for different environments (dev, staging, prod)
5. Monitor Portainer for unauthorized access
6. Use strong API key permissions

## Next Steps

- [Settings Guide](Settings-Guide.md) - Learn about all available settings
- [App Installation Guide](App-Installation.md) - Deploy applications
- [Repository Management](Repository-Management.md) - Add custom app repositories
