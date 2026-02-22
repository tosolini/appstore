import os
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any
from git import Repo
from git.exc import GitCommandError

from src.models import App
from src.parsers import AppsDirectory
from src.db.models import Repository as RepositoryModel


logger = logging.getLogger(__name__)


class GitSync:
    """Git repository synchronization manager"""
    
    def __init__(self, cache_dir: str):
        """
        Args:
            cache_dir: Path to cache folder (e.g. /app/cache)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_sync = None
        self.apps: Dict[str, App] = {}
    
    def clone_or_update(self, repo_config: RepositoryModel) -> bool:
        """
        Clone or update repository
        
        Returns:
            True if success, False otherwise
        """
        repo_name = repo_config.name
        repo_path = self.cache_dir / repo_name
        
        try:
            if repo_path.exists():
                logger.info(f"Updating repository: {repo_name}")
                repo = Repo(str(repo_path))

                # Detect remote URL mismatch and re-clone if needed
                origin_url = repo.remotes.origin.url if repo.remotes.origin else None
                if origin_url and origin_url != repo_config.url:
                    logger.warning(
                        f"Repository {repo_name} remote mismatch: "
                        f"cache={origin_url} expected={repo_config.url}. Re-cloning."
                    )
                    shutil.rmtree(repo_path)
                    return self._clone_repo(repo_config, repo_path)

                # Detect branch mismatch on remote
                if not self._remote_has_branch(repo, repo_config.branch):
                    logger.error(
                        f"Repository {repo_name} missing branch '{repo_config.branch}' "
                        f"on remote {origin_url}"
                    )
                    return False

                repo.remotes.origin.pull(repo_config.branch)
                logger.info(f"Repository {repo_name} updated successfully")
            else:
                return self._clone_repo(repo_config, repo_path)

            return True
        except Exception as e:
            logger.error(f"Error syncing {repo_name}: {e}")
            return False

    def _clone_repo(self, repo_config: RepositoryModel, repo_path: Path) -> bool:
        """Clone repository with branch validation."""
        try:
            logger.info(f"Cloning repository: {repo_config.url}")
            Repo.clone_from(
                repo_config.url,
                str(repo_path),
                branch=repo_config.branch,
                depth=1  # Shallow clone for performance
            )
            logger.info(f"Repository {repo_config.name} cloned successfully")
            return True
        except Exception as e:
            logger.error(f"Error cloning {repo_config.name}: {e}")
            return False

    def _remote_has_branch(self, repo: Repo, branch: str) -> bool:
        """Check if remote has a given branch name."""
        try:
            refs = repo.remotes.origin.refs
            return any(ref.remote_head == branch for ref in refs)
        except Exception:
            return False
    
    def sync_all(self, repositories: List[RepositoryModel]) -> Dict[str, Any]:
        """
        Synchronize all repositories and load apps
        
        Returns:
            {repositories_synced: int, apps_loaded: int, errors: []}
        """
        result = {
            'repositories_synced': 0,
            'apps_loaded': 0,
            'errors': []
        }
        
        self.apps.clear()
        
        for repo_config in repositories:
            if not repo_config.enabled:
                continue
            
            if not self.clone_or_update(repo_config):
                result['errors'].append(f"Failed to sync {repo_config.name}")
                continue
            
            result['repositories_synced'] += 1
            
            # Scan Apps/
            apps_dir = self.cache_dir / repo_config.name / "Apps"
            
            if apps_dir.exists():
                apps_found = AppsDirectory.scan_apps(str(apps_dir), repo_config.name)
                self.apps.update(apps_found)
                result['apps_loaded'] += len(apps_found)
                logger.info(f"Loaded {len(apps_found)} apps from {repo_config.name}")
        
        self.last_sync = datetime.utcnow().isoformat()
        logger.info(f"Sync complete: {result}")
        
        return result
    
    def get_all_apps(self) -> Dict[str, App]:
        """Returns all loaded apps"""
        return self.apps.copy()
    
    def get_app(self, app_id: str) -> Optional[App]:
        """Returns specific app"""
        return self.apps.get(app_id)
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Completely empty the cache
        
        Returns:
            {success: bool, message: str, deleted_repos: int, cache_size_before: str}
        """
        try:
            cache_stats = {
                'deleted_repos': 0,
                'cache_size_before': self._get_cache_size(),
            }
            
            for item in self.cache_dir.iterdir():
                if item.is_dir():
                    try:
                        shutil.rmtree(item)
                        cache_stats['deleted_repos'] += 1
                        logger.info(f"Deleted cache directory: {item.name}")
                    except Exception as e:
                        logger.error(f"Error deleting {item.name}: {e}")
                else:
                    try:
                        item.unlink()
                        logger.info(f"Deleted cache file: {item.name}")
                    except Exception as e:
                        logger.error(f"Error deleting {item.name}: {e}")
            
            # Clean up app list in memory
            self.apps.clear()
            self.last_sync = None
            
            return {
                'success': True,
                'message': f'Cache cleared successfully. {cache_stats["deleted_repos"]} repositories deleted.',
                'deleted_repos': cache_stats['deleted_repos'],
                'cache_size_before': cache_stats['cache_size_before']
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {
                'success': False,
                'message': f'Error clearing cache: {str(e)}',
                'deleted_repos': 0,
                'cache_size_before': self._get_cache_size()
            }
    
    def _get_cache_size(self) -> str:
        """Calculates total cache size in human-readable format"""
        try:
            total_size = 0
            for entry in self.cache_dir.rglob('*'):
                if entry.is_file():
                    total_size += entry.stat().st_size
            
            # Convert to human-readable format (KB, MB, GB)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if total_size < 1024:
                    return f"{total_size:.2f} {unit}"
                total_size /= 1024
            return f"{total_size:.2f} GB"
        except Exception as e:
            logger.error(f"Error calculating cache size: {e}")
            return "unknown"
