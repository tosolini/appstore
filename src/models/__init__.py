from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class LocalizedString(BaseModel):
    """Supports localized strings like {en_US: "...", it_IT: "..."}"""
    en_US: Optional[str] = None
    it_IT: Optional[str] = None
    
    def get_default(self) -> str:
        """Returns the default string (en_US preferred, fallback it_IT)"""
        return self.en_US or self.it_IT or ""


class ServiceMetadata(BaseModel):
    """Service (container) metadata"""
    container_name: str
    image: str
    ports: List[Dict[str, Any]] = []
    volumes: List[Dict[str, Any]] = []
    environment: Dict[str, str] = {}


class App(BaseModel):
    """App model extracted from docker-compose.yml with app container metadata"""
    app_id: str
    title: str
    description: str
    icon: Optional[str] = None
    developer: Optional[str] = None
    category: Optional[str] = None
    port_map: Optional[str] = None
    index: Optional[str] = "/"
    main_service: str  # nome del servizio principale
    screenshot_links: List[str] = []
    thumbnail: Optional[str] = None
    repository_source: str  # es. "CasaOS AppStore", "Custom Registry"
    compose_content: str  # docker-compose.yml raw content
    services: Dict[str, ServiceMetadata] = {}
    architectures: List[str] = ["amd64"]
    tags: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "app_id": "syncthing",
                "title": "Syncthing",
                "description": "Open Source Continuous File Synchronization",
                "icon": "https://...",
                "developer": "Syncthing",
                "category": "Backup",
                "port_map": "8384",
                "main_service": "syncthing",
                "repository_source": "CasaOS"
            }
        }


class DeployRequest(BaseModel):
    """App deployment request on Portainer"""
    app_id: Optional[str] = None  # Optional, assigned from endpoint path
    stack_name: str
    portainer_endpoint_id: int
    portainer_namespace: Optional[str] = None
    # Parametri opzionali per override compose
    env_overrides: Dict[str, str] = {}
    port_overrides: Dict[str, int] = {}
    volume_overrides: Dict[str, str] = {}  # {original_path: new_path}


class DeployResponse(BaseModel):
    """Deployment response"""
    success: bool
    stack_id: Optional[int] = None
    message: str
    portainer_response: Optional[Dict[str, Any]] = None


class Repository(BaseModel):
    """AppStore repository configuration"""
    name: str
    url: str
    branch: str = "main"
    enabled: bool = True
    priority: int = 0
    sync_interval_seconds: int = 3600


class RepositoryCreate(BaseModel):
    """Request model for repository creation"""
    name: str
    url: str
    branch: str = "main"
    priority: int = 0


class SyncStatus(BaseModel):
    """Synchronization status"""
    last_sync: Optional[str] = None
    repositories_synced: int = 0
    apps_loaded: int = 0
    next_sync: Optional[str] = None
    healthy: bool = True


class PortainerConfigRequest(BaseModel):
    """Request model for Portainer configuration"""
    base_url: str
    api_key: str
    endpoint_id: int = 1
