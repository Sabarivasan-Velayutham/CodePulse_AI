"""
API Contract Change Analysis Endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import AnalysisRequest
from app.engine.api_contract_orchestrator import APIContractOrchestrator
from app.utils.neo4j_client import neo4j_client
from typing import Dict
from app.api.webhooks import analysis_results

router = APIRouter()

api_contract_orchestrator = APIContractOrchestrator()


@router.post("/api/contract/analyze", response_model=Dict)
async def analyze_api_contract_change(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze API contract changes in a code file
    
    Can be triggered by:
    - GitHub webhook (when API-related files change)
    - Manual API call
    - CI/CD pipeline
    """
    print(f"🔌 API contract change analysis requested")
    print(f"   File: {request.file_path}")
    print(f"   Repository: {request.repository}")
    
    try:
        # Run analysis
        result = await api_contract_orchestrator.analyze_api_contract_change(
            file_path=request.file_path,
            code_diff=request.diff or "",
            commit_sha=request.commit_sha or "manual",
            repository=request.repository,
            commit_message=request.commit_message or ""
        )
        
        # Store result
        analysis_results[result["id"]] = result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/contract/analysis/{analysis_id}")
async def get_api_contract_analysis(analysis_id: str):
    """Get API contract analysis results by ID"""
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = analysis_results[analysis_id]
    
    # Verify it's an API contract analysis
    if result.get("type") != "api_contract_change":
        raise HTTPException(status_code=404, detail="Analysis is not an API contract analysis")
    
    return result


@router.get("/api/contract/consumers")
async def get_api_consumers(endpoint: str, method: str = "GET"):
    """
    Get all consumers of a specific API endpoint
    
    Query parameters:
    - endpoint: API endpoint path (e.g., '/api/payments/process')
    - method: HTTP method (GET, POST, etc.)
    """
    try:
        consumers = await neo4j_client.get_api_consumers(endpoint, method)
        return {
            "endpoint": endpoint,
            "method": method,
            "consumers": consumers,
            "count": len(consumers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

