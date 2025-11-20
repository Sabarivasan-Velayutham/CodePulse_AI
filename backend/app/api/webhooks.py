"""
Webhook endpoints for Git providers
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import GitHubWebhook, AnalysisResult
from app.engine.orchestrator import AnalysisOrchestrator
from app.engine.api_contract_orchestrator import APIContractOrchestrator
from typing import Dict
import asyncio
import re

router = APIRouter()

# Global orchestrator instances
orchestrator = AnalysisOrchestrator()
api_contract_orchestrator = APIContractOrchestrator()

# In-memory storage for demo (replace with DB in production)
analysis_results = {}

@router.post("/webhook/github", status_code=202)
async def handle_github_webhook(
    payload: GitHubWebhook,
    background_tasks: BackgroundTasks
):
    """
    Handle GitHub webhook events
    Triggers background analysis (code change or API contract change)
    """
    print(f"📨 Received GitHub webhook: {payload.commit_sha[:8]}")
    
    # Validate payload
    if not payload.files_changed:
        raise HTTPException(status_code=400, detail="No files changed")
    
    # For demo, analyze first changed file
    first_file = payload.files_changed[0]
    file_path = first_file.path
    
    # Detect if file contains API definitions
    is_api_file = _is_api_related_file(file_path, payload.diff or "")
    
    if is_api_file:
        # Route to API contract analysis
        print(f"   🔌 Detected API-related file, routing to API contract analysis")
        background_tasks.add_task(
            run_api_contract_analysis_background,
            file_path=file_path,
            code_diff=payload.diff or "",
            commit_sha=payload.commit_sha,
            repository=payload.repository,
            commit_message=getattr(payload, 'commit_message', '')
        )
    else:
        # Route to regular code analysis
        background_tasks.add_task(
            run_analysis_background,
            file_path=file_path,
            code_diff=payload.diff or "",
            commit_sha=payload.commit_sha,
            repository=payload.repository
        )
    
    return {
        "status": "accepted",
        "message": "Analysis triggered",
        "commit": payload.commit_sha[:8],
        "analysis_type": "api_contract" if is_api_file else "code_change"
    }


def _is_api_related_file(file_path: str, code_diff: str) -> bool:
    """Detect if a file contains API endpoint definitions"""
    file_lower = file_path.lower()
    
    # Check file name patterns
    api_patterns = [
        r'controller', r'route', r'api', r'endpoint', r'rest',
        r'handler', r'service\.py', r'router', r'app\.py'
    ]
    
    for pattern in api_patterns:
        if re.search(pattern, file_lower):
            return True
    
    # Check code diff for API-related patterns
    if code_diff:
        diff_lower = code_diff.lower()
        api_keywords = [
            '@restcontroller', '@controller', '@getmapping', '@postmapping',
            '@putmapping', '@deletemapping', '@requestmapping',
            '@app.route', '@router.', 'app.get', 'app.post', 'app.put', 'app.delete',
            'fastapi', 'flask', 'express', 'router.get', 'router.post'
        ]
        
        for keyword in api_keywords:
            if keyword in diff_lower:
                return True
    
    return False

async def run_analysis_background(
    file_path: str,
    code_diff: str,
    commit_sha: str,
    repository: str
):
    """Background task for code change analysis"""
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


async def run_api_contract_analysis_background(
    file_path: str,
    code_diff: str,
    commit_sha: str,
    repository: str,
    commit_message: str = ""
):
    """Background task for API contract change analysis"""
    try:
        result = await api_contract_orchestrator.analyze_api_contract_change(
            file_path=file_path,
            code_diff=code_diff,
            commit_sha=commit_sha,
            repository=repository,
            commit_message=commit_message
        )
        
        # Store result
        analysis_results[result["id"]] = result
        
        print(f"✅ API Contract Analysis {result['id']} completed and stored")
        
    except Exception as e:
        print(f"❌ API Contract background analysis failed: {e}")