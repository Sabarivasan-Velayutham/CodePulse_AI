"""
Database Schema Change Analysis Endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import SchemaChangeRequest
from app.engine.schema_orchestrator import SchemaChangeOrchestrator
from typing import Dict
from app.api.webhooks import analysis_results

router = APIRouter()

schema_orchestrator = SchemaChangeOrchestrator()


@router.post("/schema/analyze", response_model=Dict)
async def analyze_schema_change(
    request: SchemaChangeRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze impact of a database schema change
    
    Can be triggered by:
    - Database migration tools (Liquibase, Flyway, Alembic)
    - Manual DDL execution
    - Database webhook/trigger
    """
    print(f"🗄️  Schema change analysis requested")
    print(f"   Database: {request.database_name}")
    print(f"   SQL: {request.sql_statement[:100]}...")
    
    try:
        # Run analysis (can be async/background if needed)
        result = await schema_orchestrator.analyze_schema_change(
            sql_statement=request.sql_statement,
            database_name=request.database_name,
            change_id=request.change_id,
            repository=request.repository
        )
        
        # Store result
        analysis_results[result["id"]] = result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema/webhook", status_code=202)
async def schema_change_webhook(
    request: SchemaChangeRequest,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for database schema changes
    
    This can be called by:
    - Database triggers (MySQL, PostgreSQL)
    - Migration tools (Liquibase, Flyway, Alembic)
    - CI/CD pipelines
    - Manual API calls
    
    Returns 202 Accepted (analysis runs in background)
    """
    print(f"📨 Received schema change webhook")
    print(f"   Database: {request.database_name}")
    print(f"   SQL: {request.sql_statement[:100]}...")
    
    # Trigger background analysis
    background_tasks.add_task(
        run_schema_analysis_background,
        sql_statement=request.sql_statement,
        database_name=request.database_name,
        change_id=request.change_id,
        repository=request.repository
    )
    
    return {
        "status": "accepted",
        "message": "Schema change analysis triggered",
        "database": request.database_name
    }


async def run_schema_analysis_background(
    sql_statement: str,
    database_name: str,
    change_id: str = None,
    repository: str = None
):
    """Background task for schema analysis"""
    try:
        result = await schema_orchestrator.analyze_schema_change(
            sql_statement=sql_statement,
            database_name=database_name,
            change_id=change_id,
            repository=repository
        )
        analysis_results[result["id"]] = result
    except Exception as e:
        print(f"❌ Background schema analysis failed: {e}")


@router.get("/schema/analysis/{analysis_id}")
async def get_schema_analysis(analysis_id: str):
    """Get schema change analysis by ID"""
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = analysis_results[analysis_id]
    
    # Verify it's a schema change analysis
    if result.get("type") != "schema_change":
        raise HTTPException(status_code=400, detail="Not a schema change analysis")
    
    return result


@router.get("/schema/table/{table_name}")
async def get_table_dependencies(table_name: str, database_name: str = "banking_db"):
    """Get all dependencies for a database table"""
    from app.utils.neo4j_client import neo4j_client
    
    try:
        # Get code dependencies
        code_deps = await neo4j_client.get_table_code_dependencies(table_name, database_name)
        
        # Get database relationships
        db_rels = await neo4j_client.get_table_relationships(table_name, database_name)
        
        return {
            "table_name": table_name,
            "database": database_name,
            "code_dependencies": code_deps,
            "database_relationships": db_rels
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/graph/{table_name}")
async def get_table_dependency_graph(table_name: str, database_name: str = "banking_db"):
    """Get dependency graph for a database table (for visualization)
    
    Includes:
    - Direct code dependencies (files that use the table)
    - Transitive code dependencies (files that depend on files using the table)
    - Database relationships (foreign keys, views, triggers)
    """
    from app.utils.neo4j_client import neo4j_client
    from urllib.parse import unquote
    
    # Decode URL-encoded table name
    table_name = unquote(table_name)
    
    try:
        # Get code dependencies (code files that use this table)
        code_deps = await neo4j_client.get_table_code_dependencies(table_name, database_name)
        
        # Get database relationships (other tables related to this one)
        db_rels = await neo4j_client.get_table_relationships(table_name, database_name)
        
        # Transform to graph format
        nodes = []
        links = []
        nodes_map = {}
        processed_files = set()  # Track files we've already processed for transitive deps
        
        # Add table node (source)
        table_node = {
            "id": f"table:{table_name}",
            "name": table_name,
            "type": "table",
            "risk": "source"
        }
        nodes.append(table_node)
        nodes_map[f"table:{table_name}"] = table_node
        
        # Add code file nodes (code that directly uses this table)
        for code_dep in code_deps:
            file_name = code_dep.get("file_name", "Unknown")
            file_id = f"file:{file_name}"
            
            if file_id not in nodes_map:
                file_node = {
                    "id": file_id,
                    "name": file_name,
                    "type": "code",
                    "risk": "medium"
                }
                nodes.append(file_node)
                nodes_map[file_id] = file_node
            
            # Create link: code file USES table
            links.append({
                "source": file_id,
                "target": f"table:{table_name}",
                "type": "USES_TABLE",
                "usage_count": code_dep.get("usage_count", 1)
            })
            
            # Find transitive dependencies: files that depend on this file
            if file_name not in processed_files:
                processed_files.add(file_name)
                try:
                    # Get reverse dependencies (files that depend on this file)
                    transitive_deps = await neo4j_client.get_dependencies(file_name, max_depth=2)
                    
                    for trans_dep in transitive_deps:
                        if trans_dep.get("direction") == "reverse":  # Others depend on this file
                            dep_module = trans_dep.get("module")
                            if dep_module and dep_module != file_name:
                                dep_file_id = f"file:{dep_module}"
                                
                                # Add the dependent file node
                                if dep_file_id not in nodes_map:
                                    dep_file_node = {
                                        "id": dep_file_id,
                                        "name": dep_module,
                                        "type": "code",
                                        "risk": "low"
                                    }
                                    nodes.append(dep_file_node)
                                    nodes_map[dep_file_id] = dep_file_node
                                
                                # Create link: dependent file -> file using table
                                links.append({
                                    "source": dep_file_id,
                                    "target": file_id,
                                    "type": trans_dep.get("relationships", ["DEPENDS_ON"])[0] if trans_dep.get("relationships") else "DEPENDS_ON",
                                    "distance": trans_dep.get("distance", 1)
                                })
                except Exception as e:
                    print(f"⚠️ Error getting transitive dependencies for {file_name}: {e}")
                    # Continue with other files
        
        # Add related table nodes (database relationships)
        for rel in db_rels.get("forward", []):
            target_table = rel.get("target_table")
            if target_table:
                target_id = f"table:{target_table}"
                if target_id not in nodes_map:
                    target_node = {
                        "id": target_id,
                        "name": target_table,
                        "type": "table",
                        "risk": "low"
                    }
                    nodes.append(target_node)
                    nodes_map[target_id] = target_node
                
                links.append({
                    "source": f"table:{table_name}",
                    "target": target_id,
                    "type": rel.get("type", "FOREIGN_KEY"),
                    "direction": "forward"
                })
        
        for rel in db_rels.get("reverse", []):
            rel_type = rel.get("type", "REFERENCED_BY")
            source_table = rel.get("source_table")
            
            if source_table:
                # Handle VIEW relationships specially
                if rel_type == "VIEW":
                    view_id = f"view:{source_table}"
                    if view_id not in nodes_map:
                        view_node = {
                            "id": view_id,
                            "name": source_table,
                            "type": "view",
                            "risk": "medium"
                        }
                        nodes.append(view_node)
                        nodes_map[view_id] = view_node
                    
                    links.append({
                        "source": view_id,
                        "target": f"table:{table_name}",
                        "type": "VIEW_DEPENDS_ON",
                        "direction": "reverse",
                        "description": rel.get("description", "View depends on this table")
                    })
                else:
                    # Regular table relationships
                    source_id = f"table:{source_table}"
                    if source_id not in nodes_map:
                        source_node = {
                            "id": source_id,
                            "name": source_table,
                            "type": "table",
                            "risk": "low"
                        }
                        nodes.append(source_node)
                        nodes_map[source_id] = source_node
                    
                    links.append({
                        "source": source_id,
                        "target": f"table:{table_name}",
                        "type": rel_type,
                        "direction": "reverse"
                    })
        
        return {
            "nodes": nodes,
            "links": links
        }
        
    except Exception as e:
        print(f"❌ Error getting table dependency graph: {e}")
        import traceback
        traceback.print_exc()
        # Return empty graph with just table node
        return {
            "nodes": [{
                "id": f"table:{table_name}",
                "name": table_name,
                "type": "table",
                "risk": "source"
            }],
            "links": []
        }

