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
    """Get dependency graph for a file (forward and reverse dependencies)"""
    from app.utils.neo4j_client import neo4j_client
    from urllib.parse import unquote
    
    # Decode URL-encoded file name
    file_name = unquote(file_name)
    
    try:
        # Try to get dependencies from Neo4j
        try:
            dependencies = await neo4j_client.get_dependencies(file_name)
        except Exception as neo4j_error:
            print(f"⚠️ Neo4j query failed: {neo4j_error}")
            # Fallback: Try to get from analysis results
            dependencies = []
            file_name_short = file_name.split("/")[-1]  # Get just filename
            
            for analysis in analysis_results.values():
                analysis_file = analysis.get("file_path", "")
                if analysis_file.endswith(file_name) or analysis_file.endswith(file_name_short):
                    # Build graph from analysis dependencies
                    deps = analysis.get("dependencies", {})
                    
                    # Add forward dependencies
                    for dep in deps.get("direct", []) + deps.get("indirect", []):
                        target = dep.get("target", "Unknown")
                        if target:
                            dependencies.append({
                                "module": target,
                                "distance": 1,
                                "relationships": [dep.get("type", "DEPENDS_ON")],
                                "line_numbers": [dep.get("line", 0)] if dep.get("line") else [],
                                "code_references": [dep.get("code_reference", "")] if dep.get("code_reference") else [],
                                "direction": "forward"
                            })
                    
                    # Add reverse dependencies
                    for dep in deps.get("reverse_direct", []) + deps.get("reverse_indirect", []):
                        source = dep.get("source", "Unknown")
                        if source:
                            dependencies.append({
                                "module": source,
                                "distance": 1,
                                "relationships": [dep.get("type", "DEPENDS_ON")],
                                "line_numbers": [dep.get("line", 0)] if dep.get("line") else [],
                                "code_references": [dep.get("code_reference", "")] if dep.get("code_reference") else [],
                                "direction": "reverse"
                            })
                    break
        
        # Transform to graph format for visualization
        nodes = []
        links = []
        nodes_map = {}  # Track nodes to avoid duplicates
        
        # Add source node
        source_node = {
            "id": file_name,
            "name": file_name,
            "risk": "source",
            "path": ""
        }
        nodes.append(source_node)
        nodes_map[file_name] = source_node
        
        # Process all dependencies (forward and reverse)
        for dep in dependencies:
            try:
                module = dep.get("module")
                if not module:
                    continue
                    
                direction = dep.get("direction", "forward")
                rel_types = dep.get("relationships", [])
                line_numbers = dep.get("line_numbers", [])
                code_refs = dep.get("code_references", [])
                
                # Determine risk level based on distance
                distance = dep.get("distance", 1)
                if distance == 1:
                    risk = "high" if direction == "reverse" else "medium"
                elif distance == 2:
                    risk = "medium"
                else:
                    risk = "low"
                
                # Add node if not seen
                if module not in nodes_map:
                    node = {
                        "id": module,
                        "name": module,
                        "risk": risk,
                        "path": ""
                    }
                    nodes.append(node)
                    nodes_map[module] = node
                
                # Create link
                if direction == "reverse":
                    # Reverse: other module depends on source file
                    source = module
                    target = file_name
                else:
                    # Forward: source file depends on other module
                    source = file_name
                    target = module
                
                # Safely extract values
                rel_type = rel_types[0] if rel_types and len(rel_types) > 0 else "DEPENDS_ON"
                line_num = line_numbers[0] if line_numbers and len(line_numbers) > 0 and line_numbers[0] is not None else None
                code_ref = code_refs[0] if code_refs and len(code_refs) > 0 and code_refs[0] else ""
                
                link = {
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "distance": distance,
                    "direction": direction,
                    "line_number": line_num,
                    "code_reference": code_ref if code_ref else ""
                }
                links.append(link)
            except Exception as e:
                print(f"⚠️ Error processing dependency: {e}")
                continue
        
        # If no dependencies found, return empty graph with just source node
        return {
            "nodes": nodes,
            "links": links
        }
        
    except Exception as e:
        print(f"❌ Error getting dependency graph: {e}")
        import traceback
        traceback.print_exc()
        # Return empty graph instead of error to prevent UI crash
        return {
            "nodes": [{
                "id": file_name,
                "name": file_name,
                "risk": "source",
                "path": ""
            }],
            "links": []
        }