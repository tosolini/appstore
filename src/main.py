import os
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import json
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models import App, DeployRequest, RepositoryCreate, PortainerConfigRequest
from src.git_sync import GitSync
from src.portainer import PortainerClient
from src.portainer.mock import MockPortainerClient
from src.db import init_db, get_db
from src.db.models import Repository as RepositoryModel, PortainerConfig
from src.parsers.compose_schema import ComposeSchema
from src.security import get_encryption_manager


# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App FastAPI
app = FastAPI(
    title="Container AppStore API",
    description="API bridge for managing and deploying container apps via Portainer",
    version="0.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
git_sync: GitSync = None
portainer_client: PortainerClient = None
scheduler: BackgroundScheduler = None


def load_config_repositories() -> list:
    """Load repository configuration from DB"""
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        repos = db.query(RepositoryModel).filter(
            RepositoryModel.enabled == True
        ).order_by(RepositoryModel.priority.desc()).all()
        db.close()
        return repos
    except Exception as e:
        logger.error(f"Error loading repositories from DB: {e}")
        # Fallback: load from env
        repos_json = os.getenv('REPOSITORIES', '[]')
        try:
            repos_data = json.loads(repos_json)
            # Returns dicts, not ORM models (will be handled by init_repositories)
            return repos_data
        except Exception as e2:
            logger.error(f"Error parsing REPOSITORIES env: {e2}")
            return []


def init_repositories():
    """Populate DB with repositories from env on first startup"""
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        
        # If there are already repos in DB, update base fields from env (e.g. branch/url)
        count = db.query(RepositoryModel).count()
        if count > 0:
            repos_json = os.getenv('REPOSITORIES', '[]')
            try:
                repos_data = json.loads(repos_json)
            except Exception as e:
                logger.error(f"Error parsing REPOSITORIES env: {e}")
                db.close()
                return

            updates = 0
            for repo_data in repos_data:
                name = repo_data.get('name')
                if not name:
                    continue
                repo = db.query(RepositoryModel).filter(RepositoryModel.name == name).first()
                if not repo:
                    continue

                new_branch = repo_data.get('branch')
                new_url = repo_data.get('url')
                if new_branch and repo.branch != new_branch:
                    repo.branch = new_branch
                    updates += 1
                if new_url and repo.url != new_url:
                    repo.url = new_url
                    updates += 1

            if updates > 0:
                db.commit()
                logger.info(f"Updated {updates} repository fields from env")
            else:
                logger.info(f"Database already has {count} repositories (no env updates applied)")

            db.close()
            return
        
        # Read from env
        repos_json = os.getenv('REPOSITORIES', '[]')
        try:
            repos_data = json.loads(repos_json)
        except Exception as e:
            logger.error(f"Error parsing REPOSITORIES env: {e}")
            db.close()
            return
        
        # Add to DB
        for idx, repo_data in enumerate(repos_data):
            repo = RepositoryModel(
                name=repo_data.get('name'),
                url=repo_data.get('url'),
                branch=repo_data.get('branch', 'main'),
                enabled=repo_data.get('enabled', True),
                priority=100 - idx  # Sort by env order
            )
            db.add(repo)
        
        db.commit()
        logger.info(f"Initialized {len(repos_data)} repositories in database")
        db.close()
    except Exception as e:
        logger.error(f"Error initializing repositories: {e}")


def init_sync():
    """Periodic synchronization task"""
    global git_sync
    if git_sync:
        repositories = load_config_repositories()
        result = git_sync.sync_all(repositories)
        logger.info(f"Sync task executed: {result}")


@app.on_event("startup")
async def startup_event():
    """Startup: initialize components and scheduler"""
    global git_sync, portainer_client, scheduler
    
    logger.info("Starting AppStore Bridge API...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize repositories in DB from env (if not already present)
    init_repositories()
    
    # Git Sync
    cache_dir = os.getenv('CACHE_DIR', '/tmp/container-appstore-cache')
    git_sync = GitSync(cache_dir)
    logger.info(f"GitSync initialized with cache dir: {cache_dir}")
    
    # Portainer client (mock or real)
    # Logic: if PORTAINER_MODE=mock or if forced from DB, use mock
    # Otherwise try to connect to real Portainer
    
    portainer_mode_env = os.getenv('PORTAINER_MODE', 'auto')  # mock | real | auto (default)
    portainer_url = os.getenv('PORTAINER_BASE_URL')
    portainer_key = os.getenv('PORTAINER_API_KEY')
    portainer_endpoint_id = 1
    force_mock = False
    
    logger.info(f"=== Portainer Configuration Debug ===")
    logger.info(f"PORTAINER_MODE env: {portainer_mode_env}")
    logger.info(f"PORTAINER_BASE_URL: {portainer_url}")
    logger.info(f"PORTAINER_API_KEY: {'***' if portainer_key else 'NOT SET'}")
    logger.info(f"PORTAINER_ENDPOINT_ID: {os.getenv('PORTAINER_ENDPOINT_ID', 'default')}")
    
    # Check if DB has a forced preference
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        config = db.query(PortainerConfig).first()
        db.close()
        
        if config:
            force_mock = config.force_mock_mode
            logger.info(f"force_mock_mode from DB: {force_mock}")
        else:
            logger.info("No PortainerConfig in DB, using defaults")
    except Exception as e:
        logger.warning(f"Could not load Portainer config from DB: {e}")
    
    endpoint_id_env = os.getenv('PORTAINER_ENDPOINT_ID')
    if endpoint_id_env:
        try:
            portainer_endpoint_id = int(endpoint_id_env)
        except ValueError:
            logger.warning("Invalid PORTAINER_ENDPOINT_ID, using default 1")
    
    # Decide whether to use mock or real
    should_use_mock = (
        portainer_mode_env == 'mock' or  # Explicitly mock
        force_mock or  # Forced by DB toggle
        not portainer_url or  # No URL configured
        not portainer_key  # No API key configured
    )
    
    logger.info(f"=== Mock Mode Decision ===")
    logger.info(f"portainer_mode_env == 'mock': {portainer_mode_env == 'mock'}")
    logger.info(f"force_mock from DB: {force_mock}")
    logger.info(f"portainer_url missing: {not portainer_url}")
    logger.info(f"portainer_key missing: {not portainer_key}")
    logger.info(f"should_use_mock: {should_use_mock}")
    
    if should_use_mock:
        portainer_client = MockPortainerClient()
        logger.info("Portainer client (MOCK mode) initialized")
    else:
        # Try to connect to real Portainer
        portainer_client = PortainerClient(portainer_url, portainer_key)
        if portainer_client.validate_connection():
            logger.info("Portainer client (REAL) initialized and validated")
        else:
            logger.warning("Portainer client validation failed - falling back to mock mode")
            portainer_client = MockPortainerClient()
    
    # Scheduler
    scheduler = BackgroundScheduler()
    sync_interval = int(os.getenv('GIT_SYNC_INTERVAL', '3600'))
    scheduler.add_job(init_sync, 'interval', seconds=sync_interval)
    scheduler.start()
    logger.info(f"Sync scheduler started (interval: {sync_interval}s)")
    
    # Initial sync
    init_sync()
    
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown: clean up resources"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
    logger.info("AppStore Bridge API stopped")


# Health endpoints
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    
    portainer_ok = True
    if portainer_client:
        portainer_ok = portainer_client.validate_connection()
    
    return {
        "status": "ok" if portainer_ok else "degraded",
        "service": "AppStore Bridge API",
        "portainer_connected": portainer_ok,
        "apps_loaded": len(git_sync.get_all_apps()) if git_sync else 0
    }


@app.get("/status")
async def sync_status() -> dict:
    """Synchronization status"""
    
    if not git_sync:
        return {"error": "AppStore not initialized"}
    
    all_apps = git_sync.get_all_apps()
    repos = set(a.repository_source for a in all_apps.values()) if all_apps else set()
    
    return {
        "last_sync": git_sync.last_sync,
        "apps_loaded": len(all_apps),
        "repositories_synced": len(repos),
        "healthy": len(all_apps) > 0
    }


# App endpoints
@app.get("/apps")
async def list_apps(
    category: Optional[str] = Query(None),
    repository: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)) -> dict:
    """
    List apps with optional filters
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    apps = git_sync.get_all_apps()
    
    # Filter
    filtered = list(apps.values())
    
    if category:
        filtered = [a for a in filtered if a.category and a.category.lower() == category.lower()]
    
    if repository:
        filtered = [a for a in filtered if a.repository_source.lower() == repository.lower()]
    
    # Paginate
    total = len(filtered)
    results = filtered[offset:offset + limit]
    
    # Return summary (without compose content for performance)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "apps": [
            {
                "app_id": a.app_id,
                "title": a.title,
                "description": a.description,
                "icon": a.icon,
                "category": a.category,
                "repository_source": a.repository_source,
                "tags": a.tags
            }
            for a in results
        ]
    }


@app.get("/api/categories")
async def get_categories() -> dict:
    """
    Get all available categories with app count per category
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    apps = git_sync.get_all_apps()
    
    # Collect unique categories with count
    categories_dict = {}
    for app in apps.values():
        if app.category:
            cat = app.category
            categories_dict[cat] = categories_dict.get(cat, 0) + 1
    
    # Sort alphabetically
    sorted_categories = sorted(categories_dict.items())
    
    return {
        "total": len(sorted_categories),
        "categories": [
            {
                "name": cat,
                "count": count
            }
            for cat, count in sorted_categories
        ]
    }


@app.get("/apps/search")
async def search_apps(q: str = Query(..., min_length=1, max_length=200)) -> dict:
    """
    Search apps by title/description
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    apps = git_sync.get_all_apps()
    q_lower = q.lower()
    
    # Simple FTS: match on title, description, tags
    results = [
        a for a in apps.values()
        if (q_lower in a.title.lower() or 
            q_lower in a.description.lower() or
            any(q_lower in tag.lower() for tag in a.tags))
    ]
    
    return {
        "query": q,
        "results_count": len(results),
        "apps": [
            {
                "app_id": a.app_id,
                "title": a.title,
                "description": a.description,
                "icon": a.icon,
                "category": a.category,
                "repository_source": a.repository_source
            }
            for a in results[:50]  # Limit 50 search results
        ]
    }


@app.get("/apps/{app_id}")
async def get_app_detail(app_id: str) -> dict:
    """
    Complete app details (includes compose)
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return {
        "app_id": app.app_id,
        "title": app.title,
        "description": app.description,
        "icon": app.icon,
        "developer": app.developer,
        "category": app.category,
        "port_map": app.port_map,
        "index": app.index,
        "main_service": app.main_service,
        "screenshot_links": app.screenshot_links,
        "thumbnail": app.thumbnail,
        "repository_source": app.repository_source,
        "architectures": app.architectures,
        "tags": app.tags,
        "compose_content": app.compose_content,
        "services": {
            name: {
                "container_name": svc.container_name,
                "image": svc.image,
                "ports": svc.ports,
                "volumes": svc.volumes,
                "environment": svc.environment
            }
            for name, svc in app.services.items()
        }
    }


@app.get("/apps/{app_id}/schema")
async def get_app_schema(app_id: str) -> dict:
    """
    Schema of environment parameters that can be customized
    Useful for frontend form generation
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Parse schema
    schema = ComposeSchema.extract_schema(app.compose_content)
    volumes = ComposeSchema.extract_volumes(app.compose_content)
    
    return {
        "app_id": app_id,
        "parameters": [p.to_dict() for p in schema],
        "volumes": [v.to_dict() for v in volumes]
    }


@app.post("/apps/{app_id}/deploy-mock")
async def deploy_app_mock(app_id: str, request: DeployRequest) -> dict:
    """
    Mock deploy (for testing)
    Does not send to Portainer, only tracks in-memory
    """
    
    if not isinstance(portainer_client, MockPortainerClient):
        return await deploy_app(app_id, request)
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    request.app_id = app_id
    
    # Deploy via mock
    response = portainer_client.deploy_stack(
        stack_name=request.stack_name,
        endpoint_id=request.portainer_endpoint_id,
        compose_content=app.compose_content,
        env_overrides=request.env_overrides,
        volume_overrides=request.volume_overrides,
        namespace=request.portainer_namespace
    )
    
    return response.model_dump()


@app.get("/api/repositories")
async def list_repositories(db: Session = Depends(get_db)) -> dict:
    """List all repositories"""
    repos = db.query(RepositoryModel).order_by(RepositoryModel.priority.desc()).all()
    return {
        "total": len(repos),
        "repositories": [
            {
                "id": r.id,
                "name": r.name,
                "url": r.url,
                "branch": r.branch,
                "enabled": r.enabled,
                "priority": r.priority,
                "last_synced": r.last_synced.isoformat() if r.last_synced else None
            }
            for r in repos
        ]
    }


@app.post("/api/repositories")
async def create_repository(
    repo_data: RepositoryCreate,
    db: Session = Depends(get_db)
) -> dict:
    """Create new repository accepting JSON body"""
    
    # Validation
    if not repo_data.name or not repo_data.url:
        raise HTTPException(status_code=400, detail="name and url are required")
    
    if not repo_data.url.startswith('http'):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # Check for duplicate
    existing = db.query(RepositoryModel).filter(RepositoryModel.name == repo_data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Repository '{repo_data.name}' already exists")
    
    try:
        repo = RepositoryModel(
            name=repo_data.name,
            url=repo_data.url,
            branch=repo_data.branch,
            enabled=True,
            priority=repo_data.priority
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        
        logger.info(f"Repository created: {repo_data.name}")
        
        return {
            "id": repo.id,
            "name": repo.name,
            "url": repo.url,
            "branch": repo.branch,
            "priority": repo.priority,
            "enabled": repo.enabled,
            "message": "Repository created"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating repository: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.put("/api/repositories/{repo_id}")
async def update_repository(
    repo_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """Update repository (enabled, priority)"""
    
    # Parse body
    import json
    body = await request.body()
    data = json.loads(body)
    enabled = data.get('enabled')
    priority = data.get('priority')
    
    repo = db.query(RepositoryModel).filter(RepositoryModel.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if enabled is not None:
        repo.enabled = enabled
    if priority is not None:
        repo.priority = priority
    
    db.commit()
    db.refresh(repo)
    
    logger.info(f"Repository updated: {repo.name} - enabled={repo.enabled}")
    
    return {
        "id": repo.id,
        "name": repo.name,
        "url": repo.url,
        "branch": repo.branch,
        "enabled": repo.enabled,
        "priority": repo.priority,
        "last_synced": repo.last_synced.isoformat() if repo.last_synced else None
    }


@app.delete("/api/repositories/{repo_id}")
async def delete_repository(repo_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete repository"""
    
    repo = db.query(RepositoryModel).filter(RepositoryModel.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    name = repo.name
    db.delete(repo)
    db.commit()
    
    logger.info(f"Repository deleted: {name}")
    
    return {"message": f"Repository '{name}' deleted"}


@app.post("/api/repositories/{repo_id}/sync")
async def sync_repository(repo_id: int, db: Session = Depends(get_db)) -> dict:
    """Force sync of a specific repository"""
    
    global git_sync
    
    repo = db.query(RepositoryModel).filter(RepositoryModel.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    # Refresh repository state from database to get latest enabled status
    db.refresh(repo)
    
    if not repo.enabled:
        raise HTTPException(status_code=400, detail="Repository is disabled")
    
    # Sync
    success = git_sync.clone_or_update(repo)
    
    if success:
        repo.last_synced = datetime.utcnow()
        db.commit()
        
        # Scan apps
        apps_dir = Path(git_sync.cache_dir) / repo.name / "Apps"
        if apps_dir.exists():
            from src.parsers import AppsDirectory
            apps_found = AppsDirectory.scan_apps(str(apps_dir), repo.name)
            git_sync.apps.update(apps_found)
            logger.info(f"Synced {len(apps_found)} apps from {repo.name}")
        
        return {"status": "success", "message": f"Repository '{repo.name}' synced"}
    else:
        return {"status": "error", "message": f"Failed to sync repository '{repo.name}'"}


@app.post("/apps/{app_id}/deploy")
async def deploy_app(app_id: str, request: DeployRequest) -> dict:
    """
    Deploy app to Portainer
    """
    
    if not portainer_client:
        raise HTTPException(status_code=503, detail="Portainer client not configured")
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Override request app_id with the one in URL
    request.app_id = app_id
    
    # Use env-configured endpoint ID
    endpoint_id = os.getenv('PORTAINER_ENDPOINT_ID')
    if endpoint_id:
        try:
            endpoint_id = int(endpoint_id)
        except ValueError:
            endpoint_id = request.portainer_endpoint_id or 1
    else:
        endpoint_id = request.portainer_endpoint_id or 1
    
    # Deploy via Portainer
    response = portainer_client.deploy_stack(
        stack_name=request.stack_name,
        endpoint_id=endpoint_id,
        compose_content=app.compose_content,
        env_overrides=request.env_overrides,
        volume_overrides=request.volume_overrides,
        namespace=request.portainer_namespace
    )
    
    return response.model_dump()


@app.get("/api/settings/portainer")
async def get_portainer_config() -> dict:
    """Get Portainer configuration from env (API key masked)"""
    
    base_url = os.getenv('PORTAINER_BASE_URL')
    api_key = os.getenv('PORTAINER_API_KEY')
    endpoint_id = os.getenv('PORTAINER_ENDPOINT_ID')
    
    try:
        endpoint_id_value = int(endpoint_id) if endpoint_id else 1
    except ValueError:
        endpoint_id_value = 1
    
    is_mock = isinstance(portainer_client, MockPortainerClient)
    
    return {
        "mode": "mock" if is_mock else "real",
        "base_url": base_url or "",
        "endpoint_id": endpoint_id_value,
        "is_configured": bool(base_url and api_key),
        "last_validated": None,
        "api_key": "***" if api_key else None,
        "read_only": True,
        "config_source": "env"
    }


@app.post("/api/settings/portainer")
async def set_portainer_config(
    request: PortainerConfigRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Portainer configuration managed via env (docker-compose)"""
    raise HTTPException(
        status_code=403,
        detail="Portainer configuration is managed via docker-compose.yml env vars. Update PORTAINER_BASE_URL/API_KEY and restart."
    )


@app.get("/api/settings/portainer-mode")
async def get_portainer_mode(db: Session = Depends(get_db)) -> dict:
    """Get current Portainer mode (mock or real)"""
    global portainer_client
    
    try:
        config = db.query(PortainerConfig).first()
        
        base_url = os.getenv('PORTAINER_BASE_URL')
        api_key = os.getenv('PORTAINER_API_KEY')
        configured = bool(base_url and api_key)
        
        is_mock = isinstance(portainer_client, MockPortainerClient)
        force_mock = config.force_mock_mode if config else False
        
        return {
            "current_mode": "mock" if is_mock else "real",
            "force_mock_mode": force_mock,
            "can_switch_to_real": configured,
            "portainer_configured": configured
        }
    except Exception as e:
        logger.error(f"Error getting portainer mode: {e}")
        return {
            "current_mode": "mock",
            "force_mock_mode": False,
            "can_switch_to_real": False,
            "portainer_configured": False
        }


@app.post("/api/settings/portainer-mode/toggle")
async def toggle_portainer_mode(db: Session = Depends(get_db)) -> dict:
    """Toggle between mock and real mode (requires restart for full effect)"""
    global portainer_client
    
    try:
        config = db.query(PortainerConfig).first()
        if not config:
            config = PortainerConfig(
                base_url="",
                api_key_encrypted="",
                force_mock_mode=True
            )
            db.add(config)
        
        # Toggle the preference
        new_force_mock = not config.force_mock_mode
        config.force_mock_mode = new_force_mock
        config.updated_at = datetime.utcnow()
        db.commit()
        
        is_mock = isinstance(portainer_client, MockPortainerClient)
        
        return {
            "success": True,
            "message": f"Mode preference saved to {('mock' if new_force_mock else 'real')}. Restart the app for changes to take effect.",
            "force_mock_mode": new_force_mock,
            "current_mode": "mock" if is_mock else "real",
            "note": "Restart required for full effect"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling portainer mode: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/settings/cache/clear")
async def clear_cache_endpoint() -> dict:
    """Empty the cache and reload from repositories"""
    global git_sync
    
    try:
        if not git_sync:
            raise HTTPException(status_code=503, detail="GitSync not initialized")
        
        # Clear the cache
        clear_result = git_sync.clear_cache()
        
        if clear_result['success']:
            # Synchronize repositories to reload apps
            repositories = load_config_repositories()
            sync_result = git_sync.sync_all(repositories)
            
            return {
                "success": True,
                "message": "Cache cleared and repositories resynced successfully",
                "cache_cleared": clear_result,
                "repositories_resynced": sync_result,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": clear_result['message'],
                "cache_cleared": clear_result,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.get("/api/settings/cache/status")
async def get_cache_status() -> dict:
    """Get information about cache state"""
    global git_sync
    
    try:
        if not git_sync:
            return {
                "initialized": False,
                "cache_dir": None,
                "cache_size": "unknown",
                "apps_loaded": 0,
                "last_sync": None
            }
        
        cache_dir = git_sync.cache_dir
        cache_size = git_sync._get_cache_size()
        apps_count = len(git_sync.get_all_apps())
        last_sync = git_sync.last_sync
        
        return {
            "initialized": True,
            "cache_dir": str(cache_dir),
            "cache_size": cache_size,
            "apps_loaded": apps_count,
            "last_sync": last_sync,
            "cache_path_exists": cache_dir.exists()
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/mock/stacks")
async def list_mock_stacks() -> dict:
    """List stacks in mock Portainer (only if in mock mode)"""
    
    if not isinstance(portainer_client, MockPortainerClient):
        raise HTTPException(status_code=400, detail="Not in mock mode")
    
    stacks = portainer_client.list_stacks()
    stats = portainer_client.get_stats()
    
    return {
        "mode": "mock",
        "stats": stats,
        "stacks": stacks
    }


@app.post("/api/mock/stacks/{stack_id}/force-error")
async def mock_force_error(stack_id: int, error_message: Optional[str] = None) -> dict:
    """Force error on next deploy for testing (mock only)"""
    
    if not isinstance(portainer_client, MockPortainerClient):
        raise HTTPException(status_code=400, detail="Not in mock mode")
    
    portainer_client.force_error(1, error_message)  # Set error for endpoint 1
    
    return {"message": f"Error forced: {error_message or 'default'}"}


@app.post("/api/mock/reset")
async def mock_reset() -> dict:
    """Reset mock Portainer state"""
    
    if not isinstance(portainer_client, MockPortainerClient):
        raise HTTPException(status_code=400, detail="Not in mock mode")
    
    portainer_client.reset()
    
    return {"message": "Mock Portainer state reset"}


# Mount static files (Vue frontend) with SPA fallback
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="static")
    logger.info(f"Static files mounted from {public_dir}")
else:
    logger.warning(f"Static files directory not found: {public_dir}")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', '8000'))
    host = os.getenv('HOST', '0.0.0.0')
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
