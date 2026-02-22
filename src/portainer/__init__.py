import logging
import requests
import os
from typing import Dict, Optional, Any
from src.models import DeployRequest, DeployResponse

# Disable SSL warnings for self-signed certificates in dev mode
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class PortainerClient:
    """Portainer API client for stack deployment"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Args:
            base_url: Portainer URL (e.g. http://portainer:9000)
            api_key: Portainer API key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
        # Read SSL configuration from env
        verify_ssl_env = os.getenv('PORTAINER_VERIFY_SSL', 'true').lower()
        self.verify_ssl = verify_ssl_env in ('true', '1', 'yes')
        
        logger.info(f"PORTAINER_VERIFY_SSL env value: '{verify_ssl_env}'")
        logger.info(f"self.verify_ssl boolean: {self.verify_ssl}")
        
        if not self.verify_ssl:
            logger.warning("⚠️  SSL verification DISABLED for Portainer (dev mode)")
        else:
            logger.info("✓ SSL verification enabled for Portainer")
    
    def deploy_stack(self, 
                    stack_name: str,
                    endpoint_id: int,
                    compose_content: str,
                    env_overrides: Optional[Dict[str, str]] = None,
                    volume_overrides: Optional[Dict[str, str]] = None,
                    namespace: Optional[str] = None) -> DeployResponse:
        """
        Deploy stack via Portainer
        
        Args:
            stack_name: Stack name
            endpoint_id: Portainer endpoint ID
            compose_content: docker-compose.yml content
            env_overrides: Environment variable overrides
            volume_overrides: Bind mount path overrides {original_path: new_path}
            namespace: Portainer namespace (if supported)
        
        Returns:
            DeployResponse
        """
        
        # Apply env overrides to compose if provided
        if env_overrides:
            compose_content = self._apply_env_overrides(compose_content, env_overrides)
        
        # Apply volume overrides to compose if provided
        if volume_overrides:
            from src.parsers.compose_schema import ComposeSchema
            compose_content = ComposeSchema.apply_volume_overrides(compose_content, volume_overrides)
        
        # Build payload
        payload = {
            'Name': stack_name,
            'StackFileContent': compose_content,
        }
        
        if env_overrides:
            # Portainer wants env as array of objects {name, value}
            payload['Env'] = [
                {'name': k, 'value': v} 
                for k, v in env_overrides.items()
            ]
        
        try:
            # POST /api/stacks/create/standalone/string?endpointId=X
            url = f"{self.base_url}/api/stacks/create/standalone/string?endpointId={endpoint_id}"
            
            logger.info(f"Portainer deploy request: URL={url}, Stack={stack_name}")
            logger.debug(f"Payload keys: {list(payload.keys())}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )
            
            logger.info(f"Portainer response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                return DeployResponse(
                    success=True,
                    stack_id=result.get('Id'),
                    message="Stack deployed successfully",
                    portainer_response=result
                )
            else:
                error_msg = response.text
                logger.error(f"Portainer API error: {response.status_code} - {error_msg}")
                logger.error(f"Request URL was: {url}")
                logger.error(f"Response headers: {dict(response.headers)}")
                return DeployResponse(
                    success=False,
                    message=f"Deployment failed: {response.status_code}",
                    portainer_response={'error': error_msg}
                )
        
        except requests.RequestException as e:
            logger.error(f"Request error deploying stack: {e}")
            return DeployResponse(
                success=False,
                message=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return DeployResponse(
                success=False,
                message=f"Unexpected error: {str(e)}"
            )
    
    def validate_connection(self) -> bool:
        """Validate connection to Portainer"""
        try:
            url = f"{self.base_url}/api/users"
            logger.info(f"Validating Portainer connection to {url} (verify_ssl={self.verify_ssl})")
            response = requests.get(url, headers=self.headers, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                logger.info("✓ Connected to Portainer successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Portainer connection validation failed: {e}")
            return False
    
    @staticmethod
    def _apply_env_overrides(compose_content: str, overrides: Dict[str, str]) -> str:
        """
        Apply environment variable overrides to compose content
        Simple implementation: regex-based replacement
        """
        import re
        
        result = compose_content
        
        for key, value in overrides.items():
            # Pattern: KEY: value oppure KEY=$VAR
            pattern = f"({key}:)\\s*[^\\n]+"
            replacement = f"{key}: {value}"
            result = re.sub(pattern, replacement, result)
        
        return result
