# App Installation Guide

This guide explains how to discover and install applications from Container AppStore.

## Overview

Container AppStore provides a unified interface to discover and deploy container applications to your Docker host via Portainer. Installation involves:

1. **Discovering** the app in the catalog
2. **Viewing** app details and configuration
3. **Customizing** the deployment (optional)
4. **Installing** to your Docker host
5. **Monitoring** the deployment

## Prerequisites

- Container AppStore running and accessible
- Portainer installed and configured (for real deployments)
- Docker host available for deployment
- For real deployments: Portainer API key configured

## Discovering Apps

### Via Web UI

1. Open Container AppStore in your browser: `http://localhost:8888`
2. Browse the home page to see featured apps
3. Use **search bar** to find specific apps
4. Filter by **category** using the sidebar

### Via API

#### List All Apps

```bash
curl http://localhost:8888/apps
```

Response includes basic app info with pagination.

#### Filter by Category

```bash
# Available categories: Backup, Download, Development, etc.
curl http://localhost:8888/apps?category=Backup

# Common categories
curl http://localhost:8888/apps?category=Download
curl http://localhost:8888/apps?category=Development
curl http://localhost:8888/apps?category=Media
```

#### Search for Specific App

```bash
# Search for an app by name or keyword
curl http://localhost:8888/apps/search?q=syncthing

# Response
{
  "apps": [
    {
      "app_id": "syncthing",
      "title": "Syncthing",
      "description": "File synchronization application",
      "category": "Backup",
      "icon": "https://...",
      "repository": "CasaOS"
    }
  ]
}
```

#### Limit Results

```bash
# Get only first 10 results
curl http://localhost:8888/apps?limit=10
```

## Viewing App Details

Once you find an app, view its full details including docker-compose configuration.

### Via Web UI

1. Click on an app in the listing
2. View detailed information:
   - Description and features
   - Icon and screenshots (if available)
   - Port mappings
   - Volume bindings
   - Environment variables
   - Docker-compose configuration

### Via API

```bash
curl http://localhost:8888/apps/syncthing
```

Response:
```json
{
  "app_id": "syncthing",
  "title": "Syncthing",
  "description": "Open Source Continuous File Synchronization",
  "icon": "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/syncthing.png",
  "developer": "Syncthing",
  "category": "Backup",
  "port_map": "8384",
  "services": {
    "syncthing": {
      "image": "linuxserver/syncthing:1.29.7",
      "container_name": "syncthing",
      "ports": [
        "8384:8384",
        "22000:22000/tcp",
        "22000:22000/udp",
        "21027:21027/udp"
      ],
      "volumes": [
        "/path/to/config:/config",
        "/path/to/data:/sync"
      ],
      "environment": {
        "PUID": "1000",
        "PGID": "1000",
        "TZ": "Etc/UTC"
      }
    }
  },
  "compose_content": "version: '3.8'\nservices:\n  syncthing:\n    image: linuxserver/syncthing:1.29.7\n    ..."
}
```

## Understanding Configuration

### Port Mappings

Ports shown in the app details indicate how the container is exposed:

```
"8384:8384"      → Host port 8384 → Container port 8384
"22000:22000"    → Host port 22000 → Container port 22000
```

**Before installing**: Make sure these ports are available on your host. If they're in use, you'll need to override them during installation.

### Volume Bindings

Volumes specify where data is stored:

```
"/path/to/config:/config"  → Host path → Container path
"/path/to/data:/sync"      → Host path → Container path
```

**Default paths** may not be suitable for your setup. You can override them during installation.

### Environment Variables

Configuration values passed to the container:

```
PUID: 1000      → User ID inside container
PGID: 1000      → Group ID inside container
TZ: Etc/UTC     → Timezone
```

These can be customized when deploying.

## Installing / Deploying an App

### Simple Installation (Via Web UI)

1. Browse to an app and click **"Install"** or **"Deploy"**
2. Provide a **stack name** (e.g., "my-syncthing")
3. Choose **deployment mode**:
   - **Mock Mode**: Simulates deployment (testing)
   - **Real Mode**: Actually deploys to Portainer
4. Click **"Deploy"**
5. Wait for confirmation

### Advanced Installation (Via Web UI)

Before deploying, customize the app:

1. Click on the app to view details
2. In the configuration section:
   - **Edit port mappings**: If default ports conflict
   - **Edit volume paths**: Change where data is stored
   - **Override environment variables**: Customize behavior
3. Click **"Deploy with Custom Settings"**
4. The customized docker-compose will be deployed

### Installation Via API

#### Basic Deployment

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "my-syncthing",
    "portainer_endpoint_id": 3
  }'
```

Response:
```json
{
  "success": true,
  "stack_id": 42,
  "message": "Stack deployed successfully",
  "stack_name": "my-syncthing",
  "portainer_response": {
    "Id": 42,
    "Name": "my-syncthing",
    "Status": "active",
    "SwarmId": "",
    "StackFileVersion": 1
  }
}
```

#### Deployment with Custom Configuration

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "my-syncthing",
    "portainer_endpoint_id": 3,
    "env_overrides": {
      "PUID": "5000",
      "PGID": "5000",
      "TZ": "Europe/Rome"
    },
    "port_overrides": {
      "8384": "9384",
      "22000": "32000"
    },
    "volume_overrides": {
      "/path/to/config": "/docker/syncthing/config",
      "/path/to/data": "/mnt/data/syncthing"
    }
  }'
```

**Note**: 
- `env_overrides`: Custom environment variables
- `port_overrides`: Map different host ports (if defaults are in use)
- `volume_overrides`: Change where data is stored on the host

## Monitoring Deployment

### Via Portainer Web UI

1. Open Portainer: `https://localhost:9443`
2. Go to **Stacks**
3. Look for your stack (e.g., "my-syncthing")
4. View:
   - Stack status
   - Container status
   - Logs
   - Resource usage

### Via Container AppStore API

```bash
# View deployment status
curl http://localhost:8888/status
```

### Via Docker Compose

```bash
# List running containers
docker ps | grep syncthing

# View logs
docker logs my-syncthing

# Inspect container
docker inspect my-syncthing
```

## Accessing Your App

Once deployed and running:

1. **Find the port**: Check app details for the main service port (e.g., 8384 for Syncthing)
2. **Access via browser**: `http://localhost:8384` (or your custom port)
3. **Configure**: Follow the app's setup wizard or documentation

## Common Deployment Scenarios

### Scenario 1: Default Installation

Deploy with all default settings:

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "syncthing-1",
    "portainer_endpoint_id": 3
  }'
```

Access at: `http://localhost:8384`

### Scenario 2: Custom Port (Port Conflict)

Port 8384 is already in use, deploy to 9384:

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "syncthing-2",
    "portainer_endpoint_id": 3,
    "port_overrides": {
      "8384": "9384"
    }
  }'
```

Access at: `http://localhost:9384`

### Scenario 3: Custom Data Location

Store data on external drive:

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "syncthing-external",
    "portainer_endpoint_id": 3,
    "volume_overrides": {
      "/path/to/data": "/mnt/external-drive/syncthing"
    }
  }'
```

### Scenario 4: Custom User & Timezone

Run with different user ID and timezone:

```bash
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "syncthing-custom",
    "portainer_endpoint_id": 3,
    "env_overrides": {
      "PUID": "33",
      "PGID": "33",
      "TZ": "Europe/Rome"
    }
  }'
```

## Troubleshooting

### Port Already in Use

**Problem**: Deployment fails because the port is already in use

**Solution**: Use `port_overrides` to map to a different port:
```bash
"port_overrides": {"8384": "9384"}
```

### Container Won't Start

**Problem**: Container appears in Portainer but is stopped

**Check**:
1. View container logs in Portainer
2. Ensure volume paths exist and are writable
3. Verify environment variable values

### Can't Access App

**Problem**: App seems to be running but browser shows connection refused

**Check**:
1. Verify correct port number
2. Check firewall/security settings
3. Ensure container is actually running: `docker ps`

### deployment to Wrong Endpoint

**Problem**: App deployed to wrong Docker host

**Solution**: Verify `portainer_endpoint_id` is correct:
- Check Portainer UI under Environments/Endpoints
- Use correct ID in deploy request

## Next Steps

- [Settings Guide](Settings-Guide.md) - Manage repositories and cache
- [Portainer Setup](Portainer-Setup.md) - Configure Portainer integration
- Explore more apps in the AppStore catalog
