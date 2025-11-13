"""
Main orchestration engine - ties everything together
"""

import asyncio
from typing import Dict
from datetime import datetime
import uuid

from app.services.depends_wrapper import DependsAnalyzer
from app.services.sql_extractor import SQLExtractor
from app.engine.ai_analyzer import AIAnalyzer
from app.engine.risk_scorer import RiskScorer
from app.utils.neo4j_client import neo4j_client

class AnalysisOrchestrator:
    def __init__(self):
        self.depends = DependsAnalyzer()
        self.sql_extractor = SQLExtractor()
        self.ai_analyzer = AIAnalyzer()
        self.risk_scorer = RiskScorer()
    
    async def analyze_change(
        self,
        file_path: str,
        code_diff: str,
        commit_sha: str,
        repository: str,
        commit_message: str = ""
    ) -> Dict:
        """
        Main orchestration method
        Coordinates all analysis steps
        
        Args:
            file_path: Path to changed file
            code_diff: Git diff
            commit_sha: Commit SHA
            repository: Repository name
        
        Returns:
            Complete analysis result
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🚀 Starting Analysis: {analysis_id}")
        print(f"   File: {file_path}")
        print(f"   Commit: {commit_sha[:8]}")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Dependency Analysis (using DEPENDS)
            print("Step 1/6: Analyzing code dependencies...")
            dependencies = await self._analyze_dependencies(file_path)
            
            # Step 1.5: Database Dependency Analysis (NEW)
            print("Step 2/6: Analyzing database dependencies...")
            database_dependencies = await self._analyze_database_dependencies(file_path)
            
            # Step 2: Store in Neo4j
            print("Step 3/6: Storing dependency graph...")
            await self._store_in_neo4j(file_path, dependencies, database_dependencies)
            
            # Step 3: AI Analysis (non-blocking - continue even if it fails)
            print("Step 4/6: Running AI analysis...")
            try:
                ai_insights = await self.ai_analyzer.analyze_impact(
                    file_path, code_diff, dependencies, database_dependencies
                )
            except Exception as ai_error:
                print(f"⚠️ AI analysis failed (non-blocking): {ai_error}")
                ai_insights = self.ai_analyzer._fallback_analysis()
            
            # Step 4: Risk Scoring
            print("Step 5/6: Calculating risk score...")
            risk_score = self.risk_scorer.calculate_risk(
                file_path, dependencies, ai_insights, database_dependencies
            )
            
            # Step 5: Compile Results
            print("Step 6/6: Compiling results...")
            result = self._compile_results(
                analysis_id,
                file_path,
                commit_sha,
                repository,
                dependencies,
                database_dependencies,
                ai_insights,
                risk_score,
                start_time,
                commit_message
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ Analysis Complete in {duration:.1f}s")
            print(f"   Risk Score: {risk_score['score']}/10 - {risk_score['level']}")
            print(f"   Code Dependencies: {len(dependencies.get('direct_dependencies', []))} direct")
            print(f"   Database Dependencies: {len(database_dependencies.get('tables', []))} tables")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Analysis failed: {str(e)}")
            raise
    
    async def _analyze_dependencies(self, file_path: str) -> Dict:
        """Run DEPENDS analysis"""
        # Get directory containing the file
        import os
        directory = os.path.dirname(file_path)
        if not directory:
            directory = "sample-repo/banking-app/src"  # Default for demo
        
        # Run in thread pool (DEPENDS is blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.depends.analyze_single_file,
            file_path
        )
        
        return result
    
    async def _analyze_database_dependencies(self, file_path: str) -> Dict:
        """
        Analyze database table/column usage in the changed file
        
        Returns:
            Dictionary with tables and their usage details
        """
        import os
        
        # File path might already include "sample-repo" or might not
        # Handle both cases - normalize the path
        normalized_path = file_path
        
        # Remove leading "sample-repo/" if present to avoid duplication
        if normalized_path.startswith("sample-repo/"):
            normalized_path = normalized_path[len("sample-repo/"):]
        elif normalized_path.startswith("/sample-repo/"):
            normalized_path = normalized_path[len("/sample-repo/"):]
        
        # Try multiple possible paths (Docker vs local)
        possible_paths = [
            os.path.join("/sample-repo", normalized_path),  # Docker mount path (preferred)
            normalized_path,  # As-is (if already absolute)
            os.path.join("sample-repo", normalized_path),  # Relative path
            os.path.join("/app", "sample-repo", normalized_path),  # Alternative Docker path
            os.path.join(os.getcwd(), "sample-repo", normalized_path),  # Local development
            file_path,  # Original path (fallback)
        ]
        
        full_path = None
        for path in possible_paths:
            if os.path.exists(path):
                full_path = path
                break
        
        if not full_path:
            print(f"   ⚠️ File not found: {file_path} (tried: {possible_paths[:3]})")
            return {"tables": [], "total_usages": 0}
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract table usage
            table_usage = self.sql_extractor.extract_table_usage(file_path, content)
            
            # Convert to list format
            tables = []
            total_usages = 0
            for table_name, usages in table_usage.items():
                tables.append({
                    "table_name": table_name,
                    "usages": usages,
                    "usage_count": len(usages),
                    "columns": list(set(
                        col for usage in usages 
                        for col in usage.get('columns', [])
                    ))
                })
                total_usages += len(usages)
            
            print(f"   ✅ Found {len(tables)} database tables used in this file")
            
            return {
                "tables": tables,
                "total_usages": total_usages
            }
            
        except Exception as e:
            print(f"   ⚠️ Error analyzing database dependencies: {e}")
            return {"tables": [], "total_usages": 0}
    
    async def _store_in_neo4j(self, file_path: str, dependencies: Dict, database_dependencies: Dict = None):
        """Store dependency graph in Neo4j (forward and reverse)"""
        try:
            # Create or update module node
            file_name = file_path.split("/")[-1]
            
            await neo4j_client.create_module_node(
                name=file_name,
                properties={
                    "path": file_path,
                    "last_analyzed": datetime.now().isoformat(),
                    "dependency_count": len(dependencies.get("direct_dependencies", []))
                }
            )
            
            # Store forward dependencies (this file depends on others)
            # Direct dependencies
            for dep in dependencies.get("direct_dependencies", []):
                target_name = dep.get("target", "Unknown")
                await neo4j_client.create_module_node(
                    name=target_name,
                    properties={"path": f"unknown/{target_name}"}
                )
                line_nums = dep.get("line_numbers", [])
                code_refs = dep.get("code_references", [])
                line_num_str = ",".join(map(str, line_nums)) if line_nums else str(dep.get("line", 0))
                code_ref_str = " | ".join(code_refs[:3]) if code_refs else dep.get("code_reference", "")
                
                await neo4j_client.create_dependency(
                    source=file_name,
                    target=target_name,
                    rel_type=dep.get("type", "DEPENDS_ON"),
                    line_number=line_num_str,
                    code_reference=code_ref_str
                )
            
            # Indirect dependencies
            for dep in dependencies.get("indirect_dependencies", []):
                target_name = dep.get("target", "Unknown")
                await neo4j_client.create_module_node(
                    name=target_name,
                    properties={"path": f"unknown/{target_name}"}
                )
                line_nums = dep.get("line_numbers", [])
                code_refs = dep.get("code_references", [])
                line_num_str = ",".join(map(str, line_nums)) if line_nums else str(dep.get("line", 0))
                code_ref_str = " | ".join(code_refs[:3]) if code_refs else dep.get("code_reference", "")
                
                await neo4j_client.create_dependency(
                    source=file_name,
                    target=target_name,
                    rel_type=dep.get("type", "DEPENDS_ON"),
                    line_number=line_num_str,
                    code_reference=code_ref_str
                )
            
            # Store reverse dependencies (others depend on this file)
            # Direct reverse dependencies
            for dep in dependencies.get("reverse_direct_dependencies", []):
                source_name = dep.get("source", "Unknown")
                await neo4j_client.create_module_node(
                    name=source_name,
                    properties={"path": f"unknown/{source_name}"}
                )
                line_nums = dep.get("line_numbers", [])
                code_refs = dep.get("code_references", [])
                line_num_str = ",".join(map(str, line_nums)) if line_nums else str(dep.get("line", 0))
                code_ref_str = " | ".join(code_refs[:3]) if code_refs else dep.get("code_reference", "")
                
                await neo4j_client.create_dependency(
                    source=source_name,
                    target=file_name,
                    rel_type=dep.get("type", "DEPENDS_ON"),
                    line_number=line_num_str,
                    code_reference=code_ref_str
                )
            
            # Indirect reverse dependencies
            for dep in dependencies.get("reverse_indirect_dependencies", []):
                source_name = dep.get("source", "Unknown")
                await neo4j_client.create_module_node(
                    name=source_name,
                    properties={"path": f"unknown/{source_name}"}
                )
                line_nums = dep.get("line_numbers", [])
                code_refs = dep.get("code_references", [])
                line_num_str = ",".join(map(str, line_nums)) if line_nums else str(dep.get("line", 0))
                code_ref_str = " | ".join(code_refs[:3]) if code_refs else dep.get("code_reference", "")
                
                await neo4j_client.create_dependency(
                    source=source_name,
                    target=file_name,
                    rel_type=dep.get("type", "DEPENDS_ON"),
                    line_number=line_num_str,
                    code_reference=code_ref_str
                )
            
            # Store database dependencies (code file USES database tables)
            if database_dependencies:
                for table_info in database_dependencies.get("tables", []):
                    table_name = table_info["table_name"]
                    usage_count = table_info["usage_count"]
                    
                    # Create table node if it doesn't exist
                    await neo4j_client.create_table_node(
                        name=table_name,
                        database="banking_db",  # Default database name
                        properties={}
                    )
                    
                    # Create USES_TABLE relationship
                    await neo4j_client.create_table_usage(
                        source_file=file_name,
                        target_table=table_name,
                        database="banking_db",
                        usage_count=usage_count,
                        column_name=""  # Could be enhanced to track specific columns
                    )
            
            print("   ✅ Graph updated in Neo4j")
            
        except Exception as e:
            print(f"   ⚠️ Neo4j update failed: {e}")
            # Don't fail entire analysis if Neo4j fails
    
    def _compile_results(
        self,
        analysis_id: str,
        file_path: str,
        commit_sha: str,
        repository: str,
        dependencies: Dict,
        database_dependencies: Dict,
        ai_insights: Dict,
        risk_score: Dict,
        start_time: datetime,
        commit_message: str = ""
    ) -> Dict:
        """Compile all results into final format"""
        
        # Extract affected modules (forward and reverse)
        affected_modules = []
        for dep in dependencies.get("direct_dependencies", []):
            affected_modules.append(dep.get("target"))
        for dep in dependencies.get("reverse_direct_dependencies", []):
            affected_modules.append(dep.get("source"))
        
        # Extract affected database tables
        affected_tables = []
        if database_dependencies:
            for table_info in database_dependencies.get("tables", []):
                affected_tables.append(table_info["table_name"])
        
        result = {
            "id": analysis_id,
            "type": "code_change",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "commit_sha": commit_sha,
            "commit_message": commit_message,
            "repository": repository,
            "file_path": file_path,
            "risk_score": risk_score,
            "dependencies": {
                "direct": dependencies.get("direct_dependencies", []),
                "indirect": dependencies.get("indirect_dependencies", []),
                "reverse_direct": dependencies.get("reverse_direct_dependencies", []),
                "reverse_indirect": dependencies.get("reverse_indirect_dependencies", []),
                "count": {
                    "direct": len(dependencies.get("direct_dependencies", [])),
                    "indirect": len(dependencies.get("indirect_dependencies", [])),
                    "reverse_direct": len(dependencies.get("reverse_direct_dependencies", [])),
                    "reverse_indirect": len(dependencies.get("reverse_indirect_dependencies", [])),
                    "total": (
                        len(dependencies.get("direct_dependencies", [])) +
                        len(dependencies.get("indirect_dependencies", [])) +
                        len(dependencies.get("reverse_direct_dependencies", [])) +
                        len(dependencies.get("reverse_indirect_dependencies", []))
                    )
                }
            },
            "database_dependencies": database_dependencies or {"tables": [], "total_usages": 0},
            "ai_insights": ai_insights,
            "affected_modules": list(set(affected_modules)),  # Unique modules
            "affected_tables": list(set(affected_tables)),  # Unique tables
            "summary": {
                "code_files_affected": len(set(affected_modules)),
                "database_tables_affected": len(set(affected_tables)),
                "total_code_dependencies": (
                    len(dependencies.get("direct_dependencies", [])) +
                    len(dependencies.get("indirect_dependencies", [])) +
                    len(dependencies.get("reverse_direct_dependencies", [])) +
                    len(dependencies.get("reverse_indirect_dependencies", []))
                ),
                "total_database_usages": database_dependencies.get("total_usages", 0) if database_dependencies else 0
            },
            "metadata": {
                "analyzer_version": "1.0.0",
                "analysis_type": "full"
            }
        }
        
        return result