"""Mock Arcane client for testing without real infrastructure"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.models import DeployResponse

logger = logging.getLogger(__name__)


class MockArcaneClient:
    """
    Simulates Arcane API in-memory
    Useful for testing and development without real Arcane
    """

    def __init__(self):
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.deployment_errors: Dict[int, Optional[str]] = {}

    def deploy_project(self,
                       project_name: str,
                       compose_content: str,
                       env_overrides: Optional[Dict[str, str]] = None,
                       volume_overrides: Optional[Dict[str, str]] = None) -> DeployResponse:
        """Fake deploy - creates project in memory + simulates deploy"""

        if self.deployment_errors.get(0):
            error_msg = self.deployment_errors[0]
            logger.warning(f"Mock Arcane deployment error (forced): {error_msg}")
            return DeployResponse(
                success=False,
                message=f"Mock error: {error_msg}",
                arcane_response={"error": error_msg}
            )

        import uuid
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        env_content = None
        if env_overrides:
            env_content = "\n".join(f"{k}={v}" for k, v in env_overrides.items())

        self.projects[project_id] = {
            "id": project_id,
            "name": project_name,
            "composeContent": compose_content,
            "envContent": env_content,
            "created_at": datetime.utcnow().isoformat(),
            "status": "running"
        }

        logger.info(f"Mock Arcane deployed project: {project_name} (ID: {project_id})")

        return DeployResponse(
            success=True,
            project_id=project_id,
            message="Project deployed successfully via Arcane (mock)",
            arcane_response={
                "id": project_id,
                "name": project_name,
                "status": "running"
            }
        )

    def deploy_up(self, project_id: str) -> DeployResponse:
        """Mock deploy/up on existing project"""
        if project_id not in self.projects:
            return DeployResponse(
                success=False,
                message=f"Project {project_id} not found"
            )
        self.projects[project_id]["status"] = "running"
        return DeployResponse(
            success=True,
            project_id=project_id,
            message="Project deployed successfully (mock up)"
        )

    def list_projects(self) -> List[Dict[str, Any]]:
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self.projects.get(project_id)

    def destroy_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            del self.projects[project_id]
            logger.info(f"Mock Arcane destroyed project: {project_id}")
            return True
        return False

    def validate_connection(self) -> bool:
        return True

    def force_error(self, error_message: Optional[str] = None):
        self.deployment_errors[0] = error_message
        logger.info(f"Mock Arcane set error: {error_message}")

    def reset(self):
        self.projects.clear()
        self.deployment_errors.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_projects": len(self.projects),
            "projects_by_status": {
                "running": len([p for p in self.projects.values() if p["status"] == "running"]),
                "stopped": len([p for p in self.projects.values() if p["status"] == "stopped"]),
                "error": len([p for p in self.projects.values() if p["status"] == "error"])
            }
        }
