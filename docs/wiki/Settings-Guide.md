# Settings Guide

This comprehensive guide explains all settings in Container AppStore, including Mock Mode, Repository Management, Synchronization, and Cache Management.

## Overview

Settings in Container AppStore control:
- **Portainer Integration** (mock vs real mode)
- **App Repositories** (sources of container apps)
- **Synchronization** (how often repositories refresh)
- **Cache Management** (performance optimization)

All settings can be accessed through the web UI at the "Settings" page or via API endpoints.

## Portainer Settings

### What is Portainer Mode?

Container AppStore can operate in two modes:

#### Mock Mode (Testing/Development)
- **Ideal for**: Development and testing
- **Behavior**: Simulates Portainer responses without deploying actual containers
- **Data**: In-memory, not persisted
- **Use Case**: Test the UI and API without a real Portainer instance

#### Real Mode (Production)
- **Ideal for**: Real deployments
- **Requires**: Working Portainer instance with API key
- **Behavior**: Actually deploys containers to Portainer
- **Data**: Deployed to real Docker hosts

### Toggle Mock Mode

#### Via Web UI

1. Go to **Settings** → **Portainer Configuration**
2. Look for "Force Mock Mode" toggle
3. Switch between enabled (mock) and disabled (real)
4. Note: **App restart required** for changes to take effect fully

#### Via API

Check current mode:
```bash
curl http://localhost:8888/api/settings/portainer-mode
```

Response:
```json
{
  "current_mode": "mock",
  "force_mock_mode": true,
  "can_switch_to_real": false,
  "portainer_configured": false
}
```

Toggle mode:
```bash
curl -X POST http://localhost:8888/api/settings/portainer-mode/toggle
```

### View Portainer Configuration

```bash
curl http://localhost:8888/api/settings/portainer
```

Response:
```json
{
  "mode": "real",
  "base_url": "https://host.docker.internal:9443",
  "endpoint_id": 3,
  "is_configured": true,
  "api_key": "***",
  "read_only": true,
  "config_source": "env"
}
```

**Note**: Configuration is read-only via UI (managed via environment variables or docker-compose.yml)

## Repository Management

Repositories are sources of container applications. You can add multiple repositories and enable/disable them as needed.

### Default Repositories

The application comes with pre-configured repositories:
- **CasaOS AppStore** - Official CasaOS applications
- **LinuxServer** - LinuxServer Docker images
- **BigBear** - BigBear additional applications

### View Repositories

#### Via Web UI
1. Go to **Settings** → **App Repositories**
2. See list of all configured repositories

#### Via API

```bash
curl http://localhost:8888/api/repositories
```

Response:
```json
{
  "repositories": [
    {
      "id": 1,
      "name": "CasaOS AppStore",
      "url": "https://github.com/IceWhaleTech/CasaOS-AppStore.git",
      "branch": "main",
      "enabled": true,
      "priority": 100,
      "last_synced": "2024-02-22T10:30:45.123456"
    },
    {
      "id": 2,
      "name": "LinuxServer",
      "url": "https://github.com/WisdomSky/CasaOS-LinuxServer-AppStore.git",
      "branch": "main",
      "enabled": false,
      "priority": 90,
      "last_synced": null
    }
  ]
}
```

### Add a Repository

#### Via Web UI
1. Go to **Settings** → **App Repositories**
2. Fill in the form:
   - **Repository Name**: e.g., "My Apps"
   - **Git URL**: e.g., "https://github.com/username/my-apps.git"
   - **Branch**: e.g., "main" (default)
   - **Priority**: e.g., 100 (higher = more priority in search results)
3. Click **"Add Repository"**

#### Via API

```bash
curl -X POST http://localhost:8888/api/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Apps",
    "url": "https://github.com/username/my-apps.git",
    "branch": "main",
    "priority": 100,
    "enabled": true
  }'
```

### Enable/Disable Repository

Some repositories might have many apps not relevant to you. You can temporarily disable them.

#### Via Web UI
1. Find the repository in the list
2. Click the **"Enabled"** or **"Disabled"** button to toggle

#### Via API

```bash
# Disable repository
curl -X PUT http://localhost:8888/api/repositories/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Enable repository
curl -X PUT http://localhost:8888/api/repositories/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Delete Repository

#### Via Web UI
1. Find the repository in the list
2. Click the **"Delete"** button
3. Confirm deletion

#### Via API

```bash
curl -X DELETE http://localhost:8888/api/repositories/1
```

## Synchronization

Synchronization is the process of cloning/pulling repository data to get the latest apps.

### Automatic Synchronization

Automatic sync runs periodically based on `GIT_SYNC_INTERVAL` environment variable (default: 3600 seconds = 1 hour).

### Manual Synchronization

Sometimes you need to sync immediately without waiting for the scheduled sync.

#### Via Web UI
1. Go to **Settings** → **App Repositories**
2. Click **"Sync Now"** button on a repository
3. A spinner appears while syncing
4. Status updates when complete

#### Via API

```bash
# Sync specific repository
curl -X POST http://localhost:8888/api/repositories/1/sync

# Response
{
  "success": true,
  "message": "Repository synced successfully",
  "apps_loaded": 45,
  "timestamp": "2024-02-22T10:35:12.456789"
}
```

### Sync Status

View when repositories were last synced:

```bash
curl http://localhost:8888/status
```

Response:
```json
{
  "status": "healthy",
  "sync_status": {
    "repositories_synced": 3,
    "apps_loaded": 127,
    "last_sync": "2024-02-22T10:30:45.123456",
    "errors": []
  }
}
```

## Cache Management

Cache stores downloaded repository data locally to improve performance. Sometimes cache becomes stale, causing incorrect app states.

### View Cache Status

#### Via Web UI
1. Go to **Settings** → **Cache Management**
2. See cache information:
   - Cache Size (e.g., "125.5 MB")
   - Apps Loaded (e.g., "127 apps")
   - Last Sync time
   - Cache Path

#### Via API

```bash
curl http://localhost:8888/api/settings/cache/status
```

Response:
```json
{
  "initialized": true,
  "cache_dir": "/app/cache",
  "cache_size": "125.50 MB",
  "apps_loaded": 127,
  "last_sync": "2024-02-22T10:30:45.123456",
  "cache_path_exists": true
}
```

### Clear Cache

When cache becomes inconsistent or you want a fresh start, clear it and resync.

#### Via Web UI
1. Go to **Settings** → **Cache Management**
2. Click **"🗑️ Clear Cache & Resync"** button
3. Confirm the action
4. Wait for resync to complete
5. Apps list updates with fresh data

**Why Clear Cache?**
- After modifying parameters (ports, volumes, environment variables)
- When app listings seem incorrect
- When troubleshooting sync issues
- After adding new repositories

#### Via API

```bash
curl -X POST http://localhost:8888/api/settings/cache/clear
```

Response:
```json
{
  "success": true,
  "message": "Cache cleared and repositories resynced successfully",
  "cache_cleared": {
    "success": true,
    "deleted_repos": 3,
    "cache_size_before": "125.50 MB"
  },
  "repositories_resynced": {
    "repositories_synced": 3,
    "apps_loaded": 127,
    "errors": []
  },
  "timestamp": "2024-02-22T10:35:12.456789"
}
```

**Warning**: This operation:
- Removes all cached repository data
- Reclones repositories from Git
- May take several minutes for large repositories
- Requires internet connection

### Common Cache Issues

#### **Issue**: Apps show outdated information
**Solution**: Clear cache and resync

```bash
curl -X POST http://localhost:8888/api/settings/cache/clear
```

#### **Issue**: App parameters changed but not reflected
**Solution**: This is normal - Docker images are fixed, but you can use `env_overrides` when deploying

#### **Issue**: Cache directory full
**Solution**: Clear cache to free space

```bash
curl -X POST http://localhost:8888/api/settings/cache/clear
```

## Performance Tuning

### Adjust Sync Interval

Edit `docker-compose.yml`:
```yaml
GIT_SYNC_INTERVAL: 7200  # 2 hours instead of 1
```

Longer intervals = less CPU usage but potentially stale data

### Limit Repositories

Disable unnecessary repositories in Settings to:
- Reduce sync time
- Reduce cache size
- Improve search performance

### Optimize Search

Use filters in search queries:
```bash
# Slow - searches all apps
curl http://localhost:8888/apps

# Faster - filtered search
curl http://localhost:8888/apps?category=Backup&limit=20
```

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/settings/portainer` | GET | Get Portainer config |
| `/api/settings/portainer-mode` | GET | Get current mode |
| `/api/settings/portainer-mode/toggle` | POST | Toggle mock/real mode |
| `/api/settings/cache/status` | GET | Get cache info |
| `/api/settings/cache/clear` | POST | Clear cache & resync |
| `/api/repositories` | GET | List repositories |
| `/api/repositories` | POST | Add repository |
| `/api/repositories/{id}` | PUT | Update repository |
| `/api/repositories/{id}` | DELETE | Delete repository |
| `/api/repositories/{id}/sync` | POST | Sync repository |

## Next Steps

- [Portainer Setup](Portainer-Setup.md) - Configure Portainer integration
- [App Installation](App-Installation.md) - Deploy applications
- [Repository Management](Repository-Management.md) - Advanced repository topics
