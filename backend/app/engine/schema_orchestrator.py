"""
Schema Change Orchestrator
Orchestrates analysis of database schema changes
"""

import asyncio
from typing import Dict, List
from datetime import datetime
import uuid
import os

from app.services.schema_analyzer import SchemaAnalyzer, SchemaChange
from app.services.sql_extractor import SQLExtractor
from app.engine.ai_analyzer import AIAnalyzer
from app.engine.risk_scorer import RiskScorer
from app.utils.neo4j_client import neo4j_client

# Try to import psycopg2 for direct PostgreSQL queries
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class SchemaChangeOrchestrator:
    """Orchestrates database schema change analysis"""
    
    def __init__(self):
        self.schema_analyzer = SchemaAnalyzer()
        self.sql_extractor = SQLExtractor()
        self.ai_analyzer = AIAnalyzer()
        self.risk_scorer = RiskScorer()
    
    async def analyze_schema_change(
        self,
        sql_statement: str,
        database_name: str,
        change_id: str = None,
        repository: str = None
    ) -> Dict:
        """
        Analyze impact of a database schema change
        
        Args:
            sql_statement: SQL DDL statement (ALTER TABLE, etc.)
            database_name: Name of the database
            change_id: Optional change identifier
            repository: Repository name
        
        Returns:
            Complete analysis result
        """
        analysis_id = change_id or str(uuid.uuid4())
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🗄️  Starting Schema Change Analysis: {analysis_id}")
        print(f"   Database: {database_name}")
        print(f"   SQL: {sql_statement[:100]}...")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Parse schema change
            print("Step 1/6: Parsing schema change...")
            schema_change = self.schema_analyzer.parse_schema_change(sql_statement)
            
            if not schema_change:
                # If we can't parse, try to extract at least the table name
                import re
                table_match = re.search(r'ALTER\s+TABLE\s+(?:`?(\w+)`?\.)?`?(\w+)`?', sql_statement.upper(), re.IGNORECASE)
                if table_match:
                    schema = table_match.group(1)
                    table_name = table_match.group(2)
                    schema_change = SchemaChange(
                        change_type="ALTER_TABLE",  # Generic - operation unknown
                        table_name=table_name.upper() if table_name else "UNKNOWN",
                        sql_statement=sql_statement
                    )
                    print(f"   ⚠️  Could not fully parse SQL, using generic ALTER_TABLE")
                else:
                    raise ValueError(f"Could not parse schema change from SQL statement: {sql_statement[:100]}")
            
            print(f"   ✅ Change Type: {schema_change.change_type}")
            print(f"   ✅ Table: {schema_change.table_name}")
            if schema_change.column_name:
                print(f"   ✅ Column: {schema_change.column_name}")
            elif schema_change.change_type == "ALTER_TABLE":
                print(f"   ⚠️  Operation details not available (incomplete SQL from event trigger)")
            
            # Step 2: Find code files that use this table/column
            print("Step 2/6: Finding code dependencies...")
            code_dependencies = await self._find_code_dependencies(
                schema_change.table_name,
                schema_change.column_name
            )
            
            print(f"   ✅ Found {len(code_dependencies)} code files using this table")
            
            # Step 3: Get database relationships
            print("Step 3/6: Analyzing database relationships...")
            db_relationships = await self._get_database_relationships(
                schema_change.table_name,
                database_name
            )
            
            print(f"   ✅ Found {len(db_relationships.get('forward', []))} forward relationships")
            print(f"   ✅ Found {len(db_relationships.get('reverse', []))} reverse relationships")
            
            # Step 4: Store in Neo4j
            print("Step 4/6: Storing in dependency graph...")
            await self._store_schema_in_neo4j(
                schema_change,
                database_name,
                code_dependencies,
                db_relationships
            )
            
            # Step 5: AI Analysis
            print("Step 5/6: Running AI analysis...")
            try:
                ai_insights = await self.ai_analyzer.analyze_schema_impact(
                    schema_change,
                    code_dependencies,
                    db_relationships
                )
            except Exception as ai_error:
                print(f"⚠️ AI analysis failed (non-blocking): {ai_error}")
                ai_insights = self._fallback_schema_analysis()
            
            # Step 6: Risk Scoring
            print("Step 6/6: Calculating risk score...")
            risk_score = self.risk_scorer.calculate_schema_risk(
                schema_change,
                code_dependencies,
                db_relationships,
                ai_insights
            )
            
            # Compile results
            result = self._compile_results(
                analysis_id,
                schema_change,
                database_name,
                code_dependencies,
                db_relationships,
                ai_insights,
                risk_score,
                start_time,
                repository,
                sql_statement
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ Schema Analysis Complete in {duration:.1f}s")
            print(f"   Risk Score: {risk_score['score']}/10 - {risk_score['level']}")
            print(f"   Affected Code Files: {len(code_dependencies)}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Schema analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _find_code_dependencies(
        self,
        table_name: str,
        column_name: str = None
    ) -> List[Dict]:
        """Find all code files that reference this table/column"""
        code_dependencies = []
        
        # Search in sample-repo directory
        # Try multiple possible paths (Docker vs local)
        possible_paths = [
            "/sample-repo",  # Docker mount path
            os.path.join(os.getcwd(), "sample-repo"),  # Local development
            os.path.join("/app", "sample-repo"),  # Alternative Docker path
            "sample-repo"  # Relative path
        ]
        
        repo_path = None
        for path in possible_paths:
            if os.path.exists(path):
                repo_path = path
                break
        
        if not repo_path:
            print(f"⚠️ Repository path not found. Tried: {possible_paths}")
            return code_dependencies
        
        print(f"   📁 Using repository path: {repo_path}")
        
        # Walk through repository
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in files:
                # Only process code files
                if not file.endswith(('.java', '.py', '.js', '.ts', '.sql')):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Extract table usage
                    table_usage = self.sql_extractor.extract_table_usage(relative_path, content)
                    
                    if table_name.lower() in [t.lower() for t in table_usage.keys()]:
                        usages = table_usage.get(table_name, [])
                        if not usages:
                            # Try case-insensitive match
                            for key, value in table_usage.items():
                                if key.lower() == table_name.lower():
                                    usages = value
                                    break
                        
                        # Filter by column if specified
                        if column_name:
                            filtered_usages = []
                            for usage in usages:
                                if column_name.lower() in [c.lower() for c in usage.get('columns', [])]:
                                    filtered_usages.append(usage)
                            usages = filtered_usages
                        
                        if usages:
                            code_dependencies.append({
                                "file_path": relative_path,
                                "table": table_name,
                                "column": column_name,
                                "usages": usages,
                                "usage_count": len(usages)
                            })
                
                except Exception as e:
                    print(f"⚠️ Error reading {file_path}: {e}")
                    continue
        
        return code_dependencies
    
    async def _get_database_relationships(
        self,
        table_name: str,
        database_name: str
    ) -> Dict:
        """Get database relationships (foreign keys, views, triggers, etc.) from PostgreSQL"""
        relationships = {"forward": [], "reverse": []}
        
        # Try to query PostgreSQL directly for actual relationships
        if not PSYCOPG2_AVAILABLE:
            print(f"   ⚠️ psycopg2 not available, using Neo4j fallback")
        else:
            try:
                # Get connection details from environment or use defaults
                # For Docker containers, use host.docker.internal to reach host PostgreSQL
                db_name = os.getenv("POSTGRES_DB", database_name)  # Use database_name parameter if env not set
                db_host = os.getenv("POSTGRES_HOST", "host.docker.internal")  # Docker-friendly default
                db_port = os.getenv("POSTGRES_PORT", "5432")
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "sabari")
                
                print(f"   🔌 Connecting to PostgreSQL: {db_host}:{db_port}/{db_name}")
                
                conn = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password,
                    connect_timeout=5  # 5 second timeout
                )

                
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get foreign keys (forward: tables this table references)
                    cursor.execute("""
                    SELECT 
                        c.conname AS constraint_name,
                        t2.relname AS referenced_table,
                        a2.attname AS referenced_column,
                        a1.attname AS local_column
                    FROM pg_constraint c
                    JOIN pg_class t1 ON c.conrelid = t1.oid
                    JOIN pg_class t2 ON c.confrelid = t2.oid
                    JOIN pg_attribute a1 ON a1.attrelid = t1.oid AND a1.attnum = ANY(c.conkey)
                    JOIN pg_attribute a2 ON a2.attrelid = t2.oid AND a2.attnum = ANY(c.confkey)
                    WHERE t1.relname = %s
                    AND c.contype = 'f'
                    """, (table_name.lower(),))
                    
                    for row in cursor.fetchall():
                        relationships["forward"].append({
                            "type": "FOREIGN_KEY",
                            "target_table": row["referenced_table"].upper(),
                            "local_column": row["local_column"],
                            "referenced_column": row["referenced_column"],
                            "constraint_name": row["constraint_name"]
                        })
                    
                    # Get reverse foreign keys (tables that reference this table)
                    cursor.execute("""
                    SELECT 
                        c.conname AS constraint_name,
                        t1.relname AS referencing_table,
                        a1.attname AS referencing_column,
                        a2.attname AS referenced_column
                    FROM pg_constraint c
                    JOIN pg_class t1 ON c.conrelid = t1.oid
                    JOIN pg_class t2 ON c.confrelid = t2.oid
                    JOIN pg_attribute a1 ON a1.attrelid = t1.oid AND a1.attnum = ANY(c.conkey)
                    JOIN pg_attribute a2 ON a2.attrelid = t2.oid AND a2.attnum = ANY(c.confkey)
                    WHERE t2.relname = %s
                    AND c.contype = 'f'
                    """, (table_name.lower(),))
                    
                    for row in cursor.fetchall():
                        relationships["reverse"].append({
                            "type": "REFERENCED_BY",
                            "source_table": row["referencing_table"].upper(),
                            "referencing_column": row["referencing_column"],
                            "referenced_column": row["referenced_column"],
                            "constraint_name": row["constraint_name"]
                        })
                    
                    # Get views that depend on this table
                    cursor.execute("""
                    SELECT DISTINCT
                        v.viewname AS view_name,
                        v.definition AS view_definition
                    FROM pg_views v
                    WHERE v.schemaname = 'public'
                    AND v.viewdefinition LIKE %s
                    """, (f'%{table_name.lower()}%',))
                    
                    for row in cursor.fetchall():
                        relationships["reverse"].append({
                            "type": "VIEW",
                            "source_table": row["view_name"].upper(),
                            "description": "View depends on this table"
                        })
                    
                    # Get triggers on this table
                    cursor.execute("""
                    SELECT 
                        t.tgname AS trigger_name,
                        p.proname AS function_name
                    FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_proc p ON t.tgfoid = p.oid
                    WHERE c.relname = %s
                    AND NOT t.tgisinternal
                    """, (table_name.lower(),))
                    
                    for row in cursor.fetchall():
                        relationships["reverse"].append({
                            "type": "TRIGGER",
                            "source_table": table_name.upper(),
                            "trigger_name": row["trigger_name"],
                            "function_name": row["function_name"]
                        })
                
                conn.close()
                
                print(f"   ✅ Found {len(relationships['forward'])} forward relationships from PostgreSQL")
                print(f"   ✅ Found {len(relationships['reverse'])} reverse relationships from PostgreSQL")
                
            except Exception as e:
                print(f"   ⚠️ Could not query PostgreSQL for relationships: {e}")
                # Fallback to Neo4j
                try:
                    neo4j_rels = await neo4j_client.get_table_relationships(table_name, database_name)
                    if neo4j_rels and (neo4j_rels.get("forward") or neo4j_rels.get("reverse")):
                        return neo4j_rels
                except Exception as neo4j_error:
                    print(f"   ⚠️ Could not get relationships from Neo4j: {neo4j_error}")
        
        # If still empty, try parsing from schema files
        if not relationships["forward"] and not relationships["reverse"]:
            schema_dir = os.path.join(os.getcwd(), "sample-repo", "banking-app", "src", "schema")
            if os.path.exists(schema_dir):
                for schema_file in os.listdir(schema_dir):
                    if schema_file.endswith('.sql'):
                        schema_path = os.path.join(schema_dir, schema_file)
                        try:
                            with open(schema_path, 'r', encoding='utf-8') as f:
                                ddl_content = f.read()
                            
                            tables = self.schema_analyzer.parse_ddl(ddl_content)
                            if table_name in tables:
                                table_rels = self.schema_analyzer.get_table_relationships(table_name)
                                relationships["forward"].extend(table_rels.get("forward", []))
                                relationships["reverse"].extend(table_rels.get("reverse", []))
                        except Exception as e:
                            print(f"⚠️ Error parsing schema file {schema_file}: {e}")
        
        return relationships
    
    async def _store_schema_in_neo4j(
        self,
        schema_change: SchemaChange,
        database_name: str,
        code_dependencies: List[Dict],
        db_relationships: Dict
    ):
        """Store schema change and relationships in Neo4j"""
        try:
            # Create database node
            await neo4j_client.create_database_node(
                name=database_name,
                properties={"type": "database"}
            )
            
            # Create table node
            await neo4j_client.create_table_node(
                name=schema_change.table_name,
                database=database_name,
                properties={
                    "change_type": schema_change.change_type,
                    "column_name": schema_change.column_name or "",
                    "last_modified": datetime.now().isoformat()
                }
            )
            
            # Store code dependencies (code files that use this table)
            for dep in code_dependencies:
                file_name = dep["file_path"].split("/")[-1]
                
                # Create module node for code file
                await neo4j_client.create_module_node(
                    name=file_name,
                    properties={"path": dep["file_path"]}
                )
                
                # Create relationship: Code file USES Table
                await neo4j_client.create_table_usage(
                    source_file=file_name,
                    target_table=schema_change.table_name,
                    database=database_name,
                    usage_count=dep["usage_count"],
                    column_name=schema_change.column_name or ""
                )
            
            # Store database relationships
            for rel in db_relationships.get("forward", []):
                if rel.get("target_table"):
                    await neo4j_client.create_table_relationship(
                        source_table=schema_change.table_name,
                        target_table=rel["target_table"],
                        database=database_name,
                        relationship_type=rel.get("type", "FOREIGN_KEY"),
                        properties=rel
                    )
            
            for rel in db_relationships.get("reverse", []):
                if rel.get("source_table"):
                    await neo4j_client.create_table_relationship(
                        source_table=rel["source_table"],
                        target_table=schema_change.table_name,
                        database=database_name,
                        relationship_type=rel.get("type", "REFERENCED_BY"),
                        properties=rel
                    )
            
            print("   ✅ Schema stored in Neo4j")
            
        except Exception as e:
            print(f"   ⚠️ Neo4j storage failed: {e}")
            # Don't fail entire analysis
    
    def _fallback_schema_analysis(self) -> Dict:
        """Fallback AI analysis for schema changes"""
        return {
            "summary": "Schema change detected. Manual review recommended.",
            "risks": [
                "Database schema changes can break application code",
                "Data migration may be required",
                "Backward compatibility concerns"
            ],
            "regulatory_concerns": "Schema changes may affect compliance reporting",
            "recommendations": [
                "Review all code that accesses this table",
                "Plan data migration strategy",
                "Test thoroughly in staging environment",
                "Consider backward compatibility"
            ],
            "deployment_advice": "Deploy during maintenance window"
        }
    
    def _compile_results(
        self,
        analysis_id: str,
        schema_change: SchemaChange,
        database_name: str,
        code_dependencies: List[Dict],
        db_relationships: Dict,
        ai_insights: Dict,
        risk_score: Dict,
        start_time: datetime,
        repository: str,
        sql_statement: str
    ) -> Dict:
        """Compile all results into final format"""
        
        affected_files = [dep["file_path"] for dep in code_dependencies]
        affected_tables = []
        
        # Add related tables from relationships
        for rel in db_relationships.get("forward", []):
            if rel.get("target_table"):
                affected_tables.append(rel["target_table"])
        
        for rel in db_relationships.get("reverse", []):
            if rel.get("source_table"):
                affected_tables.append(rel["source_table"])
        
        return {
            "id": analysis_id,
            "type": "schema_change",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "database": database_name,
            "repository": repository or "unknown",
            "schema_change": {
                "change_type": schema_change.change_type,
                "table_name": schema_change.table_name,
                "column_name": schema_change.column_name,
                "old_value": schema_change.old_value,
                "new_value": schema_change.new_value,
                "sql_statement": sql_statement
            },
            "risk_score": risk_score,
            "code_dependencies": code_dependencies,
            "database_relationships": db_relationships,
            "ai_insights": ai_insights,
            "affected_files": list(set(affected_files)),
            "affected_tables": list(set(affected_tables)),
            "summary": {
                "code_files_affected": len(affected_files),
                "tables_affected": len(set(affected_tables)),
                "total_usages": sum(dep["usage_count"] for dep in code_dependencies)
            },
            "metadata": {
                "analyzer_version": "1.0.0",
                "analysis_type": "schema_change"
            }
        }

