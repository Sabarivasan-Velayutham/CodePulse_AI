"""
Analysis management endpoints
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalysisRequest, AnalysisResult
from app.engine.orchestrator import AnalysisOrchestrator
from typing import List, Dict
import asyncio
from app.utils.cache import cache

router = APIRouter()

orchestrator = AnalysisOrchestrator()

# Shared storage with webhooks
from app.api.webhooks import analysis_results

@router.post("/analyze", response_model=Dict)
async def trigger_analysis(request: AnalysisRequest):
    """
    Manually trigger code analysis
    """
    print(f"🔍 Manual analysis requested for: {request.file_path}")
    
    try:
        result = await orchestrator.analyze_change(
            file_path=request.file_path,
            code_diff=request.diff or "",
            commit_sha="manual",
            repository=request.repository
        )
        
        # Store result
        analysis_results[result["id"]] = result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get specific analysis by ID (with caching)"""

    # Check cache first
    cache_key = f"analysis:{analysis_id}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        return cached_result
    
    # Not in cache, get from storage
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = analysis_results[analysis_id]

    # Cache the result
    cache.set(cache_key, result, ttl_seconds=3600)
    return result


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics (for monitoring)"""
    return cache.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear cache (admin function)"""
    cache.clear()
    return {"status": "cache cleared"}


@router.get("/analyses")
async def list_analyses(limit: int = 10):
    """List recent analyses"""
    # Get most recent analyses
    all_analyses = list(analysis_results.values())
    
    # Sort by timestamp (most recent first)
    sorted_analyses = sorted(
        all_analyses,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )
    
    return sorted_analyses[:limit]

@router.get("/graph/{file_name}")
async def get_dependency_graph(file_name: str):
    """Get dependency graph for a file"""
    from app.utils.neo4j_client import neo4j_client
    
    try:
        dependencies = await neo4j_client.get_dependencies(file_name)
        
        # Transform to graph format for visualization
        nodes = []
        links = []
        
        # Add source node
        nodes.append({
            "id": file_name,
            "name": file_name,
            "risk": "source"
        })
        
        # Add dependency nodes and links
        seen_nodes = {file_name}
        for dep in dependencies:
            module = dep["module"]
            if module not in seen_nodes:
                nodes.append({
                    "id": module,
                    "name": module,
                    "risk": "normal"
                })
                seen_nodes.add(module)
            
            links.append({
                "source": file_name,
                "target": module,
                "type": dep["relationships"][0] if dep["relationships"] else "DEPENDS_ON"
            })
        
        return {
            "nodes": nodes,
            "links": links
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))