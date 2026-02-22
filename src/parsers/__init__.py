import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.models import App, ServiceMetadata


class DockerComposeParser:
    """Parser per docker-compose.yml con supporto metadata container app"""
    
    @staticmethod
    def parse_app(compose_path: str, app_id: str, repository_source: str) -> Optional[App]:
        """
        Parse docker-compose.yml e estrai metadati container app
        
        Args:
            compose_path: Path assoluto a docker-compose.yml
            app_id: ID app (cartella padre)
            repository_source: Nome repo (es. "CasaOS AppStore")
            
        Returns:
            App object oppure None se errore
        """
        try:
            with open(compose_path, 'r', encoding='utf-8') as f:
                compose = yaml.safe_load(f)
            
            if not compose:
                return None
            
            # Estrai x-casaos root
            casaos_meta = compose.get('x-casaos', {})
            
            # Extracta main service
            main_service = casaos_meta.get('main')
            if not main_service:
                # Fallback: primo servizio non-volumo/network
                services = compose.get('services', {})
                main_service = next((s for s in services.keys()), None)
            
            if not main_service:
                return None
            
            # Estrai metadati app-level
            title = DockerComposeParser._localized_string(casaos_meta.get('title'))
            description = DockerComposeParser._localized_string(casaos_meta.get('description'))
            
            icon = casaos_meta.get('icon', '')
            developer = casaos_meta.get('developer', 'Unknown')
            category = casaos_meta.get('category', 'Other')
            port_map = casaos_meta.get('port_map', '80')
            index = casaos_meta.get('index', '/')
            
            # Screenshots
            screenshot_links = casaos_meta.get('screenshot_link', [])
            if isinstance(screenshot_links, str):
                screenshot_links = [screenshot_links]
            elif screenshot_links is None:
                screenshot_links = []
            
            thumbnail = casaos_meta.get('thumbnail')
            
            # Architectures
            architectures = casaos_meta.get('architectures', ['amd64'])
            
            # Tags
            tags = casaos_meta.get('tags', [])
            
            # Parsa services
            services_data = compose.get('services', {})
            parsed_services = {}
            
            for svc_name, svc_config in services_data.items():
                if not isinstance(svc_config, dict):
                    continue
                
                # Normalizza ports e volumes da stringhe a dizionari
                ports = DockerComposeParser._normalize_ports(svc_config.get('ports', []))
                volumes = DockerComposeParser._normalize_volumes(svc_config.get('volumes', []))
                
                parsed_services[svc_name] = ServiceMetadata(
                    container_name=svc_config.get('container_name', svc_name),
                    image=svc_config.get('image', ''),
                    ports=ports,
                    volumes=volumes,
                    environment=DockerComposeParser._flatten_env(svc_config.get('environment', {}))
                )
            
            # Leggi raw compose content
            with open(compose_path, 'r', encoding='utf-8') as f:
                compose_content = f.read()
            
            return App(
                app_id=app_id,
                title=title,
                description=description,
                icon=icon,
                developer=developer,
                category=category,
                port_map=port_map,
                index=index,
                main_service=main_service,
                screenshot_links=screenshot_links,
                thumbnail=thumbnail,
                repository_source=repository_source,
                compose_content=compose_content,
                services=parsed_services,
                architectures=architectures,
                tags=tags
            )
        
        except Exception as e:
            print(f"Error parsing {compose_path}: {e}")
            return None
    
    @staticmethod
    def _localized_string(value: Any) -> str:
        """Estrai stringa from localized dict o raw string"""
        if isinstance(value, dict):
            # Prova sia uppercase che lowercase
            result = (value.get('en_US') or value.get('en_us') or 
                     value.get('it_IT') or value.get('it_it'))
            if result:
                return result
            # Se nessuna chiave conosciuta, ritorna il primo valore disponibile
            for v in value.values():
                if v:
                    return str(v)
            return ""
        return str(value) if value else ""
    
    @staticmethod
    def _flatten_env(env: Any) -> Dict[str, str]:
        """Normalizza environment (list o dict) a flat dict"""
        result = {}
        
        if isinstance(env, dict):
            for k, v in env.items():
                result[k] = str(v) if v is not None else ""
        elif isinstance(env, list):
            for item in env:
                if isinstance(item, str) and '=' in item:
                    k, v = item.split('=', 1)
                    result[k] = v
        
        return result
    
    @staticmethod
    def _normalize_ports(ports: Any) -> List[Dict[str, Any]]:
        """Converte ports shorthand (stringhe) a longhand (dict)"""
        if not ports:
            return []
        
        result = []
        for port_entry in ports:
            if isinstance(port_entry, str):
                # Shorthand: "8080:8080/tcp" oppure "8080:8080"
                result.append({"port_string": port_entry})
            elif isinstance(port_entry, dict):
                result.append(port_entry)
            elif isinstance(port_entry, int):
                result.append({"port": port_entry})
        
        return result
    
    @staticmethod
    def _normalize_volumes(volumes: Any) -> List[Dict[str, Any]]:
        """Converte volumes shorthand (stringhe) a longhand (dict)"""
        if not volumes:
            return []
        
        result = []
        for vol_entry in volumes:
            if isinstance(vol_entry, str):
                # Shorthand: "/host/path:/container/path" oppure "/container/path"
                result.append({"volume_string": vol_entry})
            elif isinstance(vol_entry, dict):
                result.append(vol_entry)
        
        return result


class AppsDirectory:
    """Gestore Apps/ directory di un repository"""
    
    @staticmethod
    def scan_apps(apps_dir: str, repository_source: str) -> Dict[str, App]:
        """
        Scansiona Apps/ e restituisce mappa app_id -> App
        
        Args:
            apps_dir: Path a cartella Apps/
            repository_source: Nome repository
            
        Returns:
            Dict {app_id: App}
        """
        apps = {}
        
        if not os.path.isdir(apps_dir):
            return apps
        
        for app_folder in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_folder)
            
            if not os.path.isdir(app_path):
                continue
            
            compose_file = os.path.join(app_path, 'docker-compose.yml')
            
            if not os.path.isfile(compose_file):
                continue
            
            # Normalizza app_id a lowercase
            app_id = app_folder.lower()
            
            app = DockerComposeParser.parse_app(compose_file, app_id, repository_source)
            
            if app:
                apps[app_id] = app
        
        return apps
