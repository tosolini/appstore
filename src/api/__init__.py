import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from src.models import App, DeployRequest, DeployResponse, SyncStatus
from src.git_sync import GitSync
from src.portainer import PortainerClient


logger = logging.getLogger(__name__)


class AppRoutes:
    """Routes per gestione app"""
    
    def __init__(self, git_sync: GitSync, portainer_client: Optional[PortainerClient] = None):
        self.git_sync = git_sync
        self.portainer_client = portainer_client
        self.router = APIRouter(prefix="/apps", tags=["apps"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all routes"""
        self.router.add_api_route("/", self.list_apps, methods=["GET"])
        self.router.add_api_route("/search", self.search_apps, methods=["GET"])
        self.router.add_api_route("/{app_id}", self.get_app_detail, methods=["GET"])
        self.router.add_api_route("/{app_id}/deploy", self.deploy_app, methods=["POST"])
    
    def list_apps(self, 
                  category: Optional[str] = Query(None),
                  repository: Optional[str] = Query(None),
                  limit: int = Query(100, ge=1, le=1000),
                  offset: int = Query(0, ge=0)) -> dict:
        """
        Lista app con filtri opzionali
        
        Query params:
            - category: Filtra per categoria
            - repository: Filtra per repository source
            - limit: Numero risultati (default 100, max 1000)
            - offset: Offset paginazione
        """
        
        apps = self.git_sync.get_all_apps()
        
        # Filter
        filtered = list(apps.values())
        
        if category:
            filtered = [a for a in filtered if a.category and a.category.lower() == category.lower()]
        
        if repository:
            filtered = [a for a in filtered if a.repository_source.lower() == repository.lower()]
        
        # Paginate
        total = len(filtered)
        results = filtered[offset:offset + limit]
        
        # Return summary (senza compose content per performance)
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
    
    def search_apps(self, q: str = Query(..., min_length=1, max_length=200)) -> dict:
        """
        Ricerca app per title/description
        
        Query params:
            - q: Query di ricerca (required)
        """
        
        apps = self.git_sync.get_all_apps()
        q_lower = q.lower()
        
        # FTS semplice: match su title, description, tags
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
    
    def get_app_detail(self, app_id: str) -> dict:
        """
        Dettaglio completo app (include compose)
        """
        
        app = self.git_sync.get_app(app_id)
        
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
    
    def deploy_app(self, app_id: str, request: DeployRequest) -> dict:
        """
        Deploy app a Portainer
        """
        
        if not self.portainer_client:
            raise HTTPException(status_code=503, detail="Portainer client not configured")
        
        app = self.git_sync.get_app(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="App not found")
        
        # Override request app_id con quello in URL
        request.app_id = app_id
        
        # Deploy via Portainer
        response = self.portainer_client.deploy_stack(
            stack_name=request.stack_name,
            endpoint_id=request.portainer_endpoint_id,
            compose_content=app.compose_content,
            env_overrides=request.env_overrides,
            namespace=request.portainer_namespace
        )
        
        return response.model_dump()


class HealthRoutes:
    """Routes health e sync status"""
    
    def __init__(self, git_sync: GitSync, portainer_client: Optional[PortainerClient] = None):
        self.git_sync = git_sync
        self.portainer_client = portainer_client
        self.router = APIRouter(prefix="", tags=["health"])
        self._setup_routes()
    
    def _setup_routes(self):
        self.router.add_api_route("/health", self.health_check, methods=["GET"])
        self.router.add_api_route("/status", self.sync_status, methods=["GET"])
    
    def health_check(self) -> dict:
        """Health check endpoint"""
        
        portainer_ok = True
        if self.portainer_client:
            portainer_ok = self.portainer_client.validate_connection()
        
        return {
            "status": "ok" if portainer_ok else "degraded",
            "service": "AppStore Bridge API",
            "portainer_connected": portainer_ok,
            "apps_loaded": len(self.git_sync.get_all_apps())
        }
    
    def sync_status(self) -> dict:
        """Stato sincronizzazione"""
        
        all_apps = self.git_sync.get_all_apps()
        repos = set(a.repository_source for a in all_apps.values())
        
        return {
            "last_sync": self.git_sync.last_sync,
            "apps_loaded": len(all_apps),
            "repositories_synced": len(repos),
            "healthy": len(all_apps) > 0
        }
