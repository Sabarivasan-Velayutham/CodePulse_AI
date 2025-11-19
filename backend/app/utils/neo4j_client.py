from neo4j import AsyncGraphDatabase
import os
from typing import Optional, Dict, List

class Neo4jClient:
    """Neo4j database client"""
    
    def __init__(self):
        self.driver: Optional[AsyncGraphDatabase] = None
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "codeflow123")
    
    async def connect(self):
        """Initialize Neo4j connection"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Test connection
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            print("✅ Connected to Neo4j")
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            print("👋 Neo4j connection closed")
    
    async def create_module_node(self, name: str, properties: dict):
        """Create a module node"""
        async with self.driver.session() as session:
            query = """
            MERGE (m:Module {name: $name})
            SET m += $properties
            RETURN m
            """
            result = await session.run(query, name=name, properties=properties)
            return await result.single()
    
    async def create_dependency(self, source: str, target: str, rel_type: str, line_number: str = "0", code_reference: str = ""):
        """Create dependency relationship with line number and code reference"""
        async with self.driver.session() as session:
            query = f"""
            MATCH (source:Module {{name: $source}})
            MATCH (target:Module {{name: $target}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.line_number = $line_number,
                r.code_reference = $code_reference,
                r.last_updated = datetime()
            RETURN r
            """
            result = await session.run(
                query,
                source=source,
                target=target,
                line_number=str(line_number),
                code_reference=str(code_reference) if code_reference else ""
            )
            return await result.single()
    
    async def get_dependencies(self, module_name: str, max_depth: int = 3):
        """Get all dependencies for a module (forward and reverse)"""
        if not self.driver:
            raise Exception("Neo4j driver not connected")
            
        async with self.driver.session() as session:
            # Check if module exists
            check_query = "MATCH (m:Module {name: $module_name}) RETURN m"
            check_result = await session.run(check_query, module_name=module_name)
            if not await check_result.single():
                print(f"⚠️ Module {module_name} not found in Neo4j")
                return []
            
            # Get forward dependencies (this module depends on others)
            # Use a simpler query that works with any relationship type
            forward_query = f"""
            MATCH path = (start:Module {{name: $module_name}})-[*1..{max_depth}]->(end:Module)
            WHERE start <> end
            WITH path, end, relationships(path) as rels
            RETURN 
                end.name as module,
                length(path) as distance,
                [rel in rels | type(rel)] as relationship_types,
                [rel in rels | rel.line_number] as line_numbers,
                [rel in rels | rel.code_reference] as code_references
            ORDER BY distance
            LIMIT 100
            """
            
            # Get reverse dependencies (others depend on this module)
            reverse_query = f"""
            MATCH path = (start:Module)-[*1..{max_depth}]->(end:Module {{name: $module_name}})
            WHERE start <> end
            WITH path, start, relationships(path) as rels
            RETURN 
                start.name as module,
                length(path) as distance,
                [rel in rels | type(rel)] as relationship_types,
                [rel in rels | rel.line_number] as line_numbers,
                [rel in rels | rel.code_reference] as code_references
            ORDER BY distance
            LIMIT 100
            """
            
            dependencies = []
            
            try:
                # Forward dependencies
                result = await session.run(forward_query, module_name=module_name)
                async for record in result:
                    try:
                        line_nums = record.get("line_numbers", [])
                        code_refs = record.get("code_references", [])
                        # Parse line numbers (can be strings like "7,73,118" or arrays)
                        line_numbers = []
                        if line_nums:
                            for ln in line_nums:
                                if ln is None:
                                    continue
                                if isinstance(ln, str):
                                    # Parse comma-separated string
                                    line_numbers.extend([int(x.strip()) for x in ln.split(',') if x.strip().isdigit()])
                                elif isinstance(ln, int):
                                    line_numbers.append(ln)
                        
                        # Parse code references (can be strings with " | " separator or arrays)
                        code_references = []
                        if code_refs:
                            for cr in code_refs:
                                if cr is None or not cr:
                                    continue
                                if isinstance(cr, str):
                                    # Split by " | " separator
                                    code_references.extend([ref.strip() for ref in cr.split(' | ') if ref.strip()])
                                else:
                                    code_references.append(str(cr))
                        
                        dependencies.append({
                            "module": record["module"],
                            "distance": record["distance"],
                            "relationships": record.get("relationship_types", []),
                            "line_numbers": line_numbers,
                            "code_references": code_references,
                            "direction": "forward"
                        })
                    except Exception as e:
                        print(f"⚠️ Error processing forward dependency record: {e}")
                        continue
                
                # Reverse dependencies
                result = await session.run(reverse_query, module_name=module_name)
                async for record in result:
                    try:
                        line_nums = record.get("line_numbers", [])
                        code_refs = record.get("code_references", [])
                        # Parse line numbers (can be strings like "7,73,118" or arrays)
                        line_numbers = []
                        if line_nums:
                            for ln in line_nums:
                                if ln is None:
                                    continue
                                if isinstance(ln, str):
                                    # Parse comma-separated string
                                    line_numbers.extend([int(x.strip()) for x in ln.split(',') if x.strip().isdigit()])
                                elif isinstance(ln, int):
                                    line_numbers.append(ln)
                        
                        # Parse code references (can be strings with " | " separator or arrays)
                        code_references = []
                        if code_refs:
                            for cr in code_refs:
                                if cr is None or not cr:
                                    continue
                                if isinstance(cr, str):
                                    # Split by " | " separator
                                    code_references.extend([ref.strip() for ref in cr.split(' | ') if ref.strip()])
                                else:
                                    code_references.append(str(cr))
                        
                        dependencies.append({
                            "module": record["module"],
                            "distance": record["distance"],
                            "relationships": record.get("relationship_types", []),
                            "line_numbers": line_numbers,
                            "code_references": code_references,
                            "direction": "reverse"
                        })
                    except Exception as e:
                        print(f"⚠️ Error processing reverse dependency record: {e}")
                        continue
            except Exception as e:
                print(f"❌ Neo4j query error: {e}")
                raise
            
            return dependencies
    
    async def create_database_node(self, name: str, properties: dict = None):
        """Create a database node"""
        async with self.driver.session() as session:
            query = """
            MERGE (d:Database {name: $name})
            SET d += $properties
            RETURN d
            """
            result = await session.run(
                query,
                name=name,
                properties=properties or {}
            )
            return await result.single()
    
    async def create_table_node(self, name: str, database: str, properties: dict = None):
        """Create a table node and link to database"""
        async with self.driver.session() as session:
            query = """
            MATCH (db:Database {name: $database})
            MERGE (t:Table {name: $name, database: $database})
            SET t += $properties
            MERGE (t)-[:BELONGS_TO]->(db)
            RETURN t
            """
            result = await session.run(
                query,
                name=name,
                database=database,
                properties=properties or {}
            )
            return await result.single()
    
    async def create_table_usage(self, source_file: str, target_table: str, database: str, usage_count: int = 1, column_name: str = ""):
        """Create relationship: Code file USES Table"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Module {name: $source_file})
            MATCH (t:Table {name: $target_table, database: $database})
            MERGE (m)-[r:USES_TABLE]->(t)
            SET r.usage_count = $usage_count,
                r.column_name = $column_name,
                r.last_updated = datetime()
            RETURN r
            """
            result = await session.run(
                query,
                source_file=source_file,
                target_table=target_table,
                database=database,
                usage_count=usage_count,
                column_name=column_name
            )
            return await result.single()
    
    async def create_collection_usage(self, source_file: str, target_collection: str, database: str, usage_count: int = 1, field_name: str = ""):
        """Create relationship: Code file USES Collection (MongoDB)"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Module {name: $source_file})
            MATCH (t:Table {name: $target_collection, database: $database})
            MERGE (m)-[r:USES_COLLECTION]->(t)
            SET r.usage_count = $usage_count,
                r.field_name = $field_name,
                r.last_updated = datetime()
            RETURN r
            """
            result = await session.run(
                query,
                source_file=source_file,
                target_collection=target_collection,
                database=database,
                usage_count=usage_count,
                field_name=field_name
            )
            return await result.single()
    
    async def create_table_relationship(self, source_table: str, target_table: str, database: str, relationship_type: str, properties: dict = None):
        """Create relationship between tables (foreign key, etc.)"""
        async with self.driver.session() as session:
            query = f"""
            MATCH (s:Table {{name: $source_table, database: $database}})
            MATCH (t:Table {{name: $target_table, database: $database}})
            MERGE (s)-[r:{relationship_type}]->(t)
            SET r += $properties,
                r.last_updated = datetime()
            RETURN r
            """
            result = await session.run(
                query,
                source_table=source_table,
                target_table=target_table,
                database=database,
                properties=properties or {}
            )
            return await result.single()
    
    async def get_table_relationships(self, table_name: str, database_name: str) -> Dict:
        """Get all relationships for a table"""
        if not self.driver:
            return {"forward": [], "reverse": []}
        
        async with self.driver.session() as session:
            # Forward: tables this table references
            forward_query = """
            MATCH (t:Table {name: $table_name, database: $database_name})-[r]->(target:Table {database: $database_name})
            RETURN 
                type(r) as relationship_type,
                target.name as target_table,
                properties(r) as properties
            """
            
            # Reverse: tables that reference this table
            reverse_query = """
            MATCH (source:Table {database: $database_name})-[r]->(t:Table {name: $table_name, database: $database_name})
            RETURN 
                type(r) as relationship_type,
                source.name as source_table,
                properties(r) as properties
            """
            
            forward = []
            reverse = []
            
            try:
                result = await session.run(forward_query, table_name=table_name, database_name=database_name)
                async for record in result:
                    forward.append({
                        "type": record.get("relationship_type", "RELATES_TO"),
                        "target_table": record.get("target_table"),
                        **record.get("properties", {})
                    })
                
                result = await session.run(reverse_query, table_name=table_name, database_name=database_name)
                async for record in result:
                    reverse.append({
                        "type": record.get("relationship_type", "RELATES_TO"),
                        "source_table": record.get("source_table"),
                        **record.get("properties", {})
                    })
            except Exception as e:
                print(f"⚠️ Error getting table relationships: {e}")
            
            return {"forward": forward, "reverse": reverse}
    
    async def get_table_code_dependencies(self, table_name: str, database_name: str) -> List[Dict]:
        """Get all code files that use a table or collection"""
        if not self.driver:
            return []
        
        async with self.driver.session() as session:
            # Query for both USES_TABLE (PostgreSQL) and USES_COLLECTION (MongoDB)
            query = """
            MATCH (m:Module)-[r]->(t:Table {name: $table_name, database: $database_name})
            WHERE type(r) IN ['USES_TABLE', 'USES_COLLECTION']
            RETURN 
                m.name as file_name,
                m.path as file_path,
                r.usage_count as usage_count,
                COALESCE(r.column_name, r.field_name, '') as column_name,
                type(r) as relationship_type
            """
            
            dependencies = []
            try:
                result = await session.run(query, table_name=table_name, database_name=database_name)
                async for record in result:
                    dependencies.append({
                        "file_name": record.get("file_name"),
                        "file_path": record.get("file_path", ""),
                        "usage_count": record.get("usage_count", 1),
                        "column_name": record.get("column_name", ""),
                        "relationship_type": record.get("relationship_type", "USES_TABLE")
                    })
            except Exception as e:
                print(f"⚠️ Error getting table code dependencies: {e}")
            
            return dependencies

# Global instance
neo4j_client = Neo4jClient()