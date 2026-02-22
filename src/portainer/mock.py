"""Mock Portainer client for testing without real infrastructure"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.models import DeployResponse


logger = logging.getLogger(__name__)


class MockPortainerClient:
    """
    Simulates Portainer API in-memory
    Useful for testing and development without real Portainer
    """
    
    def __init__(self):
        self.stacks: Dict[int, Dict[str, Any]] = {}
        self.next_stack_id = 1
        self.deployment_errors: Dict[int, Optional[str]] = {}  # Simulates forced errors
    
    def deploy_stack(self, 
                    stack_name: str,
                    endpoint_id: int,
                    compose_content: str,
                    env_overrides: Optional[Dict[str, str]] = None,
                    volume_overrides: Optional[Dict[str, str]] = None,
                    namespace: Optional[str] = None) -> DeployResponse:
        """Fake deploy - creates stack in memory"""
        
        # Check if there's a forced error for this endpoint
        if endpoint_id in self.deployment_errors and self.deployment_errors[endpoint_id]:
            error_msg = self.deployment_errors[endpoint_id]
            logger.warning(f"Mock deployment error (forced): {error_msg}")
            return DeployResponse(
                success=False,
                message=f"Mock error: {error_msg}",
                portainer_response={"error": error_msg}
            )
        
        # Generate stack ID
        stack_id = self.next_stack_id
        self.next_stack_id += 1
        
        # Save stack in memory
        self.stacks[stack_id] = {
            "id": stack_id,
            "name": stack_name,
            "endpoint_id": endpoint_id,
            "namespace": namespace or "default",
            "compose_content": compose_content,
            "env_overrides": env_overrides or {},
            "volume_overrides": volume_overrides or {},
            "created_at": datetime.utcnow().isoformat(),
            "status": "running"  # Mock always running immediately
        }
        
        logger.info(f"Mock deployed stack: {stack_name} (ID: {stack_id})")
        
        return DeployResponse(
            success=True,
            stack_id=stack_id,
            message="Stack deployed successfully (mock)",
            portainer_response={
                "Id": stack_id,
                "Name": stack_name,
                "Status": "running"
            }
        )
    
    def list_stacks(self, endpoint_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all stacks (optionally filtered by endpoint)"""
        if endpoint_id:
            return [s for s in self.stacks.values() if s["endpoint_id"] == endpoint_id]
        return list(self.stacks.values())
    
    def get_stack(self, stack_id: int) -> Optional[Dict[str, Any]]:
        """Get specific stack"""
        return self.stacks.get(stack_id)
    
    def delete_stack(self, stack_id: int) -> bool:
        """Delete stack"""
        if stack_id in self.stacks:
            del self.stacks[stack_id]
            logger.info(f"Mock deleted stack: {stack_id}")
            return True
        return False
    
    def validate_connection(self) -> bool:
        """Mock always connected"""
        return True
    
    def force_error(self, endpoint_id: int, error_message: Optional[str] = None):
        """
        Force an error for the next deploy on this endpoint
        Useful for testing error handling
        
        Args:
            endpoint_id: Endpoint ID
            error_message: Error message (None = reset)
        """
        self.deployment_errors[endpoint_id] = error_message
        logger.info(f"Mock set error for endpoint {endpoint_id}: {error_message}")
    
    def reset(self):
        """Reset state (clears stacks and errors)"""
        self.stacks.clear()
        self.deployment_errors.clear()
        self.next_stack_id = 1
        logger.info("Mock Portainer state reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistics for UI"""
        return {
            "total_stacks": len(self.stacks),
            "stacks_by_status": {
                "running": len([s for s in self.stacks.values() if s["status"] == "running"]),
                "stopped": len([s for s in self.stacks.values() if s["status"] == "stopped"]),
                "error": len([s for s in self.stacks.values() if s["status"] == "error"])
            }
        }
