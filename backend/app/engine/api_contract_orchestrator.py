"""
API Contract Change Orchestrator
Orchestrates API contract change detection and analysis
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import os

from app.services.api_extractor import APIContractExtractor
from app.services.api_contract_analyzer import APIContractAnalyzer, APIContractChange
from app.engine.ai_analyzer import AIAnalyzer
from app.engine.risk_scorer import RiskScorer
from app.utils.neo4j_client import neo4j_client
from app.utils.github_fetcher import GitHubFetcher
from app.config import get_consumer_repositories


class APIContractOrchestrator:
    """Orchestrates API contract change analysis"""
    
    def __init__(self):
        self.api_extractor = APIContractExtractor()
        self.api_analyzer = APIContractAnalyzer()
        self.ai_analyzer = AIAnalyzer()
        self.risk_scorer = RiskScorer()
        self.github_fetcher = GitHubFetcher()
    
    async def analyze_api_contract_change(
        self,
        file_path: str,
        code_diff: str,
        commit_sha: str,
        repository: str,
        github_repo_url: Optional[str] = None,
        github_branch: str = "main",
        commit_message: str = ""
    ) -> Dict:
        """
        Analyze API contract changes in a code file
        
        Args:
            file_path: Path to changed file
            code_diff: Git diff showing changes
            commit_sha: Commit SHA
            repository: Repository name
            github_repo_url: Optional GitHub repository URL
            github_branch: GitHub branch name
            commit_message: Commit message
        
        Returns:
            Complete analysis result
        """
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🔌 Starting API Contract Analysis: {analysis_id}")
        print(f"   File: {file_path}")
        print(f"   Commit: {commit_sha[:8]}")
        print(f"{'='*60}\n")
        
        try:
            # Step 1: Get repository path
            repo_path = await self._get_repository_path(repository, github_repo_url, github_branch)
            
            # Step 2: Extract API contracts from current version
            print("Step 1/7: Extracting API contracts from current code...")
            after_contracts = await self._extract_contracts_from_file(file_path, repo_path)
            
            # Step 3: Extract API contracts from previous version
            # Try to get from Neo4j (for now, return None - will compare against empty list)
            print("Step 2/7: Extracting API contracts from previous version...")
            before_contracts = await self._get_existing_contracts_from_neo4j(file_path)
            
            # If no Neo4j data, use empty list (all will be marked as ADDED)
            # In production, this would use git to get previous version or query Neo4j
            if not before_contracts:
                before_contracts = []
                print("   ⚠️ No previous contracts found - all changes will be marked as ADDED")
                print("   Note: For breaking change detection, provide 'before' contracts via Neo4j or git")
            
            # Step 4: Compare contracts to detect changes
            print("Step 3/7: Comparing API contracts...")
            changes = self.api_analyzer.compare_contracts(before_contracts, after_contracts)
            
            # Step 5: Find API consumers
            print("Step 4/7: Finding API consumers...")
            consumers = await self._find_all_consumers(after_contracts, repo_path)
            
            # Step 6: Store in Neo4j
            print("Step 5/7: Storing API contracts in Neo4j...")
            await self._store_api_contracts_in_neo4j(after_contracts, file_path, consumers)
            
            # Step 7: AI Analysis
            print("Step 6/7: Running AI analysis...")
            try:
                ai_insights = await self.ai_analyzer.analyze_api_contract_impact(
                    file_path, code_diff, changes, consumers, repository_path=repo_path
                )
            except Exception as ai_error:
                print(f"⚠️ AI analysis failed (non-blocking): {ai_error}")
                ai_insights = self._fallback_api_analysis(changes, consumers)
            
            # Step 8: Risk Scoring
            print("Step 7/7: Calculating risk score...")
            breaking_changes = [c for c in changes if c.change_type == 'BREAKING']
            consumer_count = sum(len(cons) for cons in consumers.values())
            risk_score = self._calculate_api_risk_score(breaking_changes, consumer_count, ai_insights)
            
            # Compile results
            result = self._compile_results(
                analysis_id,
                file_path,
                commit_sha,
                repository,
                changes,
                consumers,
                ai_insights,
                risk_score,
                start_time,
                commit_message
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"✅ API Contract Analysis Complete in {duration:.1f}s")
            print(f"   Changes Detected: {len(changes)} ({len(breaking_changes)} breaking)")
            print(f"   Consumers Affected: {consumer_count}")
            print(f"   Risk Score: {risk_score['score']}/10 - {risk_score['level']}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"\n❌ API Contract Analysis failed: {str(e)}")
            raise
    
    async def _get_repository_path(self, repository: str, github_repo_url: Optional[str], github_branch: str) -> Optional[str]:
        """Get repository path (local or cloned from GitHub)"""
        if github_repo_url:
            # Clone/update from GitHub
            repo_path = await self.github_fetcher.fetch_repository(github_repo_url, github_branch)
            if repo_path:
                return repo_path
        
        # Try local paths - check if repository is a subfolder in sample-repo
        possible_paths = [
            os.path.join("/sample-repo", repository),  # Docker: /sample-repo/backend-api-service
            os.path.join("sample-repo", repository),   # Local: sample-repo/backend-api-service
            os.path.join(os.getcwd(), "sample-repo", repository),  # Local with cwd
            os.path.join("/app", "sample-repo", repository),  # Alternative Docker
            repository,  # As-is
            # Also try sample-repo root if repository name matches a subfolder
            "/sample-repo",  # Docker root
            os.path.join(os.getcwd(), "sample-repo"),  # Local root
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"   📁 Found repository at: {path}")
                return path
        
        print(f"   ⚠️ Repository path not found for: {repository}")
        print(f"      Tried paths: {possible_paths[:5]}")
        return None
    
    async def _extract_contracts_from_file(self, file_path: str, repo_path: Optional[str]) -> List[Dict]:
        """Extract API contracts from a file"""
        if not repo_path:
            print(f"   ⚠️ Repository path not provided")
            return []
        
        # Find full file path - handle nested repo structure (repo/repo/src/...)
        full_path = None
        possible_paths = [
            os.path.join(repo_path, file_path),  # repo_path + file_path
            file_path,  # Absolute path
            os.path.join(repo_path, file_path.lstrip('/')),  # Remove leading /
            # Handle nested structure: if repo is cloned as "backend-api-service" but contains "backend-api-service" folder
            os.path.join(repo_path, "backend-api-service", file_path.replace("backend-api-service/", "")),
            os.path.join(repo_path, file_path.split("/", 1)[-1] if "/" in file_path else file_path),  # Remove first folder if duplicated
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                full_path = path
                print(f"   📄 Found file at: {full_path}")
                break
        
        if not full_path:
            print(f"   ⚠️ File not found: {file_path}")
            print(f"      Repository path: {repo_path}")
            print(f"      Tried paths: {possible_paths[:3]}")
            # List directory to help debug
            if repo_path and os.path.exists(repo_path):
                try:
                    dirs = [d for d in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, d))][:5]
                    print(f"      Repository contents (first 5): {dirs}")
                except:
                    pass
            return []
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                print(f"   ⚠️ File is empty: {full_path}")
                return []
            
            contracts = self.api_extractor.extract_api_contracts(file_path, content)
            print(f"   ✅ Extracted {len(contracts)} API contracts from {os.path.basename(full_path)}")
            if contracts:
                for contract in contracts[:3]:  # Show first 3
                    print(f"      - {contract.get('method')} {contract.get('path')}")
            return contracts
            
        except Exception as e:
            print(f"   ⚠️ Error extracting contracts: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_existing_contracts_from_neo4j(self, file_path: str) -> Optional[List[Dict]]:
        """Get existing API contracts from Neo4j for this file"""
        # Try to get existing contracts from Neo4j
        # For now, return None (will compare against empty list)
        # In production, this would query Neo4j for existing API endpoints from this file
        return None
    
    async def _find_all_consumers(self, contracts: List[Dict], repo_path: Optional[str]) -> Dict[str, List[Dict]]:
        """
        Find all consumers for each API contract
        Searches across multiple repositories if configured
        """
        consumers_map = {}
        
        # Get list of repositories to search
        consumer_repos = get_consumer_repositories()
        
        print(f"   🔍 Searching for API consumers...")
        print(f"      Current repository: {repo_path or 'N/A'}")
        print(f"      Additional repositories to search: {len(consumer_repos)}")
        
        for contract in contracts:
            endpoint = contract['path']
            method = contract['method']
            key = f"{method} {endpoint}"
            
            all_consumers = []
            
            # 1. Search in current repository
            if repo_path:
                consumers = self.api_extractor.find_api_consumers(endpoint, method, repo_path)
                for consumer in consumers:
                    consumer['source_repo'] = 'current'
                    all_consumers.append(consumer)
            
            # 2. Search in other configured repositories (cross-team discovery)
            for repo_identifier in consumer_repos:
                try:
                    # Fetch repository
                    other_repo_path = await self.github_fetcher.fetch_repository(
                        repo_identifier, 
                        branch="main"
                    )
                    
                    if other_repo_path:
                        consumers = self.api_extractor.find_api_consumers(endpoint, method, other_repo_path)
                        for consumer in consumers:
                            consumer['source_repo'] = repo_identifier
                            all_consumers.append(consumer)
                        print(f"      ✅ Found {len(consumers)} consumers in {repo_identifier}")
                except Exception as e:
                    print(f"      ⚠️ Failed to search {repo_identifier}: {e}")
                    continue
            
            # 3. Also check Neo4j for registered consumers (if registry is implemented)
            try:
                neo4j_consumers = await neo4j_client.get_api_consumers(endpoint, method)
                for consumer in neo4j_consumers:
                    consumer['source'] = 'neo4j_registry'
                    # Avoid duplicates
                    if not any(
                        c.get('file_path') == consumer.get('file_path') 
                        for c in all_consumers
                    ):
                        all_consumers.append(consumer)
            except Exception as e:
                print(f"      ⚠️ Neo4j consumer lookup failed: {e}")
            
            consumers_map[key] = all_consumers
        
        total_consumers = sum(len(cons) for cons in consumers_map.values())
        unique_repos = set()
        for consumers in consumers_map.values():
            for consumer in consumers:
                source = consumer.get('source_repo', consumer.get('source', 'unknown'))
                unique_repos.add(source)
        
        print(f"   ✅ Found {total_consumers} API consumers across {len(contracts)} endpoints")
        print(f"      Searched {len(unique_repos)} repositories/sources")
        
        return consumers_map
    
    async def _store_api_contracts_in_neo4j(self, contracts: List[Dict], file_path: str, consumers: Dict[str, List[Dict]]):
        """Store API contracts and consumer relationships in Neo4j"""
        try:
            for contract in contracts:
                endpoint = contract['path']
                method = contract['method']
                
                # Create API endpoint node
                await neo4j_client.create_api_endpoint_node(
                    endpoint=endpoint,
                    method=method,
                    file_path=file_path,
                    properties={
                        'framework': contract.get('framework', 'unknown'),
                        'parameters': contract.get('parameters', []),
                        'return_type': contract.get('return_type'),
                        'line_number': contract.get('line_number', 0)
                    }
                )
                
                # Create consumer relationships
                key = f"{method} {endpoint}"
                for consumer in consumers.get(key, []):
                    consumer_file = consumer['file_path'].split('/')[-1]
                    
                    # Ensure module node exists
                    await neo4j_client.create_module_node(
                        name=consumer_file,
                        properties={'path': consumer['file_path']}
                    )
                    
                    # Create CONSUMES_API relationship
                    await neo4j_client.create_api_consumer_relationship(
                        consumer_file=consumer_file,
                        api_endpoint=endpoint,
                        api_method=method,
                        line_number=consumer.get('line_number', 0)
                    )
            
            print("   ✅ API contracts stored in Neo4j")
            
        except Exception as e:
            print(f"   ⚠️ Neo4j storage failed: {e}")
    
    def _calculate_api_risk_score(self, breaking_changes: List[APIContractChange], consumer_count: int, ai_insights: Dict) -> Dict:
        """Calculate risk score for API contract changes"""
        # Use API analyzer's scoring
        base_score = self.api_analyzer.calculate_breaking_change_score(breaking_changes, consumer_count)
        
        # Adjust based on AI insights
        ai_risk = len(ai_insights.get('risks', []))
        if ai_risk > 0:
            base_score += min(ai_risk * 0.5, 2.0)
        
        # Determine risk level
        if base_score >= 7.5:
            level = "CRITICAL"
            color = "#dc3545"
        elif base_score >= 5.5:
            level = "HIGH"
            color = "#fd7e14"
        elif base_score >= 3.5:
            level = "MEDIUM"
            color = "#ffc107"
        else:
            level = "LOW"
            color = "#28a745"
        
        return {
            "score": round(base_score, 1),
            "level": level,
            "color": color,
            "breakdown": {
                "breaking_changes": len(breaking_changes),
                "consumer_count": consumer_count,
                "ai_analysis": ai_risk
            }
        }
    
    def _fallback_api_analysis(self, changes: List[APIContractChange], consumers: Dict[str, List[Dict]]) -> Dict:
        """Fallback AI analysis if AI fails"""
        breaking_count = len([c for c in changes if c.change_type == 'BREAKING'])
        total_consumers = sum(len(cons) for cons in consumers.values())
        
        return {
            "summary": f"Detected {len(changes)} API contract changes ({breaking_count} breaking). {total_consumers} consumers may be affected.",
            "risks": [
                f"{breaking_count} breaking changes detected - will cause API consumers to fail",
                f"{total_consumers} consumers found - coordinate updates before deployment"
            ] if breaking_count > 0 else [],
            "recommendations": [
                "Review all breaking changes before deployment",
                "Update API consumers before deploying changes",
                "Consider API versioning for backward compatibility"
            ] if breaking_count > 0 else [
                "Changes are non-breaking - safe to deploy"
            ]
        }
    
    def _compile_results(
        self,
        analysis_id: str,
        file_path: str,
        commit_sha: str,
        repository: str,
        changes: List[APIContractChange],
        consumers: Dict[str, List[Dict]],
        ai_insights: Dict,
        risk_score: Dict,
        start_time: datetime,
        commit_message: str = ""
    ) -> Dict:
        """Compile all results into final format"""
        
        breaking_changes = [c for c in changes if c.change_type == 'BREAKING']
        total_consumers = sum(len(cons) for cons in consumers.values())
        
        return {
            "id": analysis_id,
            "type": "api_contract_change",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "commit_sha": commit_sha,
            "commit_message": commit_message,
            "repository": repository,
            "file_path": file_path,
            "risk_score": risk_score,
            "api_changes": [
                {
                    "endpoint": c.endpoint,
                    "method": c.method,
                    "change_type": c.change_type,
                    "details": c.details
                }
                for c in changes
            ],
            "consumers": consumers,
            "ai_insights": ai_insights,
            "summary": {
                "total_changes": len(changes),
                "breaking_changes": len(breaking_changes),
                "total_consumers": total_consumers,
                "affected_endpoints": len(set(c.endpoint for c in changes))
            },
            "metadata": {
                "analyzer_version": "1.0.0",
                "analysis_type": "api_contract_change"
            }
        }

