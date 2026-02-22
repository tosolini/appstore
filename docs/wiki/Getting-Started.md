# Getting Started with Container AppStore

Welcome to Container AppStore! This guide will help you get started with the application quickly.

## Prerequisites

- Docker and Docker Compose (or `docker compose` command)
- Python 3.11+ (for local development)
- Git
- Portainer (optional, for deployment features)

## Installation

### Option 1: Docker Compose (Recommended)

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/tosolini/appstore.git
cd appstore

# Copy environment template
cp .env.example .env

# Start the service
docker compose up -d
```

The API will be available at `http://localhost:8888`
Swagger UI: `http://localhost:8888/docs`

### Option 2: Local Development

If you want to run it locally for development:

```bash
# Clone repository
git clone https://github.com/tosolini/appstore.git
cd appstore

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run the application
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8888
```

## First Steps

### 1. Access the Dashboard

Open your browser and navigate to:
- **API Documentation**: http://localhost:8888/docs
- **Alternative Documentation**: http://localhost:8888/redoc

### 2. Check Status

```bash
curl http://localhost:8888/health
curl http://localhost:8888/status
```

### 3. Browse Available Apps

```bash
# List all apps
curl http://localhost:8888/apps

# List apps from a specific category
curl http://localhost:8888/apps?category=Backup

# Search for an app
curl http://localhost:8888/apps/search?q=syncthing
```

### 4. Configure Portainer (Optional)

To enable deployment features, configure Portainer:

1. Set environment variables in `docker-compose.yml`:
   ```yaml
   PORTAINER_BASE_URL: https://host.docker.internal:9443
   PORTAINER_API_KEY: your_api_key_here
   PORTAINER_ENDPOINT_ID: 3
   PORTAINER_VERIFY_SSL: "false"  # For self-signed certificates
   ```

2. See [Portainer Setup Guide](Portainer-Setup.md) for detailed instructions

### 5. Manage Repositories

Add, remove, or update app repositories through the Settings API:

```bash
# View current repositories
curl http://localhost:8888/api/repositories

# Add a new repository
curl -X POST http://localhost:8888/api/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Apps",
    "url": "https://github.com/username/my-apps.git",
    "branch": "main",
    "priority": 100
  }'
```

## Next Steps

- [Portainer Setup Guide](Portainer-Setup.md) - Configure Portainer integration
- [Settings Guide](Settings-Guide.md) - Understand all settings and options
- [App Installation Guide](App-Installation.md) - Deploy apps using the AppStore
- [Repository Management](Repository-Management.md) - Add and manage app sources

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs appstore-api

# Verify environment variables
docker compose config | grep PORTAINER
```

### Apps not loading
- Ensure you have internet access for repository cloning
- Check that Git repositories are accessible
- See [Settings Guide](Settings-Guide.md) for cache management

### Health check failing
- Verify the port 8888 is accessible
- Check container logs: `docker compose logs appstore-api`

## Support

For more help:
- Open an issue on GitHub
- Check the [FAQ](FAQ.md)
- Review existing [Settings Guide](Settings-Guide.md)
