from neo4j import AsyncGraphDatabase
import os
from typing import Optional

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

# Global instance
neo4j_client = Neo4jClient()