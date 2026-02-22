# Wiki - Container AppStore Documentation

Welcome to the Container AppStore documentation. Here you'll find comprehensive guides for getting started, configuration, and usage.

## Getting Started

- **[Getting Started Guide](Getting-Started.md)** - Installation and first steps
  - Prerequisites and installation methods
  - Accessing the dashboard
  - Browsing available apps
  - Quick Portainer setup

## Core Guides

### [Portainer Setup Guide](Portainer-Setup.md)
Learn how to integrate Container AppStore with Portainer for app deployment.
- Creating API tokens in Portainer
- Finding your endpoint ID
- Configuring SSL verification
- Testing the connection
- Troubleshooting connection issues

### [Settings Guide](Settings-Guide.md)
Complete reference for all Container AppStore settings.
- **Portainer Settings**: Mock mode vs Real mode
- **Repository Management**: Add, enable, disable repositories
- **Synchronization**: Manual and automatic sync
- **Cache Management**: View, clear, and optimize cache
- API reference for all settings endpoints

### [App Installation Guide](App-Installation.md)
Step-by-step guide for discovering and installing applications.
- Discovering apps via UI and API
- Viewing app details and configuration
- Understanding port mappings, volumes, and environment variables
- Deploying apps with custom settings
- Monitoring deployments
- Common scenarios and troubleshooting

## FAQ & Troubleshooting

| Issue | Guide |
|-------|-------|
| Can't connect to Portainer | [Portainer Setup - Troubleshooting](Portainer-Setup.md#troubleshooting) |
| Apps not loading | [Settings Guide - Cache Issues](Settings-Guide.md#common-cache-issues) |
| Port conflicts during deployment | [App Installation - Scenario 2](App-Installation.md#scenario-2-custom-port-port-conflict) |
| Wrong endpoint being used | [App Installation - Troubleshooting](App-Installation.md#deployment-to-wrong-endpoint) |
| SSL certificate errors | [Portainer Setup - SSL Errors](Portainer-Setup.md#ssl-certificate-errors) |

## Quick Reference

### API Endpoints

**Settings**
```bash
GET    /api/settings/portainer          # Get Portainer config
GET    /api/settings/portainer-mode     # Get current mode
POST   /api/settings/portainer-mode/toggle  # Toggle mock/real
GET    /api/settings/cache/status       # Get cache info
POST   /api/settings/cache/clear        # Clear and resync
```

**Repositories**
```bash
GET    /api/repositories                # List repositories
POST   /api/repositories                # Add repository
PUT    /api/repositories/{id}           # Update repository
DELETE /api/repositories/{id}           # Delete repository
POST   /api/repositories/{id}/sync      # Manually sync
```

**Apps**
```bash
GET    /apps                            # List apps
GET    /apps/search?q=query             # Search apps
GET    /apps/{app_id}                   # Get app details
POST   /apps/{app_id}/deploy            # Deploy app
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOST` | 0.0.0.0 | Bind address |
| `PORT` | 8888 | API port |
| `CACHE_DIR` | /tmp/container-appstore-cache | Cache location |
| `GIT_SYNC_INTERVAL` | 3600 | Sync interval (seconds) |
| `PORTAINER_BASE_URL` | - | Portainer URL |
| `PORTAINER_API_KEY` | - | Portainer API key |
| `PORTAINER_ENDPOINT_ID` | 1 | Portainer endpoint ID |
| `PORTAINER_VERIFY_SSL` | true | Verify SSL certs |
| `MOCK_MODE` | false | Enable mock mode |
| `DEBUG_MODE` | false | Enable debug logs |

## Development & Contributing

Interested in contributing to Container AppStore? Check out:
- GitHub Repository: [Add your repo link]
- Issues: Report bugs or request features
- Pull Requests: Submit improvements

## Support

- 📚 Read the relevant guide above
- 🐛 Open an issue on GitHub
- 💬 Check existing issues for solutions

## Navigation

| | |
|---|---|
| ← [Back to Main README](../../README.md) | [Getting Started Guide →](Getting-Started.md) |
