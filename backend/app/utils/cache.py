"""
Simple in-memory cache for API responses
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

class SimpleCache:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = 3600  # 1 hour default TTL
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if datetime.now() > entry["expires_at"]:
            del self.cache[key]
            return None
        
        print(f"✅ Cache hit: {key}")
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache"""
        ttl = ttl_seconds or self.ttl_seconds
        
        self.cache[key] = {
            "value": value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=ttl)
        }
        
        print(f"💾 Cached: {key} (TTL: {ttl}s)")

    def delete(self, key: str):
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
            print(f"🗑️ Deleted from cache: {key}")

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        print("🗑️ Cache cleared")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "total_entries": len(self.cache),
            "entries": list(self.cache.keys())
        }
    
# Global cache instance
cache = SimpleCache()