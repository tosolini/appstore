# Container AppStore

A modern GUI application for discovering, managing, and deploying containerized applications via Portainer. Browse thousands of pre-configured apps from multiple repositories, deploy with one click, and manage your containers.

## ✨ Features

- 🎨 **Modern Web UI** - Beautiful, intuitive interface for browsing and deploying apps
- 🔍 **Smart Discovery** - Search, filter, and browse apps from multiple repositories
- 🚀 **One-Click Deploy** - Deploy apps to Portainer with custom configuration
- 📦 **App Repositories** - Support for multiple app sources (CasaOS, LinuxServer, custom repos)
- 🔄 **Automatic Sync** - Keep your app catalog up-to-date
- ⚙️ **Advanced Settings** - Customize environment variables, ports, volumes, and more
- 🎯 **Mock Mode** - Test and develop without a real Portainer instance (not fully functional)
- 💾 **Cache Management** - Optimize performance and free up space
- 📡 **REST API** - Full API access for automation and integration
- 🐳 **Docker-First** - Production-ready with docker-compose
- 🔐 **Portainer Integration** - Seamless integration with Portainer for deployment

## Quick Start (Docker Compose - Recommended)

```bash
# Clone repository
git clone https://github.com/tosolini/appstore.git
cd appstore

# Start with Docker Compose
docker compose up -d
```

Then open your browser:
- **Web UI**: http://localhost:8888 🎨
- **API Docs**: http://localhost:8888/docs 📝

That's it! Start discovering and deploying apps!

## Getting Started

### Via Web UI (Recommended for Most Users)

1. **Open the Dashboard**
   ```
   http://localhost:8888
   ```

2. **Browse Applications**
   - Explore all available apps from multiple repositories
   - Search by name or keyword
   - Filter by category (Backup, Media, Development, etc.)

3. **View App Details**
   - Click any app to see full details
   - Review port mappings, volumes, and environment variables
   - Read description and requirements

4. **Deploy an App**
   - Click "Deploy" on any app
   - Customize settings (optional):
     - Change container name
     - Override environment variables
     - Remap ports if needed
     - Change data volumes location
   - Click "Deploy" to start the application
   - Monitor deployment in real-time

5. **Manage Settings**
   - Add/remove app repositories
   - Toggle Mock mode for testing
   - Sync repositories manually
   - Clear cache when needed

⚠️  **pay attention, GUI is made for local use, do not expose it to the internet without proper security measures (authentication, HTTPS, firewall)**

### Via API (For Automation)

If you prefer to automate or integrate with other tools, a full REST API is available:

```bash
# Search for an app
curl http://localhost:8888/apps/search?q=syncthing

# Get app details
curl http://localhost:8888/apps/syncthing

# Deploy an app programmatically
curl -X POST http://localhost:8888/apps/syncthing/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stack_name": "my-syncthing",
    "portainer_endpoint_id": 3,
    "env_overrides": {"PUID": "1000"}
  }'
```

Full API documentation available at: http://localhost:8888/docs

## Screenshots & Features

### Dashboard
- Clean, organized interface showing available apps
- Search and filter capabilities
- Category navigation
- Status indicators for repositories

### App Details
- Complete app information with descriptions
- Port and volume configuration preview
- Environment variables reference
- Docker-compose content available

### Settings Panel
- **Repositories**: Add/remove/enable app sources
- **Portainer**: Configure Portainer connection
- **Mock Mode**: Test without real Portainer
- **Cache Management**: Clear cache and resync
- **Synchronization**: Manual and automatic sync

![Dashboard Screenshot](https://raw.githubusercontent.com/tosolini/appstore/main/docs/screenshots/dashboard.jpeg)

![App Detail Screenshot](https://raw.githubusercontent.com/tosolini/appstore/main/docs/screenshots/app-detail.jpeg)

![docker-compose screenshot](https://raw.githubusercontent.com/tosolini/appstore/main/docs/screenshots/docker-compose.jpeg)

![cache management screenshot](https://raw.githubusercontent.com/tosolini/appstore/main/docs/screenshots/cache.jpeg)


## Installation Options

### Option 1: Docker Compose (Recommended)

```bash
docker compose up -d
```
Access at: http://localhost:8888

### Option 2: Standalone Docker

```bash
docker run -p 8888:8888 \
  -e PORTAINER_BASE_URL=https://host.docker.internal:9443 \
  -e PORTAINER_API_KEY=your_key \
  container-appstore:latest
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8888
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOST` | 0.0.0.0 | Bind address |
| `PORT` | 8888 | Web UI port |
| `CACHE_DIR` | /tmp/container-appstore-cache | Repository cache location |
| `GIT_SYNC_INTERVAL` | 3600 | Repository sync interval (seconds) |
| `PORTAINER_BASE_URL` | - | Portainer URL (e.g., https://host.docker.internal:9443) |
| `PORTAINER_API_KEY` | - | Portainer API token |
| `PORTAINER_ENDPOINT_ID` | 1 | Portainer endpoint ID |
| `PORTAINER_VERIFY_SSL` | true | Verify SSL certificates |
| `MOCK_MODE` | false | Enable mock Portainer for testing |

### Example Configuration (docker-compose.yml)

```yaml
services:
  appstore:
    image: container-appstore:latest
    ports:
      - "8888:8888"
    environment:
      PORTAINER_BASE_URL: https://host.docker.internal:9443
      PORTAINER_API_KEY: your_api_key_here
      PORTAINER_ENDPOINT_ID: 3
      PORTAINER_VERIFY_SSL: "false"
      MOCK_MODE: "false"
    volumes:
      - appstore_cache:/app/cache
    restart: unless-stopped

volumes:
  appstore_cache:
```

## Using Container AppStore

### Common Workflows

#### 1. Browse and Deploy an App

**Via Web UI (Easiest):**
1. Open http://localhost:8888
2. Search for "Syncthing" or browse categories
3. Click on the app
4. Click "Deploy"
5. Enter stack name (e.g., "my-syncthing")
6. Click "Deploy" button
7. App is deployed to Portainer!

#### 2. Deploy with Custom Settings

**Via Web UI (Advanced):**
1. Click on app to view details
2. Scroll to "Advanced Settings" section
3. Customize:
   - **Environment Variables** (PUID, PGID, TZ, etc.)
   - **Port Mappings** (change if ports conflict)
   - **Volumes** (change data storage location)
4. Click "Deploy with Custom Settings"

#### 3. Add Your Own App Repository

**Via Settings → Repositories:**
1. Click "+ Add Repository"
2. Enter:
   - Repository name (e.g., "My Apps")
   - Git URL (https://github.com/username/apps.git)
   - Branch (e.g., main)
3. Click "Add"
4. Apps from your repository appear in search!

#### 4. Manage Portainer Connection

**Via Settings → Portainer Configuration:**
- View current Portainer connection status
- Toggle between Mock Mode (testing) and Real Mode (deployment)
- View endpoint ID
- See API key status

#### 5. Fix Cache Issues

**Via Settings → Cache Management:**
- View cache size and app count
- Click "Clear Cache & Resync" if apps seem outdated
- Wait for resync to complete
- Apps list refreshes automatically

## API Documentation

For automation and integration, Container AppStore provides a complete REST API.

### Full API available at:
- **Swagger UI**: http://localhost:8888/docs
- **ReDoc**: http://localhost:8888/redoc

### Quick API Examples

#### Search for Apps

```bash
curl http://localhost:8888/apps/search?q=syncthing
```

#### Get App Details

```bash
curl http://localhost:8888/apps/syncthing
```

#### Deploy Programmatically

```bash
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

#### Manage Repositories

```bash
# List repositories
curl http://localhost:8888/api/repositories

# Add repository
curl -X POST http://localhost:8888/api/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Apps",
    "url": "https://github.com/username/my-apps.git",
    "branch": "main"
  }'

# Manually sync repository
curl -X POST http://localhost:8888/api/repositories/1/sync
```

#### Cache Management

```bash
# Check cache status
curl http://localhost:8888/api/settings/cache/status

# Clear cache and resync
curl -X POST http://localhost:8888/api/settings/cache/clear
```

## Technologies Used

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Vue 3 + Vite
- **UI Framework**: Modern CSS3
- **Container**: Docker + Docker Compose
- **Integration**: Portainer REST API
- **Database**: SQLite (default)
- **Version Control**: Git

## Project Structure

```
appstore/
├── frontend/                     # Vue 3 web UI
│   ├── src/
│   │   ├── views/              # Pages (Home, AppDetail, Settings)
│   │   ├── components/         # Vue components
│   │   └── composables/        # Reusable logic
│   └── vite.config.js          # Vite build config
├── src/                         # Python FastAPI backend
│   ├── main.py                 # Main application
│   ├── models/                 # Pydantic data models
│   ├── parsers/                # Docker-compose parser
│   ├── git_sync/               # Repository sync logic
│   ├── portainer/              # Portainer API client
│   ├── db/                     # Database models
│   ├── security/               # Encryption utilities
│   └── api/                    # API routes
├── docs/
│   ├── wiki/                   # Full documentation
│   └── ENCRYPTION.md           # Encryption details
├── tests/                       # Unit tests
├── Dockerfile                   # Container image
├── docker-compose.yml           # Orchestration
├── requirements.txt             # Python deps
└── README.md                    # This file
```

## Documentation

Complete documentation available in the [Wiki](https://github.com/tosolini/appstore/wiki):

- **[Getting Started](docs/wiki/Getting-Started.md)** - Installation and first steps
- **[Portainer Setup](docs/wiki/Portainer-Setup.md)** - How to create API keys and configure Portainer
- **[Settings Guide](docs/wiki/Settings-Guide.md)** - Complete settings reference (mock mode, repositories, cache, sync)
- **[App Installation](docs/wiki/App-Installation.md)** - Deploy apps with custom configuration

## System Requirements

### Minimum
- Docker & Docker Compose
- 512MB RAM
- 1GB disk space

### Recommended
- Docker & Docker Compose
- 2GB RAM
- 10GB disk space (for app cache)
- Portainer CE/EE (for real deployments)

## Troubleshooting

### Web UI Not Loading

**Problem**: Cannot access http://localhost:8888

**Check**:
```bash
# Check if container is running
docker compose ps

# View logs
docker compose logs appstore-api

# Verify port is available
netstat -tuln | grep 8888
```

### Apps Not Appearing

**Problem**: Search returns no results

**Solutions**:
1. Verify internet connection (needed for cloning repositories)
2. Check cache: Settings → Cache Management → View status
3. Clear cache: Settings → Cache Management → "Clear Cache & Resync"
4. Check logs: `docker compose logs appstore-api`

### Portainer Connection Error

**Problem**: Cannot deploy (stuck in mock mode)

**Solutions**:
1. Verify Portainer is running: `docker ps | grep portainer`
2. Verify API key is correct in docker-compose.yml
3. Check SSL setting: `PORTAINER_VERIFY_SSL=false` for self-signed certificates
4. See [Portainer Setup Guide](docs/wiki/Portainer-Setup.md)

### Deployment Fails

**Problem**: App deployment to Portainer fails

**Check**:
1. Verify Portainer is in the "Real" mode (not Mock)
2. Check Portainer endpoint ID is correct
3. View deployment logs in Portainer UI
4. Ensure stack name doesn't already exist

### Poor Performance

**Solutions**:
- Increase `GIT_SYNC_INTERVAL` (e.g., 7200 for 2 hours)
- Disable unused repositories in Settings
- Clear cache: `docker compose exec appstore-api curl -X POST http://localhost:8888/api/settings/cache/clear`
- Reduce number of apps to display with `limit` parameter

## Performance & Scalability

### Single Instance
- Handles 1000+ apps
- ~100-200 concurrent users over REST API
- Auto-sync 3-5 repositories without issues

### For Large Deployments
- Deploy behind a reverse proxy (nginx, Traefik)
- Use PostgreSQL instead of SQLite
- Implement caching layer (Redis)
- Horizontal scaling with multiple instances

## Security Considerations

- Store API keys securely (never commit to git)
- Use `.env` files listed in `.gitignore`
- Enable `PORTAINER_VERIFY_SSL: "true"` in production
- Use HTTPS/SSL for web UI in production
- Regularly rotate Portainer API tokens
- Limit API access with firewall rules

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support & Issues

- 📖 Check the [Wiki](https://github.com/tosolini/appstore/wiki)
- 🐛 [Report bug](https://github.com/tosolini/appstore/issues)
- 💡 [Request feature](https://github.com/tosolini/appstore/issues)
- 💬 [Discussions](https://github.com/tosolini/appstore/discussions)

## Author

**Walter Tosolini** - [GitHub](https://github.com/tosolini) | [Website](https://tosolini.info)

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- [CasaOS](https://casaos.io) - For AppStore inspiration
- [Portainer](https://portainer.io) - Container management platform
- [LinuxServer.io](https://www.linuxserver.io/) - Docker images
- All contributors and users

---

⭐ If you find this project helpful, please give it a star on GitHub!
