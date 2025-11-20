"""
Schema Change Orchestrator
Orchestrates analysis of database schema changes
"""

import asyncio
from typing import Dict, List, Tuple
from datetime import datetime
import uuid
import os

from app.services.schema_analyzer import SchemaAnalyzer, SchemaChange
from app.services.mongodb_schema_analyzer import MongoDBSchemaAnalyzer, MongoSchemaChange
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

# Try to import pymongo for MongoDB queries
try:
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class SchemaChangeOrchestrator:
    """Orchestrates database schema change analysis"""
    
    def __init__(self):
        self.schema_analyzer = SchemaAnalyzer()
        self.mongodb_analyzer = MongoDBSchemaAnalyzer()
        self.sql_extractor = SQLExtractor()
        self.ai_analyzer = AIAnalyzer()
        self.risk_scorer = RiskScorer()
    
    def _detect_database_type(self, database_name: str, operation_statement: str, database_type: str = None) -> str:
        """Detect database type from database name, operation, or explicit type"""
        if database_type:
            return database_type.lower()
        
        # Check database name
        if database_name.startswith("mongodb_") or "mongo" in database_name.lower():
            return "mongodb"
        
        # Check operation statement
        op_lower = operation_statement.lower()
        if any(keyword in op_lower for keyword in ["create collection", "drop collection", "createindex", "dropindex", "db."]):
            return "mongodb"
        
        # Default to PostgreSQL
        return "postgresql"
    
    async def analyze_schema_change(
        self,
        sql_statement: str,
        database_name: str,
        change_id: str = None,
        repository: str = None,
        database_type: str = None,
        github_repo_url: str = None,
        github_branch: str = "main"
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
        
        # Detect database type
        db_type = self._detect_database_type(database_name, sql_statement, database_type)
        
        print(f"\n{'='*60}")
        print(f"🗄️  Starting Schema Change Analysis: {analysis_id}")
        print(f"   Database: {database_name} ({db_type.upper()})")
        print(f"   Operation: {sql_statement[:100]}...")
        print(f"{'='*60}\n")
        
        # Route to MongoDB or PostgreSQL analyzer
        if db_type == "mongodb":
            return await self._analyze_mongodb_schema_change(
                sql_statement, database_name, change_id, repository, analysis_id, github_repo_url, github_branch
            )
        
        # PostgreSQL analysis (existing code)
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
            
            # If we have a generic ALTER_TABLE, try to query PostgreSQL for actual change details
            if schema_change.change_type == "ALTER_TABLE" and not schema_change.column_name:
                schema_change = await self._enhance_schema_change_from_db(schema_change, database_name)
            
            print(f"   ✅ Change Type: {schema_change.change_type}")
            print(f"   ✅ Table: {schema_change.table_name}")
            if schema_change.column_name:
                print(f"   ✅ Column: {schema_change.column_name}")
            if schema_change.old_value:
                print(f"   ✅ Old Value: {schema_change.old_value}")
            if schema_change.new_value:
                print(f"   ✅ New Value: {schema_change.new_value}")
            if schema_change.change_type == "ALTER_TABLE" and not schema_change.column_name:
                print(f"   ⚠️  Operation details not available (incomplete SQL from event trigger)")
            
            # Step 2: Find code files that use this table/column
            print("Step 2/6: Finding code dependencies...")
            # Get GitHub repo URL from parameter, environment, or repository parameter
            # Priority: github_repo_url parameter > GITHUB_REPO_URL_POSTGRESQL env > repository parameter
            final_github_repo_url = github_repo_url or os.getenv("GITHUB_REPO_URL_POSTGRESQL") or repository
            final_github_branch = github_branch or os.getenv("GITHUB_BRANCH", "main")
            
            code_dependencies, repo_path = await self._find_code_dependencies(
                schema_change.table_name,
                schema_change.column_name,
                database_type="postgresql",
                github_repo_url=final_github_repo_url if final_github_repo_url and ("github.com" in final_github_repo_url or "/" in final_github_repo_url) else None,
                github_branch=final_github_branch
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
                    db_relationships,
                    repository_path=repo_path
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
                sql_statement,
                database_type="postgresql"
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
        column_name: str = None,
        database_type: str = "postgresql",
        github_repo_url: str = None,
        github_branch: str = "main"
    ) -> Tuple[List[Dict], str]:
        """Find all code files that reference this table/column or collection
        
        Args:
            table_name: Table or collection name
            column_name: Optional column/field name
            database_type: "postgresql" or "mongodb" - determines which patterns to use
            github_repo_url: Optional GitHub repository URL (e.g., "owner/repo" or full URL)
            github_branch: GitHub branch to use (default: main)
        """
        code_dependencies = []
        
        repo_path = None
        
        # If GitHub repository URL is provided, fetch from GitHub
        if github_repo_url:
            from app.utils.github_fetcher import github_fetcher
            
            # Determine subfolder based on database type
            # For MongoDB: fetch banking-app-mongodb subfolder
            # For PostgreSQL: fetch banking-app or python-analytics subfolders
            subfolder = None
            if database_type == "mongodb":
                subfolder = "banking-app-mongodb"
            # For PostgreSQL, we can search the whole repo or specific folders
            
            print(f"   🔗 Fetching from GitHub: {github_repo_url}")
            repo_path = github_fetcher.fetch_repository(
                repo_url=github_repo_url,
                branch=github_branch,
                subfolder=subfolder
            )
            
            if not repo_path:
                print(f"   ⚠️ Failed to fetch from GitHub, falling back to local repository")
                # Fall through to local repository search
        
        # If no GitHub repo or fetch failed, search in local sample-repo directory
        if not repo_path:
            # Try multiple possible paths (Docker vs local)
            possible_paths = [
                "/sample-repo",  # Docker mount path
                os.path.join(os.getcwd(), "sample-repo"),  # Local development
                os.path.join("/app", "sample-repo"),  # Alternative Docker path
                "sample-repo"  # Relative path
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    repo_path = path
                    break
            
            if not repo_path:
                print(f"⚠️ Repository path not found. Tried: {possible_paths}")
                return code_dependencies, None
        
        print(f"   📁 Using repository path: {repo_path}")
        print(f"   🔍 Database type: {database_type.upper()}")
        
        # Determine which folders to search based on database type
        # For MongoDB: search in banking-app-mongodb folder
        # For PostgreSQL: search in banking-app and python-analytics folders
        search_folders = []
        if database_type == "mongodb":
            search_folders = ["banking-app-mongodb"]
        else:
            search_folders = ["banking-app", "python-analytics"]
        
        # Walk through repository, but only in relevant folders
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            # Check if we're in a relevant folder
            relative_root = os.path.relpath(root, repo_path)
            
            # At root level, filter directories to only search in relevant folders
            if relative_root == ".":
                dirs[:] = [d for d in dirs if d in search_folders]
            else:
                # Check if current path is in a relevant folder
                path_parts = relative_root.split(os.sep)
                # Check if any of the search folders is in the path
                if not any(folder in path_parts for folder in search_folders):
                    # Skip this directory tree
                    dirs[:] = []
                    continue
            
            for file in files:
                # For MongoDB: exclude SQL files (they're PostgreSQL-specific)
                # For PostgreSQL: include SQL files
                if database_type == "mongodb" and file.endswith('.sql'):
                    continue
                
                # Only process code files
                if not file.endswith(('.java', '.py', '.js', '.ts', '.sql')):
                    continue
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Extract table/collection usage based on database type
                    if database_type == "mongodb":
                        # For MongoDB: only look for MongoDB collection patterns
                        table_usage = self.sql_extractor.extract_mongodb_usage_only(relative_path, content, table_name)
                    else:
                        # For PostgreSQL: use full extraction (SQL + ORM + heuristics)
                        table_usage = self.sql_extractor.extract_table_usage(relative_path, content)
                    
                    if table_name.lower() in [t.lower() for t in table_usage.keys()]:
                        usages = table_usage.get(table_name, [])
                        if not usages:
                            # Try case-insensitive match
                            for key, value in table_usage.items():
                                if key.lower() == table_name.lower():
                                    usages = value
                                    break
                        
                        # Filter by column/field if specified
                        if column_name:
                            filtered_usages = []
                            for usage in usages:
                                # For MongoDB, check field_name; for PostgreSQL, check columns
                                if database_type == "mongodb":
                                    # MongoDB: check if field is mentioned in context
                                    context = usage.get('context', '').lower()
                                    if column_name.lower() in context or column_name.lower() in usage.get('full_query', '').lower():
                                        filtered_usages.append(usage)
                                else:
                                    # PostgreSQL: check columns list
                                    if column_name.lower() in [c.lower() for c in usage.get('columns', [])]:
                                        filtered_usages.append(usage)
                            usages = filtered_usages
                        
                        if usages:
                            code_dependencies.append({
                                "file_path": relative_path,
                                "table": table_name,
                                "column": column_name,
                                "usages": usages,
                                "usage_count": len(usages),
                                "database_type": database_type
                            })
                
                except Exception as e:
                    print(f"⚠️ Error reading {file_path}: {e}")
                    continue
        
        return code_dependencies, repo_path
    
    async def _enhance_schema_change_from_db(
        self,
        schema_change: SchemaChange,
        database_name: str
    ) -> SchemaChange:
        """
        Try to enhance schema change details by:
        1. Parsing the SQL statement more carefully (regex)
        2. Querying PostgreSQL system catalogs to detect what actually changed
        """
        if not PSYCOPG2_AVAILABLE:
            return schema_change
        
        try:
            import re
            sql_upper = schema_change.sql_statement.upper()
            
            # Method 1: Try regex parsing on the SQL string
            # Try to detect ADD COLUMN from common patterns (handle incomplete SQL)
            # Pattern: ALTER TABLE ... ADD [COLUMN] column_name [TYPE]
            if 'ADD' in sql_upper and 'COLUMN' in sql_upper:
                # More flexible pattern that handles incomplete SQL
                # Match: ADD COLUMN column_name or ADD column_name
                col_match = re.search(r'ADD\s+(?:COLUMN\s+)?(?:`?(\w+)`?|(\w+))', sql_upper, re.IGNORECASE)
                if col_match:
                    column_name = col_match.group(1) or col_match.group(2)
                    if column_name:
                        schema_change.change_type = "ADD_COLUMN"
                        schema_change.column_name = column_name.upper()
                        # Try to get column type (may not be present in incomplete SQL)
                        type_match = re.search(r'ADD\s+(?:COLUMN\s+)?`?\w+`?\s+(\w+(?:\([^)]+\))?)', sql_upper, re.IGNORECASE)
                        if type_match:
                            schema_change.new_value = type_match.group(1)
                        print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                        return schema_change
            
            # Also try without COLUMN keyword (some databases allow ADD column_name directly)
            if 'ADD' in sql_upper and 'COLUMN' not in sql_upper:
                # Check if it's likely an ADD COLUMN (not ADD CONSTRAINT)
                if 'CONSTRAINT' not in sql_upper:
                    col_match = re.search(r'ADD\s+`?(\w+)`?\s+(\w+(?:\([^)]+\))?)', sql_upper, re.IGNORECASE)
                    if col_match:
                        schema_change.change_type = "ADD_COLUMN"
                        schema_change.column_name = col_match.group(1).upper()
                        schema_change.new_value = col_match.group(2)
                        print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                        return schema_change
            
            # Try to detect DROP COLUMN (check this BEFORE ADD to avoid false positives)
            # Pattern: DROP COLUMN column_name or DROP column_name
            if 'DROP' in sql_upper and 'COLUMN' in sql_upper:
                # More flexible pattern for incomplete SQL
                col_match = re.search(r'DROP\s+(?:COLUMN\s+)?(?:`?(\w+)`?|(\w+))', sql_upper, re.IGNORECASE)
                if col_match:
                    column_name = col_match.group(1) or col_match.group(2)
                    if column_name:
                        schema_change.change_type = "DROP_COLUMN"
                        schema_change.column_name = column_name.upper()
                        print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                        return schema_change
            
            # Also try DROP without COLUMN keyword
            if 'DROP' in sql_upper and 'COLUMN' not in sql_upper:
                # Check if it's likely DROP COLUMN (not DROP TABLE or DROP CONSTRAINT)
                if 'TABLE' not in sql_upper and 'CONSTRAINT' not in sql_upper:
                    col_match = re.search(r'DROP\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                    if col_match:
                        schema_change.change_type = "DROP_COLUMN"
                        schema_change.column_name = col_match.group(1).upper()
                        print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                        return schema_change
            
            # Try to detect ALTER COLUMN / MODIFY COLUMN
            if 'ALTER' in sql_upper and 'COLUMN' in sql_upper and 'TYPE' in sql_upper:
                col_match = re.search(r'ALTER\s+COLUMN\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if col_match:
                    schema_change.change_type = "MODIFY_COLUMN"
                    schema_change.column_name = col_match.group(1).upper()
                    # Try to get new type
                    type_match = re.search(r'TYPE\s+(\w+(?:\([^)]+\))?)', sql_upper, re.IGNORECASE)
                    if type_match:
                        schema_change.new_value = type_match.group(1)
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect RENAME COLUMN
            if 'RENAME' in sql_upper and 'COLUMN' in sql_upper and 'TO' in sql_upper:
                rename_match = re.search(r'RENAME\s+COLUMN\s+`?(\w+)`?\s+TO\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if rename_match:
                    schema_change.change_type = "RENAME_COLUMN"
                    schema_change.column_name = rename_match.group(1).upper()
                    schema_change.old_value = rename_match.group(1).upper()
                    schema_change.new_value = rename_match.group(2).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect SET DEFAULT
            if 'SET' in sql_upper and 'DEFAULT' in sql_upper and 'ALTER' in sql_upper and 'COLUMN' in sql_upper:
                set_default_match = re.search(r'ALTER\s+COLUMN\s+`?(\w+)`?\s+SET\s+DEFAULT\s+(.+?)(?:\s|$)', sql_upper, re.IGNORECASE)
                if set_default_match:
                    schema_change.change_type = "SET_DEFAULT"
                    schema_change.column_name = set_default_match.group(1).upper()
                    default_value = set_default_match.group(2).strip().rstrip(';')
                    schema_change.new_value = default_value
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect DROP DEFAULT
            if 'DROP' in sql_upper and 'DEFAULT' in sql_upper and 'ALTER' in sql_upper and 'COLUMN' in sql_upper:
                drop_default_match = re.search(r'ALTER\s+COLUMN\s+`?(\w+)`?\s+DROP\s+DEFAULT', sql_upper, re.IGNORECASE)
                if drop_default_match:
                    schema_change.change_type = "DROP_DEFAULT"
                    schema_change.column_name = drop_default_match.group(1).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect SET NOT NULL
            if 'SET' in sql_upper and 'NOT' in sql_upper and 'NULL' in sql_upper and 'ALTER' in sql_upper and 'COLUMN' in sql_upper:
                set_not_null_match = re.search(r'ALTER\s+COLUMN\s+`?(\w+)`?\s+SET\s+NOT\s+NULL', sql_upper, re.IGNORECASE)
                if set_not_null_match:
                    schema_change.change_type = "SET_NOT_NULL"
                    schema_change.column_name = set_not_null_match.group(1).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect DROP NOT NULL
            if 'DROP' in sql_upper and 'NOT' in sql_upper and 'NULL' in sql_upper and 'ALTER' in sql_upper and 'COLUMN' in sql_upper:
                drop_not_null_match = re.search(r'ALTER\s+COLUMN\s+`?(\w+)`?\s+DROP\s+NOT\s+NULL', sql_upper, re.IGNORECASE)
                if drop_not_null_match:
                    schema_change.change_type = "DROP_NOT_NULL"
                    schema_change.column_name = drop_not_null_match.group(1).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect ADD CONSTRAINT
            if 'ADD' in sql_upper and 'CONSTRAINT' in sql_upper:
                add_constraint_match = re.search(r'ADD\s+CONSTRAINT\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if add_constraint_match:
                    schema_change.change_type = "ADD_CONSTRAINT"
                    constraint_name = add_constraint_match.group(1).upper()
                    schema_change.column_name = constraint_name  # Reuse column_name field
                    # Try to detect constraint type
                    if 'PRIMARY KEY' in sql_upper:
                        schema_change.new_value = "PRIMARY_KEY"
                    elif 'FOREIGN KEY' in sql_upper:
                        schema_change.new_value = "FOREIGN_KEY"
                    elif 'UNIQUE' in sql_upper:
                        schema_change.new_value = "UNIQUE"
                    elif 'CHECK' in sql_upper:
                        schema_change.new_value = "CHECK"
                    else:
                        schema_change.new_value = "CONSTRAINT"
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect DROP CONSTRAINT
            if 'DROP' in sql_upper and 'CONSTRAINT' in sql_upper:
                drop_constraint_match = re.search(r'DROP\s+CONSTRAINT\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if drop_constraint_match:
                    schema_change.change_type = "DROP_CONSTRAINT"
                    constraint_name = drop_constraint_match.group(1).upper()
                    schema_change.column_name = constraint_name  # Reuse column_name field
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect RENAME TABLE
            if 'RENAME' in sql_upper and 'TO' in sql_upper and 'COLUMN' not in sql_upper:
                rename_table_match = re.search(r'RENAME\s+TO\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if rename_table_match:
                    schema_change.change_type = "RENAME_TABLE"
                    schema_change.old_value = schema_change.table_name
                    schema_change.new_value = rename_table_match.group(1).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect ADD INDEX (CREATE INDEX)
            if 'CREATE' in sql_upper and 'INDEX' in sql_upper:
                create_index_match = re.search(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s+ON\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                if create_index_match:
                    schema_change.change_type = "ADD_INDEX"
                    index_name = create_index_match.group(1).upper()
                    table_name_from_index = create_index_match.group(2).upper()
                    schema_change.table_name = table_name_from_index
                    schema_change.column_name = index_name  # Reuse column_name field
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Try to detect DROP INDEX
            if 'DROP' in sql_upper and 'INDEX' in sql_upper:
                drop_index_match = re.search(r'DROP\s+INDEX\s+(?:IF\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?', sql_upper, re.IGNORECASE)
                if drop_index_match:
                    schema_change.change_type = "DROP_INDEX"
                    index_name = (drop_index_match.group(2) or drop_index_match.group(1)).upper()
                    schema_change.column_name = index_name  # Reuse column_name field
                    # Try to get table name from ON clause if present
                    if 'ON' in sql_upper:
                        on_match = re.search(r'ON\s+`?(\w+)`?', sql_upper, re.IGNORECASE)
                        if on_match:
                            schema_change.table_name = on_match.group(1).upper()
                    print(f"   ✅ Enhanced: Detected {schema_change.change_type} via regex")
                    return schema_change
            
            # Method 2: Query PostgreSQL system catalogs to detect what changed
            # IMPORTANT: Only use this for ADD operations. For DROP, we can't detect from current state.
            # Check if SQL suggests ADD operation (no DROP keyword found)
            if 'DROP' not in sql_upper:
                print(f"   🔍 Querying PostgreSQL system catalogs to detect change...")
                try:
                    db_name = os.getenv("POSTGRES_DB", database_name)
                    db_host = os.getenv("POSTGRES_HOST", "host.docker.internal")
                    db_port = os.getenv("POSTGRES_PORT", "5432")
                    db_user = os.getenv("POSTGRES_USER", "postgres")
                    db_password = os.getenv("POSTGRES_PASSWORD", "sabari")
                    
                    conn = psycopg2.connect(
                        host=db_host,
                        port=db_port,
                        database=db_name,
                        user=db_user,
                        password=db_password,
                        connect_timeout=5
                    )
                    
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        table_name = schema_change.table_name.lower()
                        
                        # Get all columns for this table, ordered by creation time (attnum)
                        # New columns typically have higher attnum values
                        cursor.execute("""
                            SELECT 
                                a.attname AS column_name,
                                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                                a.attnum,
                                a.atthasdef,
                                pg_get_expr(adbin, adrelid) AS default_value
                            FROM pg_attribute a
                            LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
                            JOIN pg_class c ON a.attrelid = c.oid
                            JOIN pg_namespace n ON c.relnamespace = n.oid
                            WHERE n.nspname = 'public'
                            AND c.relname = %s
                            AND a.attnum > 0
                            AND NOT a.attisdropped
                            ORDER BY a.attnum DESC
                            LIMIT 5
                        """, (table_name,))
                        
                        recent_columns = cursor.fetchall()
                        
                        if recent_columns:
                            # The most recently added column (highest attnum) is likely what changed
                            # Only use this heuristic for ADD operations (when DROP is not in SQL)
                            newest_col = recent_columns[0]
                            col_name = newest_col['column_name']
                            col_type = newest_col['data_type']
                            has_default = newest_col['atthasdef']
                            default_value = newest_col['default_value']
                            
                            # Heuristic: If we can't detect from SQL and no DROP keyword,
                            # assume the newest column was added
                            print(f"   💡 Detected potential new column: {col_name} ({col_type})")
                            schema_change.change_type = "ADD_COLUMN"
                            schema_change.column_name = col_name.upper()
                            schema_change.new_value = col_type
                            if default_value:
                                schema_change.new_value += f" DEFAULT {default_value}"
                            print(f"   ✅ Enhanced: Detected {schema_change.change_type} via system catalog")
                            conn.close()
                            return schema_change
                        
                    conn.close()
                except Exception as db_error:
                    print(f"   ⚠️ Could not query system catalogs: {db_error}")
            else:
                # SQL contains DROP but we couldn't parse the column name
                # This means the SQL is incomplete and we can't detect what was dropped
                print(f"   ⚠️  DROP operation detected but column name not found in incomplete SQL")
                print(f"   💡 Tip: Use direct API call with full SQL for accurate DROP detection")
            
            # If all methods fail, use generic ALTER_TABLE
            print(f"   ⚠️  Could not detect exact change type from SQL, using generic ALTER_TABLE")
            print(f"   💡 Tip: Use direct API call with full SQL for accurate detection")
            
        except Exception as e:
            print(f"   ⚠️ Could not enhance schema change: {e}")
            # Return original schema_change if enhancement fails
        
        return schema_change
    
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
                    # Use pg_get_viewdef function to get view definition
                    cursor.execute("""
                    SELECT DISTINCT
                        v.viewname AS view_name,
                        pg_get_viewdef(c.oid) AS view_definition
                    FROM pg_views v
                    JOIN pg_class c ON c.relname = v.viewname
                    WHERE v.schemaname = 'public'
                    AND pg_get_viewdef(c.oid) LIKE %s
                    """, (f'%{table_name.lower()}%',))
                    
                    for row in cursor.fetchall():
                        relationships["reverse"].append({
                            "type": "VIEW",
                            "source_table": row["view_name"].upper(),  # View name
                            "target_table": table_name.upper(),  # Table the view depends on
                            "description": "View depends on this table",
                            "view_definition": row["view_definition"][:200] if row["view_definition"] else ""  # Truncated for display
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
    
    async def _analyze_mongodb_schema_change(
        self,
        operation_statement: str,
        database_name: str,
        change_id: str,
        repository: str,
        analysis_id: str,
        github_repo_url: str = None,
        github_branch: str = "main"
    ) -> Dict:
        """Analyze MongoDB schema change (similar to PostgreSQL but for MongoDB)"""
        start_time = datetime.now()
        
        try:
            # Step 1: Parse MongoDB schema change
            print("Step 1/6: Parsing MongoDB schema change...")
            mongo_change = self.mongodb_analyzer.parse_schema_change(operation_statement)
            
            if not mongo_change:
                # Try to extract collection name
                import re
                coll_match = re.search(r'\b(\w+)\b', operation_statement)
                if coll_match:
                    collection_name = coll_match.group(1)
                    mongo_change = MongoSchemaChange(
                        change_type="MODIFY_COLLECTION",
                        collection_name=collection_name.upper(),
                        operation_statement=operation_statement
                    )
                    print(f"   ⚠️  Could not fully parse MongoDB operation, using generic MODIFY_COLLECTION")
                else:
                    raise ValueError(f"Could not parse MongoDB schema change: {operation_statement[:100]}")
            
            print(f"   ✅ Change Type: {mongo_change.change_type}")
            print(f"   ✅ Collection: {mongo_change.collection_name}")
            if mongo_change.index_name:
                print(f"   ✅ Index: {mongo_change.index_name}")
            if mongo_change.field_name:
                print(f"   ✅ Field: {mongo_change.field_name}")
            
            # Step 2: Find code files that use this collection
            print("Step 2/6: Finding code dependencies...")
            # Get GitHub repo URL from parameter, environment, or repository parameter
            # Priority: github_repo_url parameter > GITHUB_REPO_URL_MONGODB env > repository parameter
            final_github_repo_url = github_repo_url or os.getenv("GITHUB_REPO_URL_MONGODB") or repository
            final_github_branch = github_branch or os.getenv("GITHUB_BRANCH", "main")
            
            code_dependencies, repo_path = await self._find_code_dependencies(
                mongo_change.collection_name,  # Use collection name as table name for code search
                mongo_change.field_name,
                database_type="mongodb",  # Only look for MongoDB patterns, exclude SQL files
                github_repo_url=final_github_repo_url if final_github_repo_url and ("github.com" in final_github_repo_url or "/" in final_github_repo_url) else None,
                github_branch=final_github_branch
            )
            print(f"   ✅ Found {len(code_dependencies)} code files using this collection")
            
            # Step 3: Get MongoDB relationships
            print("Step 3/6: Analyzing MongoDB relationships...")
            db_relationships = await self._get_mongodb_relationships(
                mongo_change.collection_name,
                database_name
            )
            print(f"   ✅ Found {len(db_relationships.get('forward', []))} forward relationships")
            print(f"   ✅ Found {len(db_relationships.get('reverse', []))} reverse relationships")
            
            # Step 4: Store in Neo4j
            print("Step 4/6: Storing in dependency graph...")
            await self._store_mongodb_schema_in_neo4j(
                mongo_change,
                database_name,
                code_dependencies,
                db_relationships
            )
            print(f"   ✅ Schema stored in Neo4j")
            
            # Step 5: AI Analysis
            print("Step 5/6: Running AI analysis...")
            try:
                # Convert MongoDB change to schema change format for AI analyzer
                schema_change_like = SchemaChange(
                    change_type=mongo_change.change_type,
                    table_name=mongo_change.collection_name,
                    column_name=mongo_change.field_name or mongo_change.index_name,
                    old_value=mongo_change.old_value,
                    new_value=mongo_change.new_value,
                    sql_statement=mongo_change.operation_statement
                )
                
                ai_insights = await self.ai_analyzer.analyze_schema_impact(
                    schema_change_like,
                    code_dependencies,
                    db_relationships,
                    repository_path=repo_path
                )
            except Exception as ai_error:
                print(f"⚠️ AI analysis failed (non-blocking): {ai_error}")
                ai_insights = self._fallback_schema_analysis()
            
            # Step 6: Risk Scoring
            print("Step 6/6: Calculating risk score...")
            schema_change_like = SchemaChange(
                change_type=mongo_change.change_type,
                table_name=mongo_change.collection_name,
                column_name=mongo_change.field_name or mongo_change.index_name,
                old_value=mongo_change.old_value,
                new_value=mongo_change.new_value,
                sql_statement=mongo_change.operation_statement
            )
            risk_score = self.risk_scorer.calculate_schema_risk(
                schema_change_like,
                code_dependencies,
                db_relationships,
                ai_insights
            )
            
            # Compile results
            result = self._compile_results(
                analysis_id,
                schema_change_like,
                database_name,
                code_dependencies,
                db_relationships,
                ai_insights,
                risk_score,
                start_time,
                repository,
                operation_statement,
                database_type="mongodb"
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ MongoDB Schema Analysis Complete in {duration:.1f}s")
            print(f"   Risk Score: {risk_score['score']}/10 - {risk_score['level']}")
            print(f"   Affected Code Files: {len(code_dependencies)}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ MongoDB schema analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _get_mongodb_relationships(
        self,
        collection_name: str,
        database_name: str
    ) -> Dict:
        """Get MongoDB collection relationships"""
        relationships = {"forward": [], "reverse": []}
        
        if not PYMONGO_AVAILABLE:
            print(f"   ⚠️ pymongo not available, using fallback")
            return relationships
        
        try:
            # Get MongoDB connection details
            # For Docker: use host.docker.internal to reach host MongoDB
            # For local: use localhost
            default_uri = "mongodb://host.docker.internal:27017/" if os.path.exists("/.dockerenv") else "mongodb://localhost:27017/"
            mongo_uri = os.getenv("MONGO_URI", default_uri)
            # Extract DB name from database_name (might be "mongodb_banking_db")
            db_name = database_name.replace("mongodb_", "") if database_name.startswith("mongodb_") else database_name
            
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            db = client[db_name]
            collection = db[collection_name]
            
            print(f"   🔌 Connecting to MongoDB: {mongo_uri}/{db_name}")
            
            # Get sample document to infer relationships
            sample_doc = collection.find_one()
            if sample_doc:
                # Look for reference fields (e.g., customer_id, account_id)
                for key, value in sample_doc.items():
                    if key.endswith("_id") and key != "_id":
                        referenced_collection = key.replace("_id", "").replace("Id", "")
                        relationships["forward"].append({
                            "type": "REFERENCE",
                            "target_table": referenced_collection.upper(),
                            "target_collection": referenced_collection,
                            "field": key
                        })
            
            # Find collections that might reference this one
            all_collections = db.list_collection_names()
            for other_coll_name in all_collections:
                if other_coll_name.lower() == collection_name.lower():
                    continue
                
                other_coll = db[other_coll_name]
                sample_other = other_coll.find_one()
                if sample_other:
                    # Check if this collection is referenced
                    ref_field = f"{collection_name.lower().rstrip('s')}_id"
                    if ref_field in sample_other:
                        relationships["reverse"].append({
                            "type": "REFERENCED_BY",
                            "source_table": other_coll_name.upper(),
                            "source_collection": other_coll_name,
                            "field": ref_field
                        })
            
            client.close()
            print(f"   ✅ Found {len(relationships['forward'])} forward relationships from MongoDB")
            print(f"   ✅ Found {len(relationships['reverse'])} reverse relationships from MongoDB")
            
        except Exception as e:
            print(f"   ⚠️ Could not query MongoDB for relationships: {e}")
        
        return relationships
    
    async def _store_mongodb_schema_in_neo4j(
        self,
        mongo_change: MongoSchemaChange,
        database_name: str,
        code_dependencies: List[Dict],
        db_relationships: Dict
    ):
        """Store MongoDB schema change in Neo4j"""
        try:
            # Create database node
            await neo4j_client.create_database_node(
                name=database_name,
                properties={"type": "mongodb"}
            )
            
            # Create collection node (using correct parameter names)
            await neo4j_client.create_table_node(
                name=mongo_change.collection_name,
                database=database_name,
                properties={"type": "collection", "change_type": mongo_change.change_type}
            )
            
            # Create relationships to code files (using USES_COLLECTION)
            for dep in code_dependencies:
                file_name = dep["file_path"].split("/")[-1]
                
                # Create module node for code file
                await neo4j_client.create_module_node(
                    name=file_name,
                    properties={"path": dep["file_path"]}
                )
                
                # Create relationship: Code file USES Collection (MongoDB-specific)
                await neo4j_client.create_collection_usage(
                    source_file=file_name,
                    target_collection=mongo_change.collection_name,
                    database=database_name,
                    usage_count=dep["usage_count"],
                    field_name=mongo_change.field_name or ""
                )
            
            # Create database relationships (using create_table_relationship)
            # First, ensure all related collections exist as nodes in Neo4j
            for rel in db_relationships.get("forward", []):
                target = rel.get("target_table") or rel.get("target_collection", "")
                if target:
                    # Create node for target collection if it doesn't exist
                    await neo4j_client.create_table_node(
                        name=target,
                        database=database_name,
                        properties={"type": "collection"}
                    )
                    await neo4j_client.create_table_relationship(
                        source_table=mongo_change.collection_name,
                        target_table=target,
                        database=database_name,
                        relationship_type=rel.get("type", "REFERENCE"),
                        properties={"field": rel.get("field", "")}
                    )
            
            for rel in db_relationships.get("reverse", []):
                source = rel.get("source_table") or rel.get("source_collection", "")
                if source:
                    # Create node for source collection if it doesn't exist (e.g., BALANCE_HISTORY)
                    await neo4j_client.create_table_node(
                        name=source,
                        database=database_name,
                        properties={"type": "collection"}
                    )
                    await neo4j_client.create_table_relationship(
                        source_table=source,
                        target_table=mongo_change.collection_name,
                        database=database_name,
                        relationship_type=rel.get("type", "REFERENCED_BY"),
                        properties={"field": rel.get("field", "")}
                    )
            
            print("   ✅ Schema stored in Neo4j")
        
        except Exception as e:
            print(f"   ⚠️ Could not store MongoDB schema in Neo4j: {e}")
            import traceback
            traceback.print_exc()
    
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
        sql_statement: str,
        database_type: str = "postgresql"
    ) -> Dict:
        """Compile all results into final format"""
        
        affected_files = [dep["file_path"] for dep in code_dependencies]
        affected_tables = []
        
        # Add related tables/collections from relationships
        for rel in db_relationships.get("forward", []):
            if rel.get("target_table") or rel.get("target_collection"):
                affected_tables.append(rel.get("target_table") or rel.get("target_collection"))
        
        for rel in db_relationships.get("reverse", []):
            if rel.get("source_table") or rel.get("source_collection"):
                affected_tables.append(rel.get("source_table") or rel.get("source_collection"))
        
        return {
            "id": analysis_id,
            "type": "schema_change",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "database": database_name,
            "database_type": database_type,  # Add database type to results
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

