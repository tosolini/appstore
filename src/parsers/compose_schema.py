"""Parser to extract interactive parameters from docker-compose.yml"""

from typing import Dict, Any, List, Optional
import re
import yaml


class ComposeParameter:
    """An environment parameter that can be customized"""
    
    def __init__(self, name: str, default_value: Optional[str] = None, 
                 param_type: str = "string", description: str = ""):
        self.name = name
        self.default_value = default_value
        self.type = param_type  # string, int, port, path, bool
        self.description = description
        self.required = default_value is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default_value,
            "description": self.description,
            "required": self.required
        }
    
    def validate(self, value: any) -> tuple[bool, Optional[str]]:
        """Validate value according to type"""
        if self.type == "int":
            try:
                int(value)
                return True, None
            except:
                return False, f"{self.name} must be integer"
        elif self.type == "port":
            try:
                port = int(value)
                if 1 <= port <= 65535:
                    return True, None
                else:
                    return False, f"Port {port} out of range (1-65535)"
            except:
                return False, f"{self.name} must be valid port"
        elif self.type == "bool":
            if str(value).lower() in ['true', '1', 'yes', 'false', '0', 'no']:
                return True, None
            return False, f"{self.name} must be true/false"
        # string, path - accept everything
        return True, None


class VolumeParameter:
    """A bind mount volume that can be customized"""
    
    def __init__(self, source: str, target: str, service: str, mode: str = "rw"):
        self.source = source  # Host path
        self.target = target  # Container path
        self.service = service
        self.mode = mode  # rw, ro
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "service": self.service,
            "mode": self.mode
        }


class ComposeSchema:
    """Extract parameter schema from docker-compose.yml"""
    
    # Mapping to recognize common types
    TYPE_PATTERNS = {
        "port": [r"PORT", r"_PORT$"],
        "int": [r"PUID", r"PGID", r"UID", r"GID", r"_ID$", r"COUNT"],
        "path": [r"PATH", r"DIR", r"VOLUME"],
        "bool": [r"ENABLED", r"DEBUG", r"SECURE"],
    }
    
    @staticmethod
    def infer_type(env_name: str) -> str:
        """Inferisce il tipo di parametro dal nome"""
        for ptype, patterns in ComposeSchema.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, env_name, re.IGNORECASE):
                    return ptype
        return "string"
    
    @staticmethod
    def extract_schema(compose_content: str) -> List[ComposeParameter]:
        """
        Estrae parametri environment da docker-compose.yml
        Ritorna lista di ComposeParameter
        """
        try:
            compose = yaml.safe_load(compose_content)
        except Exception as e:
            print(f"Error parsing compose: {e}")
            return []
        
        parameters = []
        seen_env_vars = set()
        
        if not compose or 'services' not in compose:
            return []
        
        services = compose.get('services', {})
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            env = service_config.get('environment', {})
            
            # Parse environment (can be dict or list)
            env_vars = {}
            if isinstance(env, dict):
                env_vars = env
            elif isinstance(env, list):
                for item in env:
                    if isinstance(item, str) and '=' in item:
                        k, v = item.split('=', 1)
                        env_vars[k] = v
            
            # Estrai parametri (skip variables come $PUID, ${VAR})
            for key, value in env_vars.items():
                if key in seen_env_vars:
                    continue
                
                # Skip keys that start with $ (variables)
                if str(value).startswith('$'):
                    # This is a placeholder - allow customization
                    var_name = str(value).strip('${}')
                    if not var_name.startswith('_'):
                        seen_env_vars.add(key)
                        param_type = ComposeSchema.infer_type(key)
                        param = ComposeParameter(
                            name=key,
                            default_value=None,
                            param_type=param_type,
                            description=f"Environment variable {key}"
                        )
                        parameters.append(param)
                else:
                    # Static value - add as customizable
                    seen_env_vars.add(key)
                    param_type = ComposeSchema.infer_type(key)
                    param = ComposeParameter(
                        name=key,
                        default_value=str(value),
                        param_type=param_type,
                        description=f"Environment variable {key}"
                    )
                    parameters.append(param)
        
        # Common container app variables (always available)
        common_vars = [
            ComposeParameter("TZ", "UTC", "string", "Timezone"),
            ComposeParameter("PUID", "1000", "int", "User ID"),
            ComposeParameter("PGID", "1000", "int", "Group ID"),
        ]
        
        # Add common if not already present
        existing_names = {p.name for p in parameters}
        for common_var in common_vars:
            if common_var.name not in existing_names:
                parameters.append(common_var)
        
        return parameters
    
    @staticmethod
    def apply_overrides(compose_content: str, overrides: Dict[str, str]) -> str:
        """
        Apply overrides to environment values in compose
        
        Args:
            compose_content: Original YAML
            overrides: {ENV_VAR: new_value}
        
        Returns:
            YAML modificato
        """
        try:
            compose = yaml.safe_load(compose_content)
        except:
            return compose_content
        
        if not compose or 'services' not in compose:
            return compose_content
        
        for service_name, service_config in compose.get('services', {}).items():
            if not isinstance(service_config, dict):
                continue
            
            env = service_config.get('environment', {})
            
            if isinstance(env, dict):
                for key in overrides:
                    if key in env:
                        env[key] = overrides[key]
            elif isinstance(env, list):
                new_env = []
                for item in env:
                    if isinstance(item, str) and '=' in item:
                        k, v = item.split('=', 1)
                        if k in overrides:
                            new_env.append(f"{k}={overrides[k]}")
                        else:
                            new_env.append(item)
                    else:
                        new_env.append(item)
                service_config['environment'] = new_env
        
        return yaml.dump(compose, default_flow_style=False)
    
    @staticmethod
    def extract_volumes(compose_content: str) -> List[VolumeParameter]:
        """
        Estrae i volume bind mounts dal docker-compose.yml
        
        Args:
            compose_content: Contenuto YAML del compose
        
        Returns:
            Lista di VolumeParameter con i bind mounts
        """
        try:
            compose = yaml.safe_load(compose_content)
        except:
            return []
        
        if not compose or 'services' not in compose:
            return []
        
        volumes = []
        services = compose.get('services', {})
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            service_volumes = service_config.get('volumes', [])
            
            for vol in service_volumes:
                # Skip named volumes (non bind mounts)
                if isinstance(vol, str):
                    # Bind mount format: "source:target[:mode]"
                    if ':' in vol:
                        parts = vol.split(':')
                        source = parts[0]
                        target = parts[1] if len(parts) > 1 else ""
                        mode = parts[2] if len(parts) > 2 else "rw"
                        
                        # Skip if source doesn't look like a path (named volumes start without /)
                        if not source.startswith('/') and not source.startswith('.') and not source.startswith('~'):
                            continue
                        
                        volumes.append(VolumeParameter(
                            source=source,
                            target=target,
                            service=service_name,
                            mode=mode
                        ))
                elif isinstance(vol, dict):
                    # Long syntax: {type: bind, source: ..., target: ...}
                    if vol.get('type') == 'bind':
                        source = vol.get('source', '')
                        target = vol.get('target', '')
                        mode = 'ro' if vol.get('read_only', False) else 'rw'
                        
                        volumes.append(VolumeParameter(
                            source=source,
                            target=target,
                            service=service_name,
                            mode=mode
                        ))
        
        return volumes
    
    @staticmethod
    def apply_volume_overrides(compose_content: str, overrides: Dict[str, str]) -> str:
        """
        Applica override ai volume bind paths nel compose
        
        Args:
            compose_content: YAML originale
            overrides: {original_source_path: new_source_path}
        
        Returns:
            YAML modificato con i nuovi path
        """
        try:
            compose = yaml.safe_load(compose_content)
        except:
            return compose_content
        
        if not compose or 'services' not in compose:
            return compose_content
        
        for service_name, service_config in compose.get('services', {}).items():
            if not isinstance(service_config, dict):
                continue
            
            service_volumes = service_config.get('volumes', [])
            new_volumes = []
            
            for vol in service_volumes:
                if isinstance(vol, str) and ':' in vol:
                    parts = vol.split(':')
                    source = parts[0]
                    
                    # If there's an override for this source path, apply it
                    if source in overrides:
                        parts[0] = overrides[source]
                        new_volumes.append(':'.join(parts))
                    else:
                        new_volumes.append(vol)
                elif isinstance(vol, dict) and vol.get('type') == 'bind':
                    source = vol.get('source', '')
                    if source in overrides:
                        vol['source'] = overrides[source]
                    new_volumes.append(vol)
                else:
                    new_volumes.append(vol)
            
            if new_volumes:
                service_config['volumes'] = new_volumes
        
        return yaml.dump(compose, default_flow_style=False)

