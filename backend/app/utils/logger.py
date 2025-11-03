"""
Request logging and monitoring
"""

import logging
from datetime import datetime
from typing import Dict, List
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("codeflow")

class RequestLogger:
    def __init__(self):
        self.requests: List[Dict] = []
        self.max_requests = 1000  # Keep last 1000 requests
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        details: Dict = None
    ):
        """Log API request"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "details": details or {}
        }
        
        # Add to in-memory log
        self.requests.append(log_entry)
        
        # Keep only last N requests
        if len(self.requests) > self.max_requests:
            self.requests = self.requests[-self.max_requests:]
        
        # Log to console
        logger.info(f"{method} {path} - {status_code} ({duration_ms:.0f}ms)")
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict]:
        """Get recent requests"""
        return self.requests[-limit:]
    
    def get_stats(self) -> Dict:
        """Get request statistics"""
        if not self.requests:
            return {
                "total_requests": 0,
                "avg_duration_ms": 0,
                "status_codes": {}
            }
        
        # Calculate stats
        total = len(self.requests)
        avg_duration = sum(r["duration_ms"] for r in self.requests) / total
        
        status_codes = {}
        for req in self.requests:
            code = req["status_code"]
            status_codes[code] = status_codes.get(code, 0) + 1
        
        return {
            "total_requests": total,
            "avg_duration_ms": round(avg_duration, 2),
            "status_codes": status_codes
        }

# Global logger instance
request_logger = RequestLogger()