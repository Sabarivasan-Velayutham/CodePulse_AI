from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    """Risk level enumeration"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class FileChange(BaseModel):
    """Represents a changed file"""
    path: str = Field(..., description="File path")
    status: str = Field(..., description="modified/added/deleted")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines deleted")
    
    class Config:
        json_schema_extra = {
            "example": {
                "path": "src/payment/PaymentProcessor.java",
                "status": "modified",
                "additions": 5,
                "deletions": 2
            }
        }

class GitHubWebhook(BaseModel):
    """GitHub webhook payload"""
    event: str = Field(..., description="Event type (push, pull_request)")
    repository: str = Field(..., description="Repository name")
    commit_sha: str = Field(..., description="Commit SHA")
    author: str = Field(..., description="Author email")
    branch: str = Field(..., description="Branch name")
    files_changed: List[FileChange] = Field(..., description="Changed files")
    diff: Optional[str] = Field(None, description="Code diff")

class Dependency(BaseModel):
    """Represents a code dependency"""
    source: str = Field(..., description="Source module")
    target: str = Field(..., description="Target module")
    relationship_type: str = Field(..., description="CALLS/IMPORTS/READS/WRITES")
    line_number: Optional[int] = None

class RiskScore(BaseModel):
    """Risk scoring result"""
    score: float = Field(..., ge=0, le=10, description="Risk score 0-10")
    level: RiskLevel = Field(..., description="Risk level")
    color: str = Field(..., description="Color code for UI")
    breakdown: Dict[str, float] = Field(..., description="Score breakdown")

class AIInsights(BaseModel):
    """AI-generated insights"""
    summary: str = Field(..., description="Impact summary")
    risks: List[str] = Field(..., description="Identified risks")
    regulatory_concerns: str = Field(..., description="Compliance concerns")
    recommendations: List[str] = Field(..., description="Recommendations")

class AnalysisResult(BaseModel):
    """Complete analysis result"""
    id: str = Field(..., description="Analysis ID")
    commit_sha: str = Field(..., description="Commit SHA")
    file_path: str = Field(..., description="Analyzed file")
    timestamp: datetime = Field(default_factory=datetime.now)
    risk_score: RiskScore
    dependencies: List[Dependency]
    ai_insights: AIInsights
    affected_modules: List[str] = Field(..., description="List of affected modules")
    test_scenarios: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "analysis_123",
                "commit_sha": "abc123",
                "file_path": "PaymentProcessor.java",
                "risk_score": {
                    "score": 8.5,
                    "level": "CRITICAL",
                    "color": "#dc3545"
                }
            }
        }

class AnalysisRequest(BaseModel):
    """Manual analysis request"""
    file_path: str = Field(..., description="Path to file to analyze")
    repository: str = Field(..., description="Repository name")
    diff: Optional[str] = Field(None, description="Code diff (optional)")
    commit_sha: Optional[str] = Field(None, description="Commit SHA")
    commit_message: Optional[str] = Field(None, description="Commit message")