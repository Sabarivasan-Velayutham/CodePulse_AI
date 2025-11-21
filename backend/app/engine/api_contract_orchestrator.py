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
from app.config import get_consumer_repositories, CONSUMER_SEARCH_METHOD, GITHUB_TOKEN


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
            
            # Step 2.5: Identify which endpoints are actually in the diff
            endpoints_in_diff = self._identify_endpoints_in_diff(code_diff, after_contracts) if code_diff else set()
            if endpoints_in_diff:
                print(f"   🔍 Endpoints found in diff: {endpoints_in_diff}")
            
            # Step 3: Extract API contracts from previous version
            # Try to get from Neo4j first
            print("Step 2/7: Extracting API contracts from previous version...")
            before_contracts = await self._get_existing_contracts_from_neo4j(file_path)
            
            # If no Neo4j data, try to extract from code diff
            if not before_contracts and code_diff:
                print("   🔍 Attempting to extract 'before' contracts from code diff...")
                before_contracts = await self._extract_contracts_from_diff(code_diff, file_path)
                if before_contracts:
                    print(f"   ✅ Successfully extracted {len(before_contracts)} 'before' contracts from diff")
            
            # If still no data, use empty list (all will be marked as ADDED)
            # But only show warning if we couldn't extract from diff AND endpoints_in_diff is empty
            if not before_contracts:
                before_contracts = []
                # Only show warning if we don't know which endpoints changed
                if not endpoints_in_diff:
                    print("   ⚠️ No previous contracts found - all changes will be marked as ADDED")
                    print("   Note: For breaking change detection, provide 'before' contracts via Neo4j or git")
            
            # Step 4: Compare contracts to detect changes
            print("Step 3/7: Comparing API contracts...")
            changes = self.api_analyzer.compare_contracts(before_contracts, after_contracts)
            
            # Step 4.5: Filter changes to only include endpoints that were actually changed (in diff)
            # This prevents showing all endpoints when only one was modified
            if endpoints_in_diff:
                print(f"   🔍 Filtering to {len(endpoints_in_diff)} endpoints found in diff...")
                filtered_changes = []
                for change in changes:
                    api_key = f"{change.method} {change.endpoint}"
                    # Include if it's in the diff, has consumers, or is breaking
                    if api_key in endpoints_in_diff:
                        filtered_changes.append(change)
                    elif change.change_type == 'BREAKING':
                        # Include breaking changes even if not explicitly in diff (might be path changes)
                        # But check if endpoint path is mentioned in diff
                        endpoint_mentioned = (
                            change.endpoint.lower() in code_diff.lower() or 
                            change.endpoint.split('/')[-1] in code_diff.lower() or
                            change.method.lower() in code_diff.lower()
                        ) if code_diff else True
                        if endpoint_mentioned:
                            filtered_changes.append(change)
                    else:
                        # Check if any endpoint path matches (for path changes)
                        endpoint_in_diff = any(
                            ep.split()[-1] in change.endpoint or change.endpoint in ep.split()[-1]
                            for ep in endpoints_in_diff
                        )
                        if endpoint_in_diff:
                            filtered_changes.append(change)
                
                if filtered_changes:
                    changes = filtered_changes
                    print(f"   ✅ Filtered to {len(changes)} relevant changes")
            
            # Step 5: Find API consumers
            print("Step 4/7: Finding API consumers...")
            consumers = await self._find_all_consumers(after_contracts, repo_path)
            
            # Step 4.5: Enhance based on diff analysis to detect breaking changes
            # This helps detect breaking changes even when before state is unknown
            # We analyze the diff directly, not relying on commit message keywords
            if not before_contracts and code_diff:
                print("   🔍 Analyzing diff for breaking change indicators...")
                changes = self._enhance_breaking_changes_from_diff(changes, code_diff, endpoints_in_diff, commit_message)
            
            # Also check if endpoints with consumers have response type changes (even if before contracts exist)
            # This catches cases where response type changed but before/after comparison didn't catch it
            if code_diff:
                changes = self._enhance_breaking_changes_from_response_type(changes, code_diff, consumers, endpoints_in_diff)
            
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
            
            # Filter consumers to only show consumers for endpoints that were actually changed
            # This prevents showing consumers for unrelated endpoints in the same file
            filtered_consumers = {}
            # Get the set of endpoint keys that are actually in the changes list
            # This ensures we only show consumers for endpoints that were modified
            changed_endpoint_keys = {f"{c.method} {c.endpoint}" for c in changes}
            
            # Also include endpoints that are in the diff (what was actually changed)
            if endpoints_in_diff:
                changed_endpoint_keys.update(endpoints_in_diff)
            
            # Only include consumers for endpoints that were actually changed
            for api_key, consumer_list in consumers.items():
                if api_key in changed_endpoint_keys:
                    filtered_consumers[api_key] = consumer_list
                else:
                    # Debug: log why we're excluding this consumer
                    if consumer_list:
                        print(f"   🔍 Excluding consumers for {api_key} (not in changed endpoints: {changed_endpoint_keys})")
            
            # Compile results
            result = self._compile_results(
                analysis_id,
                file_path,
                commit_sha,
                repository,
                changes,
                filtered_consumers,  # Use filtered consumers
                ai_insights,
                risk_score,
                start_time,
                commit_message,
                endpoints_in_diff
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
            # Clone/update from GitHub (sync function, run in executor to avoid blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            repo_path = await loop.run_in_executor(None, self.github_fetcher.fetch_repository, github_repo_url, github_branch)
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
    
    def _identify_endpoints_in_diff(self, code_diff: str, contracts: List[Dict]) -> set:
        """
        Identify which API endpoints are mentioned in the diff
        Returns set of API keys (e.g., "POST /api/stocks/buy")
        """
        if not code_diff or not contracts:
            return set()
        
        endpoints_in_diff = set()
        import re
        
        # Extract method names and paths from diff more accurately
        # Look for Spring Boot annotations in diff: @PostMapping("/buy") or @GetMapping("/stocks")
        # Also handle annotations without paths: @GetMapping (uses class path only)
        annotation_pattern = r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(?:\([^)]*["\']([^"\']*)["\']\)|\(\)|)'
        matches = re.findall(annotation_pattern, code_diff, re.IGNORECASE)
        
        # Store (method, path) pairs from diff
        diff_endpoints = set()
        for match in matches:
            if len(match) >= 1:
                http_method = match[0].upper()
                method_path = match[1].strip('/') if len(match) > 1 and match[1] else ""
                diff_endpoints.add((http_method, method_path))
                if method_path:
                    print(f"      🔍 Found in diff: {http_method} /{method_path}")
                else:
                    print(f"      🔍 Found in diff: {http_method} (class-level, no path)")
        
        if not diff_endpoints:
            print(f"      ⚠️ No endpoints found in diff annotations")
            return set()
        
        # Match contracts to diff - must match BOTH method AND path
        for contract in contracts:
            method = contract.get('method', '').upper()
            full_path = contract.get('path', '')
            path_clean = full_path.strip('/').strip()
            
            # Check if this contract matches any diff endpoint
            for diff_method, diff_path in diff_endpoints:
                # Method must match EXACTLY
                if method != diff_method:
                    continue
                
                # Path must match - check if diff path is a suffix of the full path
                # e.g., diff has "buy", contract has "api/stocks/buy"
                # The diff path should be the last segment(s) of the contract path
                if diff_path:
                    # Split both paths into segments
                    path_segments = path_clean.split('/')
                    diff_segments = diff_path.split('/')
                    
                    # Check if the last N segments of path_clean match diff_segments exactly
                    # e.g., ["api", "stocks", "buy"][-1:] == ["buy"] -> True
                    if len(path_segments) >= len(diff_segments):
                        contract_suffix = path_segments[-len(diff_segments):]
                        if contract_suffix == diff_segments:
                            api_key = f"{method} {full_path}"
                            endpoints_in_diff.add(api_key)
                            print(f"      ✅ Matched: {api_key} (diff: {diff_method} /{diff_path})")
                            break
                    
                    # Also check for path changes - if diff has old path, match new path too
                    # e.g., diff shows "/account/{accountId}" removed, contract has "/by-account/{accountId}"
                    # We'll handle this in the path change detection
                else:
                    # Empty diff path means class-level only - match if contract path equals class path
                    # This is less common, but handle it
                    # For class-level mappings, we need to check if the contract path matches the class base path
                    # For now, if diff has no path and contract has a simple path, it might match
                    if not path_clean or len(path_clean.split('/')) <= 2:  # Simple paths like "api/stocks"
                        api_key = f"{method} {full_path}"
                        endpoints_in_diff.add(api_key)
                        print(f"      ✅ Matched (class-level): {api_key}")
                        break
        
        return endpoints_in_diff
    
    async def _get_existing_contracts_from_neo4j(self, file_path: str) -> Optional[List[Dict]]:
        """Get existing API contracts from Neo4j for this file"""
        # Try to get existing contracts from Neo4j
        # For now, return None (will compare against empty list)
        # In production, this would query Neo4j for existing API endpoints from this file
        return None
    
    async def _extract_contracts_from_diff(self, code_diff: str, file_path: str) -> List[Dict]:
        """
        Extract API contracts from the 'before' state in a git diff
        Uses a smarter approach: reconstructs the file by keeping context and removed lines
        Also extracts only the changed method's contract for better accuracy
        """
        if not code_diff:
            return []
        
        # Better diff parsing: maintain context around changes
        # We need to reconstruct a more complete file structure
        before_lines = []
        lines = code_diff.split('\n')
        i = 0
        in_hunk = False
        hunk_start = 0
        
        # First, collect all context lines (unchanged) to build a base
        context_lines = []
        removed_lines = []
        added_lines = []
        
        while i < len(lines):
            line = lines[i]
            
            # Skip diff headers
            if line.startswith('@@'):
                in_hunk = True
                # Extract line numbers from hunk header: @@ -start,count +start,count @@
                # We can use this to understand context
                i += 1
                continue
            if line.startswith('diff --git') or line.startswith('index ') or line.startswith('---') or line.startswith('+++'):
                i += 1
                continue
            
            # Only process lines within a hunk (between @@ markers)
            if in_hunk:
                # Process diff lines
                if line.startswith(' '):
                    # Unchanged line - part of both before and after
                    context_lines.append(line[1:])
                    before_lines.append(line[1:])
                elif line.startswith('-'):
                    # Removed line - only in before
                    removed_lines.append(line[1:])
                    before_lines.append(line[1:])
                elif line.startswith('+'):
                    # Added line - only in after, skip for before
                    added_lines.append(line[1:])
                # Lines starting with \ are continuation (rare)
            
            i += 1
        
        if not before_lines:
            return []
        
        # Reconstruct file content from before lines
        # We need to include enough context to make the file parseable
        # Try to build a minimal valid file structure
        before_content = '\n'.join(before_lines)
        
        # Extract contracts from the "before" content
        try:
            contracts = self.api_extractor.extract_api_contracts(file_path, before_content)
            if contracts:
                print(f"   ✅ Extracted {len(contracts)} 'before' contracts from diff")
                for contract in contracts[:3]:
                    print(f"      - {contract.get('method')} {contract.get('path')}")
            return contracts
        except Exception as e:
            print(f"   ⚠️ Error extracting contracts from diff: {e}")
            # If extraction failed, try a more aggressive approach
            # Look for method signatures in removed lines
            return self._extract_contracts_from_removed_lines(removed_lines, file_path)
    
    def _extract_contracts_from_removed_lines(self, removed_lines: List[str], file_path: str) -> List[Dict]:
        """Fallback: Extract API contracts from removed lines only"""
        if not removed_lines:
            return []
        
        # Try to find method signatures with annotations
        import re
        contracts = []
        
        # Look for Spring Boot annotations followed by method signatures
        i = 0
        while i < len(removed_lines):
            line = removed_lines[i]
            
            # Check for mapping annotations
            mapping_match = re.search(r'@(Get|Post|Put|Delete|Patch|Request)Mapping', line, re.IGNORECASE)
            if mapping_match:
                method = mapping_match.group(1).upper()
                
                # Extract path from annotation
                path_match = re.search(r'["\']([^"\']+)["\']', line)
                method_path = path_match.group(1) if path_match else ""
                
                # Look ahead for method signature
                j = i + 1
                while j < len(removed_lines) and j < i + 5:
                    method_line = removed_lines[j]
                    if 'public' in method_line and 'ResponseEntity' in method_line:
                        # Found method - try to extract parameters
                        # For now, create a basic contract
                        # We'll need to infer the full path from class-level mapping
                        # This is a simplified extraction
                        full_path = method_path  # Will be combined with class path in extractor
                        
                        contracts.append({
                            'method': method,
                            'path': full_path,
                            'parameters': [],  # Simplified - would need full parsing
                            'return_type': None,
                            'framework': 'spring_boot',
                            'line_number': 0
                        })
                        break
                    j += 1
            
            i += 1
        
        return contracts
    
    def _enhance_breaking_changes_from_response_type(
        self,
        changes: List[APIContractChange],
        code_diff: str,
        consumers: Dict[str, List[Dict]],
        endpoints_in_diff: Optional[set] = None
    ) -> List[APIContractChange]:
        """
        Enhance breaking change detection based on response type changes
        If an endpoint has consumers and its response type changed, it's breaking
        """
        if not code_diff:
            return changes
        
        import re
        enhanced_changes = []
        
        # Look for response type changes in diff
        response_changes = []
        lines = code_diff.split('\n')
        i = 0
        while i < len(lines) - 1:
            # Strip leading whitespace for comparison (diff lines may have indentation)
            line_i_stripped = lines[i].lstrip()
            line_i1_stripped = lines[i+1].lstrip() if i+1 < len(lines) else ""
            
            # Check for direct response type change on consecutive lines
            # Handle both with and without leading whitespace
            if (line_i_stripped.startswith('-') and 'ResponseEntity<?>' in line_i_stripped and
                line_i1_stripped.startswith('+') and 'ResponseEntity<' in line_i1_stripped and '<?>' not in line_i1_stripped):
                # Extract the new response type
                type_match = re.search(r'ResponseEntity<(\w+)>', line_i1_stripped)
                if type_match:
                    response_changes.append(type_match.group(1))
                    print(f"   🔍 Found response type change: ResponseEntity<?> → ResponseEntity<{type_match.group(1)}>")
            
            # Also check for method signature changes within a few lines
            if i < len(lines) - 3:
                for j in range(i+1, min(i+5, len(lines))):
                    line_j_stripped = lines[j].lstrip() if j < len(lines) else ""
                    if (line_i_stripped.startswith('-') and 'ResponseEntity<?>' in line_i_stripped and
                        line_j_stripped.startswith('+') and 'ResponseEntity<' in line_j_stripped and '<?>' not in line_j_stripped):
                        type_match = re.search(r'ResponseEntity<(\w+)>', line_j_stripped)
                        if type_match:
                            response_changes.append(type_match.group(1))
                            print(f"   🔍 Found response type change (within 5 lines): ResponseEntity<?> → ResponseEntity<{type_match.group(1)}>")
                            break
            
            i += 1
        
        # If we found response type changes, mark affected endpoints as breaking
        # Response type changes are ALWAYS breaking, even without consumers (future consumers will be affected)
        if response_changes:
            print(f"   🔍 Found response type changes: {response_changes}")
            for change in changes:
                api_key = f"{change.method} {change.endpoint}"
                
                # Check if this endpoint has consumers
                has_consumers = consumers and api_key in consumers and len(consumers.get(api_key, [])) > 0
                
                # Check if endpoint is mentioned in diff (response type change affects it)
                # Look for method names, endpoint paths, or class-level mappings
                code_diff_lower = code_diff.lower()
                endpoint_mentioned = (
                    change.endpoint.lower() in code_diff_lower or
                    change.method.lower() in code_diff_lower or
                    any(method_name.lower() in code_diff_lower for method_name in ['getAllStocks', 'getAllProducts', 'getAllAuctions', 'getAllTransactions'])
                )
                
                # Also check if endpoint is in endpoints_in_diff (if available)
                is_in_diff = endpoints_in_diff and api_key in endpoints_in_diff if endpoints_in_diff else False
                
                # For class-level mappings (like @GetMapping without path), check if method name matches
                # The diff might have @GetMapping without path, and we need to match it to the endpoint
                is_class_level_match = False
                if not is_in_diff and not endpoint_mentioned:
                    # Check if this is a GET endpoint and diff has @GetMapping without path
                    if change.method.upper() == 'GET' and '@GetMapping' in code_diff:
                        # Check if the endpoint path is simple (like /api/stocks or /api/products)
                        # and matches the class-level mapping pattern
                        path_parts = change.endpoint.strip('/').split('/')
                        if len(path_parts) <= 2:  # Simple paths like "api/stocks"
                            # Check if the last part matches common patterns
                            last_part = path_parts[-1] if path_parts else ""
                            if last_part in ['stocks', 'products', 'auctions', 'transactions', 'accounts']:
                                is_class_level_match = True
                                endpoint_mentioned = True
                                print(f"   🔍 Class-level match: {api_key} matches @GetMapping pattern for {last_part}")
                
                # Additional check: if we found response type changes and this is a GET endpoint
                # with a simple path, and the diff has @GetMapping, it's likely the same endpoint
                if not endpoint_mentioned and not is_in_diff and not is_class_level_match:
                    if change.method.upper() == 'GET' and '@GetMapping' in code_diff:
                        # Check if method name is in diff (like getAllStocks, getAllProducts)
                        method_names_to_check = {
                            'stocks': 'getAllStocks',
                            'products': 'getAllProducts',
                            'auctions': 'getAllAuctions',
                            'transactions': 'getAllTransactions',
                            'accounts': 'getAllAccounts'
                        }
                        path_parts = change.endpoint.strip('/').split('/')
                        last_part = path_parts[-1] if path_parts else ""
                        if last_part in method_names_to_check:
                            method_name = method_names_to_check[last_part]
                            if method_name.lower() in code_diff_lower:
                                endpoint_mentioned = True
                                is_class_level_match = True
                                print(f"   🔍 Method name match: {method_name} found in diff for {api_key}")
                
                # Response type changes are ALWAYS breaking, regardless of consumers
                # If endpoint is mentioned in diff (or is in endpoints_in_diff) and response type changed, it's breaking
                if (is_in_diff or endpoint_mentioned or is_class_level_match) and change.change_type != 'BREAKING':
                    reason_parts = [f'Response type changed to {", ".join(response_changes)}']
                    if has_consumers:
                        reason_parts.append('Has existing consumers')
                    
                    enhanced_changes.append(APIContractChange(
                        endpoint=change.endpoint,
                        method=change.method,
                        change_type='BREAKING',
                        details={
                            **change.details,
                            'reason': '; '.join(reason_parts),
                            'severity': 'CRITICAL',
                            'detected_from': 'response_type_change'
                        }
                    ))
                    print(f"   ⚠️ Marked {change.method} {change.endpoint} as BREAKING (response type changed)")
                else:
                    enhanced_changes.append(change)
        else:
            enhanced_changes = changes
        
        return enhanced_changes
    
    def _enhance_breaking_changes_from_diff(
        self,
        changes: List[APIContractChange],
        code_diff: str,
        endpoints_in_diff: Optional[set] = None,
        commit_message: str = ""
    ) -> List[APIContractChange]:
        """
        Analyze diff directly to detect breaking changes when before contracts aren't available
        Looks for indicators like: added required parameters, path changes, response type changes
        """
        if not code_diff:
            return changes
        
        import re
        enhanced_changes = []
        
        # Look for added required parameters in diff
        # Pattern: @RequestParam Type paramName (without required = false)
        # Also check for @RequestParam in added lines (+)
        added_params = []
        lines = code_diff.split('\n')
        for line in lines:
            if line.startswith('+') and '@RequestParam' in line:
                # Check if it's required (default) or optional
                if 'required' not in line or 'required\s*=\s*false' not in line:
                    # Extract parameter name
                    param_match = re.search(r'@RequestParam\s+(?:\([^)]*\)\s*)?(\w+)\s+(\w+)', line)
                    if param_match:
                        added_params.append((param_match.group(1), param_match.group(2)))
        
        # Look for path changes in annotations
        # Pattern: -@GetMapping("/old") followed by +@GetMapping("/new") (may be on different lines)
        # First, find all removed and added mappings
        removed_mappings = []
        added_mappings = []
        
        lines = code_diff.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('-') and '@' in line and 'Mapping' in line:
                # Extract mapping annotation
                mapping_match = re.search(r'@(\w+Mapping)\s*\([^)]*["\']([^"\']+)["\']', line)
                if mapping_match:
                    removed_mappings.append((mapping_match.group(1), mapping_match.group(2)))
            elif line.startswith('+') and '@' in line and 'Mapping' in line:
                # Extract mapping annotation
                mapping_match = re.search(r'@(\w+Mapping)\s*\([^)]*["\']([^"\']+)["\']', line)
                if mapping_match:
                    added_mappings.append((mapping_match.group(1), mapping_match.group(2)))
            i += 1
        
        # Match removed and added mappings that are similar (path changes)
        path_changes = []
        for removed_map, removed_path in removed_mappings:
            for added_map, added_path in added_mappings:
                # Check if same method type and similar paths
                if removed_map == added_map:
                    # Check if paths are similar (one segment difference)
                    # Also handle cases where paths might be full paths vs relative paths
                    removed_norm = removed_path.strip('/')
                    added_norm = added_path.strip('/')
                    
                    # Direct similarity check
                    if self.api_analyzer._is_similar_path(removed_path, added_path):
                        path_changes.append((removed_path, added_path))
                    # Also check if one is a segment of the other (for nested paths)
                    elif (removed_norm in added_norm or added_norm in removed_norm) and removed_norm != added_norm:
                        # Check if they differ by exactly one segment
                        removed_segments = removed_norm.split('/')
                        added_segments = added_norm.split('/')
                        if abs(len(removed_segments) - len(added_segments)) <= 1:
                            path_changes.append((removed_path, added_path))
        
        # Look for response type changes
        # Pattern: -ResponseEntity<?> and +ResponseEntity<SpecificType> (may be on different lines)
        # Also check for method signatures that changed return types
        response_changes = []
        lines = code_diff.split('\n')
        i = 0
        while i < len(lines) - 1:
            # Check for direct response type change on consecutive lines
            if (lines[i].startswith('-') and 'ResponseEntity<?>' in lines[i] and
                lines[i+1].startswith('+') and 'ResponseEntity<' in lines[i+1] and '<?>' not in lines[i+1]):
                # Extract the new response type
                type_match = re.search(r'ResponseEntity<(\w+)>', lines[i+1])
                if type_match:
                    response_changes.append(type_match.group(1))
            
            # Also check for method signature changes within a few lines
            # Look for method declarations that changed return type
            if i < len(lines) - 3:
                # Check if we have a method signature with return type change
                if (lines[i].startswith('-') and 'ResponseEntity<?>' in lines[i] and
                    any(lines[j].startswith('+') and 'ResponseEntity<' in lines[j] and '<?>' not in lines[j] 
                        for j in range(i+1, min(i+5, len(lines))))):
                    # Find the + line with new response type
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].startswith('+') and 'ResponseEntity<' in lines[j] and '<?>' not in lines[j]:
                            type_match = re.search(r'ResponseEntity<(\w+)>', lines[j])
                            if type_match:
                                response_changes.append(type_match.group(1))
                                break
            
            i += 1
        
        for change in changes:
            api_key = f"{change.method} {change.endpoint}"
            
            # Only enhance endpoints that were in the diff
            if endpoints_in_diff and api_key not in endpoints_in_diff:
                enhanced_changes.append(change)
                continue
            
            # Check if this endpoint has indicators of breaking changes
            should_mark_breaking = False
            reasons = []
            
            # Check for added required parameters
            if added_params and change.change_type == 'ADDED':
                # Check if endpoint path matches the diff context
                # Look for the endpoint path or method in the diff near the parameter addition
                endpoint_mentioned = (
                    change.endpoint.lower() in code_diff.lower() or
                    change.method.lower() in code_diff.lower() or
                    any(param_name.lower() in code_diff.lower() for _, param_name in added_params)
                )
                if endpoint_mentioned:
                    should_mark_breaking = True
                    param_names = ', '.join([name for _, name in added_params])
                    reasons.append(f'Required parameter(s) added: {param_names}')
            
            # Check for path changes
            if path_changes:
                for old_path, new_path in path_changes:
                    # Normalize paths for comparison
                    old_path_norm = old_path.strip('/')
                    new_path_norm = new_path.strip('/')
                    endpoint_norm = change.endpoint.strip('/')
                    
                    # Check if endpoint matches new path (after change) or old path (before change)
                    # For path changes, we might see the new path as ADDED, but it's actually a BREAKING change
                    if (endpoint_norm == new_path_norm or 
                        endpoint_norm.endswith('/' + new_path_norm) or
                        endpoint_norm.endswith('/' + old_path_norm) or
                        new_path_norm in endpoint_norm or
                        old_path_norm in endpoint_norm):
                        should_mark_breaking = True
                        reasons.append(f'Path changed from /{old_path} to /{new_path}')
                        break
            
            # Check for response type changes
            # Response type changes are ALWAYS breaking, even without consumers
            if response_changes:
                # Check if this endpoint's method is mentioned in the diff
                # Response type changes affect the endpoint even if it's marked as ADDED
                # Look for method names or endpoint paths in the diff
                endpoint_mentioned = (
                    change.endpoint.lower() in code_diff.lower() or
                    change.method.lower() in code_diff.lower() or
                    any(method_name.lower() in code_diff.lower() for method_name in ['getAllStocks', 'getAllProducts', 'getAllAuctions', 'getAllTransactions'])
                )
                if endpoint_mentioned:
                    should_mark_breaking = True
                    reasons.append(f'Response type changed to {", ".join(response_changes)}')
            
            if should_mark_breaking and change.change_type != 'BREAKING':
                enhanced_changes.append(APIContractChange(
                    endpoint=change.endpoint,
                    method=change.method,
                    change_type='BREAKING',
                    details={
                        **change.details,
                        'reason': '; '.join(reasons) + ' (Detected from diff analysis)',
                        'severity': 'CRITICAL',
                        'detected_from': 'diff_analysis'
                    }
                ))
                print(f"   ⚠️ Marked {change.method} {change.endpoint} as BREAKING (detected from diff)")
            else:
                enhanced_changes.append(change)
        
        return enhanced_changes
    
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
                    if CONSUMER_SEARCH_METHOD == "api":
                        # Use GitHub API search (no cloning required)
                        print(f"      🔍 Searching {repo_identifier} via GitHub API...")
                        consumers = self.api_extractor.find_api_consumers_via_github_api(
                            endpoint, 
                            method, 
                            repo_identifier,
                            github_token=GITHUB_TOKEN
                        )
                        for consumer in consumers:
                            consumer['source_repo'] = repo_identifier
                            all_consumers.append(consumer)
                        print(f"      ✅ Found {len(consumers)} consumers in {repo_identifier} (via API)")
                    else:
                        # Clone and search locally (default)
                        # fetch_repository is sync, run in executor to avoid blocking
                        import asyncio
                        loop = asyncio.get_event_loop()
                        other_repo_path = await loop.run_in_executor(
                            None, 
                            self.github_fetcher.fetch_repository,
                            repo_identifier,
                            "main"
                        )
                        
                        if other_repo_path:
                            consumers = self.api_extractor.find_api_consumers(endpoint, method, other_repo_path)
                            for consumer in consumers:
                                consumer['source_repo'] = repo_identifier
                                all_consumers.append(consumer)
                            print(f"      ✅ Found {len(consumers)} consumers in {repo_identifier} (via clone)")
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
        
        # If we have breaking changes but score is still low, boost it
        if len(breaking_changes) > 0 and base_score < 3.0:
            # Minimum score for breaking changes should be higher
            base_score = max(base_score, 3.0 + (len(breaking_changes) * 1.0))
        
        # Adjust based on AI insights
        ai_risk = len(ai_insights.get('risks', []))
        if ai_risk > 0:
            base_score += min(ai_risk * 0.5, 2.0)
        
        # Consumer impact multiplier (stronger for breaking changes)
        if len(breaking_changes) > 0 and consumer_count > 0:
            # Breaking changes with consumers are much more critical
            base_score *= 1.5
        
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
        commit_message: str = "",
        endpoints_in_diff: Optional[set] = None
    ) -> Dict:
        """Compile all results into final format"""
        
        breaking_changes = [c for c in changes if c.change_type == 'BREAKING']
        total_consumers = sum(len(cons) for cons in consumers.values())
        
        # Filter to only show affected endpoints (those with consumers or breaking changes)
        # This prevents showing all endpoints when only one was changed
        # Change types:
        # - "ADDED": New endpoint (not in before state) - only show if has consumers or is breaking
        # - "BREAKING": Breaking change (removed endpoint, changed params, etc.) - always show
        # - "MODIFIED": Non-breaking modification - always show
        # - "REMOVED": Endpoint was removed - always show
        affected_changes = []
        for change in changes:
            api_key = f"{change.method} {change.endpoint}"
            has_consumers = api_key in consumers and len(consumers.get(api_key, [])) > 0
            is_breaking = change.change_type == 'BREAKING'
            is_removed = change.change_type == 'REMOVED'
            is_modified = change.change_type == 'MODIFIED'
            was_in_diff = endpoints_in_diff and api_key in endpoints_in_diff if endpoints_in_diff else False
            
            # Priority: If we know which endpoints were in the diff, prioritize those
            # Include if:
            # - It was in the diff (highest priority - this is what actually changed)
            # - It's breaking (always important)
            # - It's removed (always important)
            # - It's modified (non-breaking but still a change)
            # - It's added AND was in diff (only show added endpoints that were actually changed)
            should_include = (
                was_in_diff or  # Was in diff (what actually changed) - highest priority
                is_breaking or  # Breaking changes are always important
                is_removed or  # Removed endpoints are always important
                is_modified  # Modified endpoints are always important
            )
            
            # For ADDED endpoints, only include if they were in the diff (actually changed)
            # OR if they're marked as breaking (from commit message analysis)
            if change.change_type == 'ADDED':
                should_include = was_in_diff or is_breaking
            
            if should_include:
                affected_changes.append(change)
        
        # If no affected changes found but we have breaking changes, include all breaking changes
        if not affected_changes and breaking_changes:
            affected_changes = breaking_changes
        
        # If still no affected changes, include all changes (fallback)
        if not affected_changes:
            affected_changes = changes
        
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
                for c in affected_changes
            ],
            "consumers": consumers,
            "ai_insights": ai_insights,
            "summary": {
                "total_changes": len(affected_changes),  # Only affected changes
                "breaking_changes": len(breaking_changes),
                "total_consumers": total_consumers,
                "affected_endpoints": len(set(c.endpoint for c in affected_changes))
            },
            "metadata": {
                "analyzer_version": "1.0.0",
                "analysis_type": "api_contract_change"
            }
        }

