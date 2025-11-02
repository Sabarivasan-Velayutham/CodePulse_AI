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
    
    async def create_dependency(self, source: str, target: str, rel_type: str):
        """Create dependency relationship"""
        async with self.driver.session() as session:
            query = f"""
            MATCH (source:Module {{name: $source}})
            MATCH (target:Module {{name: $target}})
            MERGE (source)-[r:{rel_type}]->(target)
            RETURN r
            """
            result = await session.run(
                query,
                source=source,
                target=target
            )
            return await result.single()
    
    async def get_dependencies(self, module_name: str, max_depth: int = 3):
        """Get all dependencies for a module"""
        async with self.driver.session() as session:
            query = """
            MATCH path = (start:Module {name: $module_name})-[*1..%d]->(end:Module)
            RETURN 
                end.name as module,
                length(path) as distance,
                [r in relationships(path) | type(r)] as relationship_types
            ORDER BY distance
            """ % max_depth
            
            result = await session.run(query, module_name=module_name)
            dependencies = []
            async for record in result:
                dependencies.append({
                    "module": record["module"],
                    "distance": record["distance"],
                    "relationships": record["relationship_types"]
                })
            return dependencies

# Global instance
neo4j_client = Neo4jClient()