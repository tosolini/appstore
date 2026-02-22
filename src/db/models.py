"""SQLAlchemy ORM models per AppStore database"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from src.security.crypto import get_encryption_manager

Base = declarative_base()


class Repository(Base):
    """Model for repository (Container AppStore, custom sources)"""
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    url = Column(String(500), nullable=False)
    branch = Column(String(50), default="main")
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Search order (higher = priority)
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Repository(name={self.name}, enabled={self.enabled}, priority={self.priority})>"


class PortainerConfig(Base):
    """Portainer configuration"""
    __tablename__ = "portainer_config"
    
    id = Column(Integer, primary_key=True)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)  # Encrypted
    endpoint_id = Column(Integer, default=1)
    is_configured = Column(Boolean, default=False)
    force_mock_mode = Column(Boolean, default=False)  # Override to force mock mode from UI
    last_validated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def api_key(self) -> str:
        """Decrypt and return the API key"""
        if not self.api_key_encrypted:
            return None
        try:
            cipher = get_encryption_manager()
            return cipher.decrypt(self.api_key_encrypted)
        except Exception:
            return None
    
    @api_key.setter
    def api_key(self, plaintext: str):
        """Encrypt and save the API key"""
        if plaintext:
            cipher = get_encryption_manager()
            self.api_key_encrypted = cipher.encrypt(plaintext)
        else:
            self.api_key_encrypted = None
    
    def __repr__(self):
        return f"<PortainerConfig(base_url={self.base_url}, configured={self.is_configured})>"


class DeployLog(Base):
    """Deployment logs"""
    __tablename__ = "deploy_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(100), nullable=False)
    stack_name = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False)  # success, pending, error
    portainer_stack_id = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeployLog(app_id={self.app_id}, status={self.status})>"
