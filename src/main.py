import os
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import json
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models import App, DeployRequest, RepositoryCreate, PortainerConfigRequest, ArcaneConfigRequest
from src.git_sync import GitSync
from src.portainer import PortainerClient
from src.portainer.mock import MockPortainerClient
from src.arcane import ArcaneClient
from src.arcane.mock import MockArcaneClient
from src.db import init_db, get_db
from src.db.models import (
    Repository as RepositoryModel,
    PortainerConfig,
    ArcaneConfig,
    FavoriteApp,
    GitHubImportedApp,
)
from src.github_import import (
    GitHubAppImporter,
    GitHubImportError,
    deserialize_imported_app,
    load_persisted_imported_apps,
    serialize_imported_app,
)
from src.parsers.compose_schema import ComposeSchema
from src.security import get_encryption_manager
from src.models import GitHubImportRequest


# Load environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App FastAPI
app = FastAPI(
    title="Container AppStore API",
    description="API bridge for managing and deploying container apps via Portainer or Arcane",
    version="1.0.7"
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
arcane_client: ArcaneClient = None
scheduler: BackgroundScheduler = None
active_backend: str = "portainer"  # "portainer" | "arcane"


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


def load_imported_apps_into_memory():
    """Load persisted GitHub-imported apps into the in-memory catalog."""
    global git_sync
    if not git_sync:
        return

    from src.db import get_db_sync

    db = get_db_sync()
    try:
        records = load_persisted_imported_apps(db)
        imported_apps = {}
        for record in records:
            app = deserialize_imported_app(record.payload_json)
            imported_apps[app.app_id] = app
        git_sync.set_imported_apps(imported_apps)
        logger.info(f"Loaded {len(imported_apps)} GitHub-imported apps into memory")
    finally:
        db.close()


def _app_runtime_metadata(app: App) -> dict:
    host_architecture = app.host_architecture or GitHubAppImporter.host_architecture()
    architectures = list(dict.fromkeys(app.architectures or []))
    compatible_with_host = app.compatible_with_host
    compatibility_status = app.compatibility_status
    compatibility_warning = app.compatibility_warning

    if compatible_with_host is None and architectures:
        compatible_with_host = host_architecture in architectures
        compatibility_status = "compatible" if compatible_with_host else "warning"
        if not compatible_with_host and not compatibility_warning:
            compatibility_warning = f"This app does not list support for {host_architecture}."
    elif compatibility_status is None:
        compatibility_status = "unknown"

    return {
        "host_architecture": host_architecture,
        "architectures": architectures,
        "compatible_with_host": compatible_with_host,
        "compatibility_status": compatibility_status,
        "compatibility_warning": compatibility_warning,
        "unsupported_services": app.unsupported_services,
    }


def _app_summary(app: App) -> dict:
    runtime = _app_runtime_metadata(app)
    return {
        "app_id": app.app_id,
        "title": app.title,
        "description": app.description,
        "icon": app.icon,
        "developer": app.developer,
        "category": app.category,
        "repository_source": app.repository_source,
        "tags": app.tags,
        "source_url": app.source_url,
        "homepage": app.homepage,
        "source_type": app.source_type,
        "import_debug": app.import_debug,
        **runtime,
    }


def _app_detail_payload(app: App) -> dict:
    runtime = _app_runtime_metadata(app)
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
        "tags": app.tags,
        "compose_content": app.compose_content,
        "source_url": app.source_url,
        "homepage": app.homepage,
        "source_type": app.source_type,
        "import_debug": app.import_debug,
        **runtime,
        "services": {
            name: {
                "container_name": svc.container_name,
                "image": svc.image,
                "ports": svc.ports,
                "volumes": svc.volumes,
                "environment": svc.environment,
                "architectures": svc.architectures,
            }
            for name, svc in app.services.items()
        }
    }


def _persist_imported_app_record(
    db: Session,
    record: Optional[GitHubImportedApp],
    repository_url: str,
    app: App,
    source: dict,
) -> GitHubImportedApp:
    payload_json = serialize_imported_app(app)

    if not record:
        record = GitHubImportedApp(
            source_url=repository_url,
            repo_full_name=source["repo_full_name"],
            app_id=app.app_id,
            payload_json=payload_json,
        )
        db.add(record)
    else:
        record.repo_full_name = source["repo_full_name"]
        record.app_id = app.app_id
        record.payload_json = payload_json
        record.enabled = True
        record.last_imported_at = datetime.utcnow()

    return record


@app.on_event("startup")
async def startup_event():
    """Startup: initialize components and scheduler"""
    global git_sync, portainer_client, arcane_client, scheduler, active_backend
    
    logger.info("Starting AppStore Bridge API v1.0.7...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize repositories in DB from env (if not already present)
    init_repositories()
    
    # Git Sync
    cache_dir = os.getenv('CACHE_DIR', '/tmp/container-appstore-cache')
    git_sync = GitSync(cache_dir)
    logger.info(f"GitSync initialized with cache dir: {cache_dir}")
    
    # Initialize both clients
    portainer_client = _init_portainer()
    arcane_client = _init_arcane()
    
    # Determine active backend
    active_backend = _resolve_active_backend()
    logger.info(f"Active backend: {active_backend}")
    
    # Scheduler
    scheduler = BackgroundScheduler()
    sync_interval = int(os.getenv('GIT_SYNC_INTERVAL', '3600'))
    scheduler.add_job(init_sync, 'interval', seconds=sync_interval)
    scheduler.start()
    logger.info(f"Sync scheduler started (interval: {sync_interval}s)")
    
    # Initial sync
    init_sync()
    load_imported_apps_into_memory()
    
    logger.info("Startup complete")


def _init_portainer():
    """Initialize Portainer client (real or mock)"""
    mode = os.getenv('PORTAINER_MODE', 'auto')
    url = os.getenv('PORTAINER_BASE_URL')
    key = os.getenv('PORTAINER_API_KEY')
    force_mock = False
    
    logger.info("=== Portainer Configuration Debug ===")
    logger.info(f"PORTAINER_MODE: {mode}")
    logger.info(f"PORTAINER_BASE_URL: {url}")
    logger.info(f"PORTAINER_API_KEY: {'***' if key else 'NOT SET'}")
    
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        config = db.query(PortainerConfig).first()
        db.close()
        if config:
            force_mock = config.force_mock_mode
    except Exception as e:
        logger.warning(f"Could not load Portainer config from DB: {e}")
    
    should_use_mock = (mode == 'mock' or force_mock or not url or not key)
    
    if should_use_mock:
        client = MockPortainerClient()
        logger.info("Portainer client (MOCK mode) initialized")
        return client
    
    client = PortainerClient(url, key)
    if client.validate_connection():
        logger.info("Portainer client (REAL) initialized and validated")
        return client
    
    logger.warning("Portainer connection failed - using mock")
    return MockPortainerClient()


def _init_arcane():
    """Initialize Arcane client (real or mock)"""
    mode = os.getenv('ARCANE_MODE', 'auto')
    url = os.getenv('ARCANE_BASE_URL')
    key = os.getenv('ARCANE_API_KEY')
    env_id = 0
    force_mock = False
    
    logger.info("=== Arcane Configuration Debug ===")
    logger.info(f"ARCANE_MODE: {mode}")
    logger.info(f"ARCANE_BASE_URL: {url}")
    logger.info(f"ARCANE_API_KEY: {'***' if key else 'NOT SET'}")
    
    env_id_env = os.getenv('ARCANE_ENVIRONMENT_ID')
    if env_id_env:
        try:
            env_id = int(env_id_env)
        except ValueError:
            logger.warning("Invalid ARCANE_ENVIRONMENT_ID, using default 0")
    
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        config = db.query(ArcaneConfig).first()
        db.close()
        if config:
            force_mock = config.force_mock_mode
    except Exception as e:
        logger.warning(f"Could not load Arcane config from DB: {e}")
    
    should_use_mock = (mode == 'mock' or force_mock or not url or not key)
    
    if should_use_mock:
        client = MockArcaneClient()
        logger.info("Arcane client (MOCK mode) initialized")
        return client
    
    client = ArcaneClient(url, key, env_id)
    if client.validate_connection():
        logger.info("Arcane client (REAL) initialized and validated")
        return client
    
    logger.warning("Arcane connection failed - using mock")
    return MockArcaneClient()


def _resolve_active_backend():
    """Resolve which backend to use as active"""
    backend_env = os.getenv('ACTIVE_BACKEND', 'auto')
    
    if backend_env in ('portainer', 'arcane'):
        return backend_env
    
    # Auto-detect: prefer Arcane if configured and connected, else Portainer
    try:
        from src.db import get_db_sync
        db = get_db_sync()
        config = db.query(ArcaneConfig).first()
        if config and config.active_backend:
            return config.active_backend
        db.close()
    except Exception:
        pass
    
    # Check which real clients are available
    if isinstance(arcane_client, ArcaneClient) and arcane_client.validate_connection():
        return "arcane"
    if isinstance(portainer_client, PortainerClient) and portainer_client.validate_connection():
        return "portainer"
    
    return "portainer"


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
    
    arcane_ok = True
    if arcane_client:
        arcane_ok = arcane_client.validate_connection()
    
    overall_ok = portainer_ok or arcane_ok
    
    return {
        "status": "ok" if overall_ok else "degraded",
        "service": "AppStore Bridge API",
        "version": "1.0.7",
        "active_backend": active_backend,
        "portainer_connected": portainer_ok,
        "arcane_connected": arcane_ok,
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
    offset: int = Query(0, ge=0),
    random: bool = Query(False)) -> dict:
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
    
    # Randomize if requested
    if random:
        import random as rnd
        rnd.shuffle(filtered)
    
    # Paginate
    total = len(filtered)
    results = filtered[offset:offset + limit]
    
    # Return summary (without compose content for performance)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "apps": [_app_summary(a) for a in results]
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
        "apps": [_app_summary(a) for a in results[:50]]
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
    
    return _app_detail_payload(app)


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
    Uses the mock client of the active or specified backend
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    request.app_id = app_id
    backend = request.backend or active_backend
    
    if backend == "arcane":
        if isinstance(arcane_client, MockArcaneClient):
            response = arcane_client.deploy_project(
                project_name=request.stack_name,
                compose_content=app.compose_content,
                env_overrides=request.env_overrides,
                volume_overrides=request.volume_overrides
            )
            return response.model_dump()
        else:
            return await _deploy_to_arcane(app, request)
    else:
        if isinstance(portainer_client, MockPortainerClient):
            response = portainer_client.deploy_stack(
                stack_name=request.stack_name,
                endpoint_id=request.portainer_endpoint_id,
                compose_content=app.compose_content,
                env_overrides=request.env_overrides,
                volume_overrides=request.volume_overrides,
                namespace=request.portainer_namespace
            )
            return response.model_dump()
        else:
            return await _deploy_to_portainer(app, request)


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


@app.get("/api/imports/github")
async def list_github_imports(db: Session = Depends(get_db)) -> dict:
    """List persisted GitHub-imported apps."""
    records = load_persisted_imported_apps(db)
    imports = []
    for record in records:
        app = deserialize_imported_app(record.payload_json)
        imports.append(
            {
                "id": record.id,
                "source_url": record.source_url,
                "repo_full_name": record.repo_full_name,
                "app_id": record.app_id,
                "title": app.title,
                "description": app.description,
                "icon": app.icon,
                "homepage": app.homepage,
                "source_type": app.source_type,
                "import_debug": app.import_debug,
                "architectures": app.architectures,
                "host_architecture": app.host_architecture,
                "compatible_with_host": app.compatible_with_host,
                "compatibility_status": app.compatibility_status,
                "compatibility_warning": app.compatibility_warning,
                "last_imported_at": record.last_imported_at.isoformat() if record.last_imported_at else None,
            }
        )

    return {
        "total": len(imports),
        "imports": imports,
    }


@app.post("/api/imports/github")
async def import_github_repositories(
    request: GitHubImportRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Import GitHub repositories with docker-compose or Dockerfile into the app catalog."""
    global git_sync

    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")

    repositories = [repo.strip() for repo in request.repositories if repo.strip()]
    if not repositories:
        raise HTTPException(status_code=400, detail="At least one repository URL is required")

    importer = GitHubAppImporter()
    imported_apps = git_sync.imported_apps.copy()
    results = []

    for repository_url in repositories:
        try:
            app, source = importer.import_repository(repository_url)

            record = (
                db.query(GitHubImportedApp)
                .filter(GitHubImportedApp.source_url == repository_url)
                .first()
            )
            old_app_id = record.app_id if record else None
            _persist_imported_app_record(db, record, repository_url, app, source)

            if old_app_id and old_app_id != app.app_id:
                imported_apps.pop(old_app_id, None)
            imported_apps[app.app_id] = app
            results.append(
                {
                    "repository": repository_url,
                    "status": "imported",
                    "app_id": app.app_id,
                    "title": app.title,
                    "message": "Imported successfully",
                }
            )
        except GitHubImportError as exc:
            results.append(
                {
                    "repository": repository_url,
                    "status": "skipped",
                    "message": str(exc),
                }
            )

    db.commit()
    git_sync.set_imported_apps(imported_apps)

    return {
        "total": len(results),
        "imported": len([result for result in results if result["status"] == "imported"]),
        "skipped": len([result for result in results if result["status"] != "imported"]),
        "results": results,
    }


@app.get("/api/imports/github/export")
async def export_github_imports(
    format: str = Query("json", pattern="^(json|urls)$"),
    db: Session = Depends(get_db)
):
    """Export imported GitHub repositories as a distributable list."""
    records = load_persisted_imported_apps(db)
    repositories = [record.source_url for record in records]

    if format == "urls":
        return PlainTextResponse(
            "\n".join(repositories),
            headers={"Content-Disposition": 'attachment; filename="github-imports.txt"'},
        )

    apps = [deserialize_imported_app(record.payload_json).model_dump() for record in records]
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "host_architecture": GitHubAppImporter.host_architecture(),
        "repositories": repositories,
        "apps": apps,
    }
    return JSONResponse(
        payload,
        headers={"Content-Disposition": 'attachment; filename="github-imports.json"'},
    )


@app.post("/api/imports/github/{import_id}/resync")
async def resync_github_import(import_id: int, db: Session = Depends(get_db)) -> dict:
    """Re-import a persisted GitHub repository."""
    global git_sync

    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")

    record = db.query(GitHubImportedApp).filter(GitHubImportedApp.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Imported app not found")

    importer = GitHubAppImporter()
    try:
        app, source = importer.import_repository(record.source_url)
    except GitHubImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    old_app_id = record.app_id
    _persist_imported_app_record(db, record, record.source_url, app, source)
    db.commit()

    imported_apps = git_sync.imported_apps.copy()
    if old_app_id and old_app_id != app.app_id:
        imported_apps.pop(old_app_id, None)
    imported_apps[app.app_id] = app
    git_sync.set_imported_apps(imported_apps)

    return {
        "status": "success",
        "message": f"Re-imported {record.repo_full_name}",
        "app_id": app.app_id,
        "title": app.title,
    }


@app.delete("/api/imports/github/{import_id}")
async def delete_github_import(import_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a persisted GitHub import."""
    global git_sync

    record = db.query(GitHubImportedApp).filter(GitHubImportedApp.id == import_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Imported app not found")

    db.delete(record)
    db.commit()

    if git_sync:
        imported_apps = git_sync.imported_apps.copy()
        imported_apps.pop(record.app_id, None)
        git_sync.set_imported_apps(imported_apps)

    return {"status": "success", "message": f"Deleted import for {record.repo_full_name}"}


@app.post("/apps/{app_id}/deploy")
async def deploy_app(app_id: str, request: DeployRequest) -> dict:
    """
    Deploy app to active backend (Portainer or Arcane)
    """
    
    if not git_sync:
        raise HTTPException(status_code=503, detail="AppStore not initialized")
    
    app = git_sync.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    request.app_id = app_id
    backend = request.backend or active_backend
    
    if backend == "arcane":
        return await _deploy_to_arcane(app, request)
    else:
        return await _deploy_to_portainer(app, request)


async def _deploy_to_portainer(app, request):
    """Deploy app via Portainer"""
    global portainer_client
    
    if not portainer_client:
        raise HTTPException(status_code=503, detail="Portainer client not configured")
    
    endpoint_id = os.getenv('PORTAINER_ENDPOINT_ID')
    if endpoint_id:
        try:
            endpoint_id = int(endpoint_id)
        except ValueError:
            endpoint_id = request.portainer_endpoint_id or 1
    else:
        endpoint_id = request.portainer_endpoint_id or 1
    
    response = portainer_client.deploy_stack(
        stack_name=request.stack_name,
        endpoint_id=endpoint_id,
        compose_content=app.compose_content,
        env_overrides=request.env_overrides,
        volume_overrides=request.volume_overrides,
        namespace=request.portainer_namespace
    )
    
    return response.model_dump()


async def _deploy_to_arcane(app, request):
    """Deploy app via Arcane"""
    global arcane_client
    
    if not arcane_client:
        raise HTTPException(status_code=503, detail="Arcane client not configured")
    
    env_id = os.getenv('ARCANE_ENVIRONMENT_ID')
    if env_id:
        try:
            env_id = int(env_id)
        except ValueError:
            env_id = request.arcane_environment_id or 0
    else:
        env_id = request.arcane_environment_id or 0
    
    # Temporarily set environment_id on the client for this deployment
    original_env_id = arcane_client.environment_id
    arcane_client.environment_id = env_id
    
    try:
        response = arcane_client.deploy_project(
            project_name=request.stack_name,
            compose_content=app.compose_content,
            env_overrides=request.env_overrides,
            volume_overrides=request.volume_overrides
        )
    finally:
        arcane_client.environment_id = original_env_id
    
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


# --- Favorites ---

@app.get("/api/favorites")
async def list_favorites(db: Session = Depends(get_db)) -> dict:
    """List all favorite app IDs"""
    favorites = db.query(FavoriteApp).order_by(FavoriteApp.created_at.desc()).all()
    return {
        "favorites": [
            {
                "app_id": f.app_id,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in favorites
        ]
    }


@app.get("/api/favorites/ids")
async def get_favorite_ids(db: Session = Depends(get_db)) -> dict:
    """Get set of favorite app IDs (for UI to check which are favorited)"""
    ids = [f.app_id for f in db.query(FavoriteApp).all()]
    return {"ids": ids}


@app.post("/api/favorites/{app_id}")
async def add_favorite(app_id: str, db: Session = Depends(get_db)) -> dict:
    """Add an app to favorites"""
    existing = db.query(FavoriteApp).filter(FavoriteApp.app_id == app_id).first()
    if existing:
        return {"success": True, "message": "Already in favorites"}

    favorite = FavoriteApp(app_id=app_id)
    db.add(favorite)
    db.commit()
    logger.info(f"App {app_id} added to favorites")
    return {"success": True, "message": "Added to favorites"}


@app.delete("/api/favorites/{app_id}")
async def remove_favorite(app_id: str, db: Session = Depends(get_db)) -> dict:
    """Remove an app from favorites"""
    favorite = db.query(FavoriteApp).filter(FavoriteApp.app_id == app_id).first()
    if not favorite:
        return {"success": True, "message": "Not in favorites"}

    db.delete(favorite)
    db.commit()
    logger.info(f"App {app_id} removed from favorites")
    return {"success": True, "message": "Removed from favorites"}


# --- Backend Selection ---

@app.get("/api/settings/backend")
async def get_backend_status(db: Session = Depends(get_db)) -> dict:
    """Get current backend status"""
    global portainer_client, arcane_client, active_backend

    portainer_real = isinstance(portainer_client, PortainerClient)
    arcane_real = isinstance(arcane_client, ArcaneClient)

    portainer_configured = bool(os.getenv('PORTAINER_BASE_URL') and os.getenv('PORTAINER_API_KEY'))
    arcane_configured = bool(os.getenv('ARCANE_BASE_URL') and os.getenv('ARCANE_API_KEY'))

    try:
        config = db.query(ArcaneConfig).first()
        db_preference = config.active_backend if config else None
    except Exception:
        db_preference = None

    return {
        "active_backend": active_backend,
        "available_backends": {
            "portainer": {
                "configured": portainer_configured,
                "connected": portainer_real and portainer_client.validate_connection(),
                "mode": "real" if portainer_real else "mock"
            },
            "arcane": {
                "configured": arcane_configured,
                "connected": arcane_real and arcane_client.validate_connection(),
                "mode": "real" if arcane_real else "mock"
            }
        },
        "db_preference": db_preference
    }


@app.post("/api/settings/backend/select")
async def select_backend(request: Request, db: Session = Depends(get_db)) -> dict:
    """Select active backend (portainer or arcane)"""
    global active_backend

    import json
    body = await request.body()
    data = json.loads(body)
    backend = data.get('backend', 'portainer')

    if backend not in ('portainer', 'arcane'):
        raise HTTPException(status_code=400, detail="Backend must be 'portainer' or 'arcane'")

    active_backend = backend

    # Persist preference to DB
    try:
        config = db.query(ArcaneConfig).first()
        if not config:
            config = ArcaneConfig(base_url="", api_key_encrypted="")
            db.add(config)
        config.active_backend = backend
        config.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.warning(f"Could not persist backend preference: {e}")

    logger.info(f"Active backend switched to: {backend}")
    return {
        "success": True,
        "active_backend": backend,
        "message": f"Active backend set to {backend.upper()}"
    }


# --- Arcane Settings ---

@app.get("/api/settings/arcane")
async def get_arcane_config() -> dict:
    """Get Arcane configuration from env"""
    base_url = os.getenv('ARCANE_BASE_URL')
    api_key = os.getenv('ARCANE_API_KEY')
    env_id = os.getenv('ARCANE_ENVIRONMENT_ID')

    try:
        env_id_value = int(env_id) if env_id else 0
    except ValueError:
        env_id_value = 0

    is_mock = isinstance(arcane_client, MockArcaneClient)

    return {
        "mode": "mock" if is_mock else "real",
        "base_url": base_url or "",
        "environment_id": env_id_value,
        "is_configured": bool(base_url and api_key),
        "last_validated": None,
        "api_key": "***" if api_key else None,
        "read_only": True,
        "config_source": "env"
    }


@app.post("/api/settings/arcane")
async def set_arcane_config(
    request: ArcaneConfigRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Arcane configuration managed via env vars"""
    raise HTTPException(
        status_code=403,
        detail="Arcane configuration is managed via docker-compose.yml env vars. Update ARCANE_BASE_URL/API_KEY and restart."
    )


@app.get("/api/settings/arcane-mode")
async def get_arcane_mode(db: Session = Depends(get_db)) -> dict:
    """Get current Arcane mode (mock or real)"""
    global arcane_client

    try:
        config = db.query(ArcaneConfig).first()
        base_url = os.getenv('ARCANE_BASE_URL')
        api_key = os.getenv('ARCANE_API_KEY')
        configured = bool(base_url and api_key)

        is_mock = isinstance(arcane_client, MockArcaneClient)
        force_mock = config.force_mock_mode if config else False

        return {
            "current_mode": "mock" if is_mock else "real",
            "force_mock_mode": force_mock,
            "can_switch_to_real": configured,
            "arcane_configured": configured
        }
    except Exception as e:
        logger.error(f"Error getting arcane mode: {e}")
        return {
            "current_mode": "mock",
            "force_mock_mode": False,
            "can_switch_to_real": False,
            "arcane_configured": False
        }


@app.post("/api/settings/arcane-mode/toggle")
async def toggle_arcane_mode(db: Session = Depends(get_db)) -> dict:
    """Toggle between mock and real mode for Arcane"""
    global arcane_client

    try:
        config = db.query(ArcaneConfig).first()
        if not config:
            config = ArcaneConfig(base_url="", api_key_encrypted="", force_mock_mode=True)
            db.add(config)

        new_force_mock = not config.force_mock_mode
        config.force_mock_mode = new_force_mock
        config.updated_at = datetime.utcnow()
        db.commit()

        is_mock = isinstance(arcane_client, MockArcaneClient)

        return {
            "success": True,
            "message": f"Arcane mode preference saved to {('mock' if new_force_mock else 'real')}. Restart the app for changes to take effect.",
            "force_mock_mode": new_force_mock,
            "current_mode": "mock" if is_mock else "real",
            "note": "Restart required for full effect"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling arcane mode: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- Arcane Mock Endpoints ---

@app.get("/api/mock/arcane/projects")
async def list_arcane_mock_projects() -> dict:
    """List projects in mock Arcane (only if in mock mode)"""
    if not isinstance(arcane_client, MockArcaneClient):
        raise HTTPException(status_code=400, detail="Arcane not in mock mode")

    projects = arcane_client.list_projects()
    stats = arcane_client.get_stats()

    return {
        "mode": "mock",
        "backend": "arcane",
        "stats": stats,
        "projects": projects
    }


@app.post("/api/mock/arcane/projects/{project_id}/force-error")
async def arcane_mock_force_error(project_id: str, error_message: Optional[str] = None) -> dict:
    """Force error on next deploy for Arcane mock testing"""
    if not isinstance(arcane_client, MockArcaneClient):
        raise HTTPException(status_code=400, detail="Arcane not in mock mode")

    arcane_client.force_error(error_message)
    return {"message": f"Arcane mock error forced: {error_message or 'default'}"}


@app.post("/api/mock/arcane/reset")
async def arcane_mock_reset() -> dict:
    """Reset mock Arcane state"""
    if not isinstance(arcane_client, MockArcaneClient):
        raise HTTPException(status_code=400, detail="Arcane not in mock mode")

    arcane_client.reset()
    return {"message": "Mock Arcane state reset"}


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
