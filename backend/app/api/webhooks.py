"""
Webhook endpoints for Git providers
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import GitHubWebhook, AnalysisResult
from app.engine.orchestrator import AnalysisOrchestrator
from typing import Dict
import asyncio

router = APIRouter()

# Global orchestrator instance
orchestrator = AnalysisOrchestrator()

# In-memory storage for demo (replace with DB in production)
analysis_results = {}

@router.post("/webhook/github", status_code=202)
async def handle_github_webhook(
    payload: GitHubWebhook,
    background_tasks: BackgroundTasks
):
    """
    Handle GitHub webhook events
    Triggers background analysis
    """
    print(f"📨 Received GitHub webhook: {payload.commit_sha[:8]}")
    
    # Validate payload
    if not payload.files_changed:
        raise HTTPException(status_code=400, detail="No files changed")
    
    # For demo, analyze first changed file
    first_file = payload.files_changed[0]
    
    # Trigger background analysis
    background_tasks.add_task(
        run_analysis_background,
        file_path=first_file.path,
        code_diff=payload.diff or "",
        commit_sha=payload.commit_sha,
        repository=payload.repository
    )
    
    return {
        "status": "accepted",
        "message": "Analysis triggered",
        "commit": payload.commit_sha[:8]
    }

async def run_analysis_background(
    file_path: str,
    code_diff: str,
    commit_sha: str,
    repository: str
):
    """Background task for analysis"""
    try:
        result = await orchestrator.analyze_change(
            file_path=file_path,
            code_diff=code_diff,
            commit_sha=commit_sha,
            repository=repository
        )
        
        # Store result
        analysis_results[result["id"]] = result
        
        print(f"✅ Analysis {result['id']} completed and stored")
        
    except Exception as e:
        print(f"❌ Background analysis failed: {e}")