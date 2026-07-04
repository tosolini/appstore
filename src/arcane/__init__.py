import logging
import requests
import os
from typing import Dict, Optional, Any
from src.models import DeployResponse

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ArcaneClient:
    """Arcane API client for project (stack) deployment"""

    def __init__(self, base_url: str, api_key: str, environment_id: int = 0):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.environment_id = environment_id
        self.headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        }
        verify_ssl_env = os.getenv('ARCANE_VERIFY_SSL', 'true').lower()
        self.verify_ssl = verify_ssl_env in ('true', '1', 'yes')

        logger.info(f"ARCANE_VERIFY_SSL env value: '{verify_ssl_env}'")
        logger.info(f"self.verify_ssl boolean: {self.verify_ssl}")

        if not self.verify_ssl:
            logger.warning("SSL verification DISABLED for Arcane (dev mode)")
        else:
            logger.info("SSL verification enabled for Arcane")

    def deploy_project(self,
                       project_name: str,
                       compose_content: str,
                       env_overrides: Optional[Dict[str, str]] = None,
                       volume_overrides: Optional[Dict[str, str]] = None) -> DeployResponse:
        """
        Deploy a project via Arcane (create + deploy)

        1. POST /api/environments/{env_id}/projects — create
        2. POST /api/environments/{env_id}/projects/{id}/up — deploy
        """

        if env_overrides:
            compose_content = self._apply_env_overrides(compose_content, env_overrides)

        if volume_overrides:
            from src.parsers.compose_schema import ComposeSchema
            compose_content = ComposeSchema.apply_volume_overrides(compose_content, volume_overrides)

        env_content = self._build_env_content(env_overrides) if env_overrides else None

        # Step 1: Create project
        payload = {
            'name': project_name,
            'composeContent': compose_content,
        }
        if env_content:
            payload['envContent'] = env_content

        try:
            url = f"{self.base_url}/api/environments/{self.environment_id}/projects"

            logger.info(f"Arcane create project: URL={url}, Project={project_name}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )

            logger.info(f"Arcane create response: {response.status_code}")

            if response.status_code not in (200, 201):
                error_msg = response.text
                logger.error(f"Arcane create error: {response.status_code} - {error_msg}")
                return DeployResponse(
                    success=False,
                    message=f"Project creation failed: {response.status_code}",
                    arcane_response={'error': error_msg}
                )

            result = response.json()
            data = result.get('data') or result
            project_id = data.get('id')

            if not project_id:
                return DeployResponse(
                    success=False,
                    message="Project created but no ID returned",
                    arcane_response=data
                )

            # Step 2: Deploy (up) the project
            logger.info(f"Arcane deploying project: {project_id}")
            deploy_response = self._deploy_up(project_id)
            return deploy_response

        except requests.RequestException as e:
            logger.error(f"Request error deploying project: {e}")
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

    def _deploy_up(self, project_id: str) -> DeployResponse:
        """Deploy (up) an existing project"""
        try:
            url = f"{self.base_url}/api/environments/{self.environment_id}/projects/{project_id}/up"
            response = requests.post(
                url,
                headers=self.headers,
                json={},
                verify=self.verify_ssl,
                timeout=60
            )

            logger.info(f"Arcane deploy/up response: {response.status_code}")

            if response.status_code in (200, 204):
                return DeployResponse(
                    success=True,
                    project_id=project_id,
                    message="Project deployed successfully via Arcane"
                )

            error_msg = response.text
            logger.error(f"Arcane deploy/up error: {response.status_code} - {error_msg}")

            # Try to get project status for more info
            try:
                get_url = f"{self.base_url}/api/environments/{self.environment_id}/projects/{project_id}"
                get_resp = requests.get(get_url, headers=self.headers, verify=self.verify_ssl, timeout=10)
                if get_resp.status_code == 200:
                    project_data = get_resp.json().get('data') or get_resp.json()
                    return DeployResponse(
                        success=True,
                        project_id=project_id,
                        message="Project created (deploy returned warning)",
                        arcane_response=project_data
                    )
            except Exception:
                pass

            return DeployResponse(
                success=False,
                message=f"Project deploy failed: {response.status_code}",
                arcane_response={'error': error_msg}
            )

        except requests.RequestException as e:
            logger.error(f"Request error during deploy/up: {e}")
            return DeployResponse(
                success=False,
                message=f"Deploy request failed: {str(e)}"
            )

    def validate_connection(self) -> bool:
        """Validate connection to Arcane by listing environments"""
        try:
            url = f"{self.base_url}/api/environments"
            logger.info(f"Validating Arcane connection to {url} (verify_ssl={self.verify_ssl})")
            response = requests.get(url, headers=self.headers, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                logger.info("Connected to Arcane successfully")
                return True
            logger.warning(f"Arcane connection validation failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Arcane connection validation failed: {e}")
            return False

    def list_projects(self) -> list:
        """List projects in the configured environment"""
        try:
            url = f"{self.base_url}/api/environments/{self.environment_id}/projects"
            response = requests.get(url, headers=self.headers, timeout=10, verify=self.verify_ssl)
            if response.status_code == 200:
                result = response.json()
                data = result.get('data') or result
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and 'projects' in data:
                    return data['projects']
                return []
            return []
        except Exception as e:
            logger.error(f"Error listing Arcane projects: {e}")
            return []

    def destroy_project(self, project_id: str) -> bool:
        """Destroy a project"""
        try:
            url = f"{self.base_url}/api/environments/{self.environment_id}/projects/{project_id}/destroy"
            response = requests.post(url, headers=self.headers, verify=self.verify_ssl, timeout=15)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error destroying project: {e}")
            return False

    @staticmethod
    def _apply_env_overrides(compose_content: str, overrides: Dict[str, str]) -> str:
        import re
        result = compose_content
        for key, value in overrides.items():
            pattern = f"({key}:)\\s*[^\\n]+"
            replacement = f"{key}: {value}"
            result = re.sub(pattern, replacement, result)
        return result

    @staticmethod
    def _build_env_content(env_overrides: Dict[str, str]) -> str:
        """Convert env_overrides dict to .env format string"""
        lines = []
        for key, value in env_overrides.items():
            lines.append(f"{key}={value}")
        return "\n".join(lines)
