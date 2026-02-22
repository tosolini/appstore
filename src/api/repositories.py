"""API endpoints to manage repositories"""

import logging
from typing import List, Optional
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from src.db import get_db
from src.db.models import Repository
from src.models import Repository as RepositorySchema

logger = logging.getLogger(__name__)


class RepositoryAPI:
    """CRUD operations for Repository"""
    
    @staticmethod
    def create_repository(
        repo_data: RepositorySchema,
        db: Session = Depends(get_db)
    ) -> Repository:
        """Create new repository"""
        
        # Check for duplicate
        existing = db.query(Repository).filter(
            Repository.name == repo_data.name
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail=f"Repository '{repo_data.name}' already exists")
        
        db_repo = Repository(
            name=repo_data.name,
            url=repo_data.url,
            branch=repo_data.branch,
            enabled=repo_data.enabled,
            priority=0
        )
        db.add(db_repo)
        db.commit()
        db.refresh(db_repo)
        
        logger.info(f"Repository created: {repo_data.name}")
        return db_repo
    
    @staticmethod
    def list_repositories(db: Session = Depends(get_db)) -> List[Repository]:
        """List all repositories ordered by priority"""
        repos = db.query(Repository).order_by(Repository.priority.desc()).all()
        return repos
    
    @staticmethod
    def get_repository(repo_id: int, db: Session = Depends(get_db)) -> Repository:
        """Get specific repository"""
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        return repo
    
    @staticmethod
    def update_repository(
        repo_id: int,
        repo_data: RepositorySchema,
        db: Session = Depends(get_db)
    ) -> Repository:
        """Update repository"""
        
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check name conflict (if changing name)
        if repo_data.name != repo.name:
            existing = db.query(Repository).filter(
                Repository.name == repo_data.name
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail=f"Repository '{repo_data.name}' already exists")
        
        repo.name = repo_data.name
        repo.url = repo_data.url
        repo.branch = repo_data.branch
        repo.enabled = repo_data.enabled
        
        db.commit()
        db.refresh(repo)
        
        logger.info(f"Repository updated: {repo_data.name}")
        return repo
    
    @staticmethod
    def delete_repository(repo_id: int, db: Session = Depends(get_db)) -> dict:
        """Delete repository"""
        
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        name = repo.name
        db.delete(repo)
        db.commit()
        
        logger.info(f"Repository deleted: {name}")
        return {"message": f"Repository '{name}' deleted"}
    
    @staticmethod
    def set_priority(repo_id: int, priority: int, db: Session = Depends(get_db)) -> Repository:
        """Update repository priority"""
        
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        repo.priority = priority
        db.commit()
        db.refresh(repo)
        
        logger.info(f"Repository {repo.name} priority set to {priority}")
        return repo
    
    @staticmethod
    def toggle_enabled(repo_id: int, db: Session = Depends(get_db)) -> Repository:
        """Toggle enabled/disabled"""
        
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        repo.enabled = not repo.enabled
        db.commit()
        db.refresh(repo)
        
        state = "enabled" if repo.enabled else "disabled"
        logger.info(f"Repository {repo.name} {state}")
        return repo


def repo_to_dict(repo: Repository) -> dict:
    """Convert ORM model to dict"""
    return {
        "id": repo.id,
        "name": repo.name,
        "url": repo.url,
        "branch": repo.branch,
        "enabled": repo.enabled,
        "priority": repo.priority,
        "last_synced": repo.last_synced.isoformat() if repo.last_synced else None,
        "created_at": repo.created_at.isoformat() if repo.created_at else None
    }
