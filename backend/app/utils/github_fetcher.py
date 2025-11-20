"""
GitHub Repository Fetcher
Fetches code from GitHub repositories for analysis
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional
from pathlib import Path


class GitHubFetcher:
    """Fetches and caches GitHub repositories"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize GitHub fetcher
        
        Args:
            cache_dir: Directory to cache cloned repositories (default: /tmp/github_repos)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Use temp directory or a persistent cache directory
            self.cache_dir = Path(os.getenv("GITHUB_CACHE_DIR", "/tmp/github_repos"))
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_repo_name_from_url(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        # Handle different URL formats:
        # https://github.com/owner/repo.git
        # https://github.com/owner/repo
        # git@github.com:owner/repo.git
        # owner/repo
        
        repo_url = repo_url.strip()
        
        # If it's already owner/repo format
        if '/' in repo_url and '@' not in repo_url and '://' not in repo_url:
            return repo_url.replace('/', '_')
        
        # Extract from URL
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        
        if 'github.com' in repo_url:
            # Extract owner/repo from URL
            parts = repo_url.split('github.com/')
            if len(parts) > 1:
                repo_path = parts[1].split('/')
                if len(repo_path) >= 2:
                    return f"{repo_path[0]}_{repo_path[1]}"
        
        # Fallback: use last part of URL
        return repo_url.split('/')[-1].replace('.git', '').replace(':', '_')
    
    def _get_repo_url(self, repo_url: str) -> str:
        """Normalize repository URL"""
        repo_url = repo_url.strip()
        
        # If it's already a full URL, return as is
        if repo_url.startswith('http://') or repo_url.startswith('https://') or repo_url.startswith('git@'):
            return repo_url
        
        # If it's owner/repo format, convert to HTTPS URL
        if '/' in repo_url and '@' not in repo_url:
            return f"https://github.com/{repo_url}.git"
        
        return repo_url
    
    def fetch_repository(
        self, 
        repo_url: str, 
        branch: str = "main",
        subfolder: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch repository from GitHub and return local path
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo or owner/repo)
            branch: Branch to checkout (default: main)
            subfolder: Optional subfolder within repo to return (e.g., "banking-app-mongodb")
        
        Returns:
            Local path to repository or subfolder, None if failed
        """
        try:
            repo_name = self._get_repo_name_from_url(repo_url)
            normalized_url = self._get_repo_url(repo_url)
            repo_cache_path = self.cache_dir / repo_name
            
            print(f"   📥 Fetching repository: {normalized_url}")
            print(f"   📁 Cache path: {repo_cache_path}")
            
            # Check if repository is already cloned
            if repo_cache_path.exists() and (repo_cache_path / '.git').exists():
                print(f"   ✅ Repository already cached, updating...")
                try:
                    # Update existing repository
                    subprocess.run(
                        ['git', 'fetch', 'origin'],
                        cwd=repo_cache_path,
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    subprocess.run(
                        ['git', 'checkout', branch],
                        cwd=repo_cache_path,
                        check=True,
                        capture_output=True,
                        timeout=10
                    )
                    subprocess.run(
                        ['git', 'pull', 'origin', branch],
                        cwd=repo_cache_path,
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    print(f"   ✅ Repository updated successfully")
                except subprocess.TimeoutExpired:
                    print(f"   ⚠️ Git operation timed out, using cached version")
                except subprocess.CalledProcessError as e:
                    print(f"   ⚠️ Failed to update repository: {e}")
                    # Continue with existing cache
            else:
                # Clone repository
                print(f"   📥 Cloning repository...")
                try:
                    subprocess.run(
                        ['git', 'clone', '--depth', '1', '--branch', branch, normalized_url, str(repo_cache_path)],
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                    print(f"   ✅ Repository cloned successfully")
                except subprocess.TimeoutExpired:
                    print(f"   ❌ Git clone timed out")
                    return None
                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Failed to clone repository: {e}")
                    if e.stderr:
                        print(f"   Error: {e.stderr.decode()}")
                    return None
            
            # Return path to subfolder if specified, otherwise root
            if subfolder:
                subfolder_path = repo_cache_path / subfolder
                if subfolder_path.exists():
                    return str(subfolder_path)
                else:
                    print(f"   ⚠️ Subfolder '{subfolder}' not found in repository")
                    return str(repo_cache_path)
            
            return str(repo_cache_path)
            
        except Exception as e:
            print(f"   ❌ Error fetching repository: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def clear_cache(self, repo_url: Optional[str] = None):
        """
        Clear repository cache
        
        Args:
            repo_url: Specific repository to clear, or None to clear all
        """
        try:
            if repo_url:
                repo_name = self._get_repo_name_from_url(repo_url)
                repo_cache_path = self.cache_dir / repo_name
                if repo_cache_path.exists():
                    shutil.rmtree(repo_cache_path)
                    print(f"   ✅ Cleared cache for {repo_name}")
            else:
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    print(f"   ✅ Cleared all repository cache")
        except Exception as e:
            print(f"   ⚠️ Error clearing cache: {e}")


# Global instance
github_fetcher = GitHubFetcher()

