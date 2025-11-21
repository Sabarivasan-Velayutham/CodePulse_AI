"""
API Contract Extractor
Extracts API endpoint definitions from code files
Supports: Spring Boot (Java), Flask/FastAPI (Python), Express (Node.js), etc.
"""

import re
import os
import requests
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path


class APIContractExtractor:
    """Extracts API endpoint definitions from code"""
    
    def __init__(self):
        # HTTP methods
        self.http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
        
    def extract_api_contracts(self, file_path: str, file_content: str) -> List[Dict]:
        """
        Extract all API endpoint definitions from a code file
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
        
        Returns:
            List of API contract dictionaries
        """
        contracts = []
        
        # Detect framework/language
        framework = self._detect_framework(file_path, file_content)
        
        if framework == 'spring_boot':
            contracts = self._extract_spring_boot_apis(file_content, file_path)
        elif framework == 'flask':
            contracts = self._extract_flask_apis(file_content, file_path)
        elif framework == 'fastapi':
            contracts = self._extract_fastapi_apis(file_content, file_path)
        elif framework == 'express':
            contracts = self._extract_express_apis(file_content, file_path)
        else:
            # Generic extraction (try common patterns)
            contracts = self._extract_generic_apis(file_content, file_path)
        
        return contracts
    
    def _detect_framework(self, file_path: str, content: str) -> str:
        """Detect the web framework used"""
        file_lower = file_path.lower()
        content_lower = content.lower()
        
        # Spring Boot (Java)
        if file_lower.endswith('.java') and ('@RestController' in content or '@Controller' in content):
            return 'spring_boot'
        
        # Flask (Python)
        if file_lower.endswith('.py') and ('from flask import' in content_lower or '@app.route' in content_lower):
            return 'flask'
        
        # FastAPI (Python)
        if file_lower.endswith('.py') and ('from fastapi import' in content_lower or 'FastAPI' in content):
            return 'fastapi'
        
        # Express (Node.js/TypeScript)
        if (file_lower.endswith('.js') or file_lower.endswith('.ts')) and ('express' in content_lower or 'router.' in content_lower):
            return 'express'
        
        return 'generic'
    
    def _extract_spring_boot_apis(self, content: str, file_path: str) -> List[Dict]:
        """Extract API endpoints from Spring Boot controllers"""
        contracts = []
        lines = content.split('\n')
        
        # Find class-level @RequestMapping
        class_base_path = ""
        class_line = 0
        for i, line in enumerate(lines):
            if '@RequestMapping' in line:
                # Try both formats: @RequestMapping("/path") and @RequestMapping(value = "/path")
                match = re.search(r'@RequestMapping\s*\([^)]*(?:value\s*=\s*)?["\']([^"\']+)["\']', line)
                if match:
                    class_base_path = match.group(1)
                    class_line = i + 1
                    break
        
        # Find method-level annotations
        current_method = None
        current_method_line = 0
        current_params = []
        current_return_type = None
        
        for i, line in enumerate(lines):
            # Check for HTTP method annotations
            # Spring Boot uses camelCase: @GetMapping, @PostMapping, etc.
            for method in self.http_methods:
                # Convert GET -> Get, POST -> Post, etc.
                method_camel = method.capitalize() if len(method) > 1 else method.upper()
                annotation = f'@{method_camel}Mapping'
                if annotation in line:
                    # Extract path - handle multiple formats:
                    # @PostMapping("/buy") - direct string
                    # @PostMapping(value = "/buy") - with value=
                    # @PostMapping() - empty parentheses (uses class path only)
                    # @PostMapping - no parentheses (uses class path only)
                    path = ""
                    # Try to match with parentheses and path (use camelCase annotation)
                    path_match = re.search(rf'@{method_camel}Mapping\s*\([^)]*(?:value\s*=\s*)?["\']([^"\']+)["\']', line)
                    if path_match:
                        path = path_match.group(1)
                    # If no path found but annotation exists, path remains "" which will use class base path only
                    
                    # Combine with class base path
                    full_path = self._combine_paths(class_base_path, path)
                    
                    current_method = method
                    current_method_line = i + 1
                    current_params = []
                    current_return_type = None
                    
                    # Look ahead for method signature
                    for j in range(i + 1, min(i + 10, len(lines))):
                        method_line = lines[j]
                        
                        # Extract return type - improved pattern matching
                        if current_return_type is None:
                            # Try multiple patterns for return type
                            # Pattern 1: public ReturnType methodName(
                            return_match = re.search(r'public\s+(\w+(?:<[^>]+>)?)\s+\w+\s*\(', method_line)
                            if return_match:
                                current_return_type = return_match.group(1)
                            else:
                                # Pattern 2: ResponseEntity<ReturnType> methodName(
                                response_match = re.search(r'ResponseEntity\s*<\s*(\w+(?:<[^>]+>)?)\s*>', method_line)
                                if response_match:
                                    current_return_type = f"ResponseEntity<{response_match.group(1)}>"
                                else:
                                    # Pattern 3: Just look for common return types before method name
                                    # ReturnType methodName( - without public keyword
                                    simple_match = re.search(r'(\w+(?:<[^>]+>)?)\s+\w+\s*\([^)]*\)\s*\{', method_line)
                                    if simple_match and simple_match.group(1) not in ['void', 'private', 'protected', 'static', 'final']:
                                        current_return_type = simple_match.group(1)
                        
                        # Extract parameters - improved pattern matching
                        # Handle @RequestParam, @RequestBody, @PathVariable
                        # Pattern 1: @RequestParam String accountId
                        # Pattern 2: @RequestParam(required = false) String accountId
                        # Pattern 3: @RequestParam(value = "accountId", required = true) String accountId
                        param_patterns = [
                            # @RequestParam(required = false) String accountId
                            r'@RequestParam\s*\([^)]*required\s*=\s*(true|false)',
                            # @RequestParam String accountId (default required = true)
                            r'@RequestParam\s+(?!\()',
                            # @RequestParam(value = "id") String accountId
                            r'@RequestParam\s*\([^)]*\)',
                            # @RequestBody SomeType param
                            r'@RequestBody',
                            # @PathVariable String id
                            r'@PathVariable'
                        ]
                        
                        for pattern in param_patterns:
                            if re.search(pattern, method_line):
                                # Extract parameter details
                                # Try to find the parameter name and type
                                # @RequestParam String accountId or @RequestParam(required = false) String accountId
                                param_match = re.search(
                                    r'@(?:RequestParam|RequestBody|PathVariable)(?:\([^)]*\))?\s+(\w+(?:<[^>]+>)?)\s+(\w+)',
                                    method_line
                                )
                                if param_match:
                                    param_type = param_match.group(1)
                                    param_name = param_match.group(2)
                                    
                                    # Determine if required
                                    is_required = True  # Default
                                    if '@RequestParam' in method_line:
                                        # Check for required = false
                                        required_match = re.search(r'required\s*=\s*(true|false)', method_line)
                                        if required_match:
                                            is_required = required_match.group(1).lower() == 'true'
                                        # If no required specified, default is true for @RequestParam
                                    elif '@PathVariable' in method_line:
                                        # Path variables are always required
                                        is_required = True
                                    elif '@RequestBody' in method_line:
                                        # Request body is typically required unless @RequestBody(required = false)
                                        required_match = re.search(r'required\s*=\s*(true|false)', method_line)
                                        if required_match:
                                            is_required = required_match.group(1).lower() == 'true'
                                        else:
                                            is_required = True  # Default for @RequestBody
                                    
                                    current_params.append({
                                        'name': param_name,
                                        'type': param_type,
                                        'required': is_required,
                                        'location': 'body' if '@RequestBody' in method_line else 'query' if '@RequestParam' in method_line else 'path'
                                    })
                                break  # Found a parameter, move to next line
                        
                        # Method signature complete
                        if '{' in method_line and current_method:
                            break
                    
                    # Create contract
                    if current_method:
                        contracts.append({
                            'method': current_method,
                            'path': full_path,
                            'file_path': file_path,
                            'line_number': current_method_line,
                            'parameters': current_params.copy(),
                            'return_type': current_return_type,
                            'framework': 'spring_boot'
                        })
                        current_method = None
        
        return contracts
    
    def _extract_flask_apis(self, content: str, file_path: str) -> List[Dict]:
        """Extract API endpoints from Flask routes"""
        contracts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Flask route decorator: @app.route('/path', methods=['GET', 'POST'])
            route_match = re.search(r'@(?:app|blueprint|router)\.route\s*\(["\']([^"\']+)["\']', line)
            if route_match:
                path = route_match.group(1)
                
                # Extract methods
                methods_match = re.search(r"methods\s*=\s*\[([^\]]+)\]", line)
                methods = ['GET']  # Default
                if methods_match:
                    methods_str = methods_match.group(1)
                    methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
                
                # Look ahead for function definition
                params = []
                return_type = None
                for j in range(i + 1, min(i + 5, len(lines))):
                    func_line = lines[j]
                    
                    # Extract function parameters
                    func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', func_line)
                    if func_match:
                        params_str = func_match.group(2)
                        # Simple parameter extraction
                        for param in params_str.split(','):
                            param = param.strip()
                            if param and param != 'self':
                                param_name = param.split('=')[0].strip()
                                params.append({
                                    'name': param_name,
                                    'type': 'any',
                                    'required': '=' not in param,
                                    'location': 'query'
                                })
                        break
                
                # Create contracts for each method
                for method in methods:
                    contracts.append({
                        'method': method.upper(),
                        'path': path,
                        'file_path': file_path,
                        'line_number': i + 1,
                        'parameters': params,
                        'return_type': return_type,
                        'framework': 'flask'
                    })
        
        return contracts
    
    def _extract_fastapi_apis(self, content: str, file_path: str) -> List[Dict]:
        """Extract API endpoints from FastAPI routes"""
        contracts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # FastAPI decorator: @app.get('/path'), @router.post('/path')
            for method in self.http_methods:
                decorator_pattern = rf'@(?:app|router)\.{method.lower()}\s*\(["\']([^"\']+)["\']'
                match = re.search(decorator_pattern, line, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    
                    # Look ahead for function definition and Pydantic models
                    params = []
                    return_type = None
                    for j in range(i + 1, min(i + 10, len(lines))):
                        func_line = lines[j]
                        
                        # Extract function parameters with type hints
                        func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(\w+))?', func_line)
                        if func_match:
                            params_str = func_match.group(2)
                            return_type = func_match.group(3)
                            
                            # Parse parameters
                            for param in params_str.split(','):
                                param = param.strip()
                                if param and ':' in param:
                                    parts = param.split(':')
                                    param_name = parts[0].strip()
                                    param_type = parts[1].strip() if len(parts) > 1 else 'any'
                                    is_required = '=' not in param
                                    
                                    params.append({
                                        'name': param_name,
                                        'type': param_type,
                                        'required': is_required,
                                        'location': 'body' if param_type not in ['str', 'int', 'float', 'bool'] else 'query'
                                    })
                            break
                    
                    contracts.append({
                        'method': method.upper(),
                        'path': path,
                        'file_path': file_path,
                        'line_number': i + 1,
                        'parameters': params,
                        'return_type': return_type,
                        'framework': 'fastapi'
                    })
        
        return contracts
    
    def _extract_express_apis(self, content: str, file_path: str) -> List[Dict]:
        """Extract API endpoints from Express.js routes"""
        contracts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Express patterns: router.get('/path', ...), app.post('/path', ...)
            for method in self.http_methods:
                pattern = rf'(?:router|app)\.{method.lower()}\s*\(["\']([^"\']+)["\']'
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    
                    # Extract parameters from route path (e.g., /users/:id)
                    path_params = re.findall(r':(\w+)', path)
                    params = [{
                        'name': p,
                        'type': 'string',
                        'required': True,
                        'location': 'path'
                    } for p in path_params]
                    
                    contracts.append({
                        'method': method.upper(),
                        'path': path,
                        'file_path': file_path,
                        'line_number': i + 1,
                        'parameters': params,
                        'return_type': None,
                        'framework': 'express'
                    })
        
        return contracts
    
    def _extract_generic_apis(self, content: str, file_path: str) -> List[Dict]:
        """Generic API extraction for unknown frameworks"""
        contracts = []
        lines = content.split('\n')
        
        # Look for common patterns
        for i, line in enumerate(lines):
            # Pattern: HTTP_METHOD /path
            for method in self.http_methods:
                pattern = rf'{method}\s+["\']?([/][^"\'\s]+)["\']?'
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    path = match.group(1)
                    contracts.append({
                        'method': method.upper(),
                        'path': path,
                        'file_path': file_path,
                        'line_number': i + 1,
                        'parameters': [],
                        'return_type': None,
                        'framework': 'generic'
                    })
        
        return contracts
    
    def _combine_paths(self, base: str, path: str) -> str:
        """Combine base path and method path"""
        if not base:
            return path
        if not path:
            return base
        
        # Remove leading/trailing slashes and combine
        base = base.strip('/')
        path = path.strip('/')
        
        if base and path:
            return f'/{base}/{path}'
        elif base:
            return f'/{base}'
        elif path:
            return f'/{path}'
        else:
            return '/'
    
    def find_api_consumers(self, api_path: str, api_method: str, repository_path: str) -> List[Dict]:
        """
        Find all code files that consume a specific API endpoint
        
        Args:
            api_path: API path (e.g., '/api/payments/process')
            api_method: HTTP method (e.g., 'POST')
            repository_path: Path to repository root
        
        Returns:
            List of consumer file information
        """
        consumers = []
        
        # Search for API calls in code
        api_patterns = [
            # fetch('/api/payments/process', ...)
            rf'fetch\s*\(["\']{re.escape(api_path)}["\']',
            # axios.post('/api/payments/process', ...)
            rf'axios\.(?:get|post|put|delete|patch)\s*\(["\']{re.escape(api_path)}["\']',
            # http.get('/api/payments/process', ...)
            rf'http\.(?:get|post|put|delete|patch)\s*\(["\']{re.escape(api_path)}["\']',
            # requests.post('/api/payments/process', ...)
            rf'requests\.(?:get|post|put|delete|patch)\s*\(["\']{re.escape(api_path)}["\']',
            # RestTemplate.getForObject('/api/payments/process', ...)
            rf'RestTemplate\.(?:get|post)For(?:Object|Entity)\s*\(["\']{re.escape(api_path)}["\']',
            # @GetMapping("/api/payments/process") - Feign client
            rf'@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(["\']{re.escape(api_path)}["\']',
        ]
        
        # Search repository
        if repository_path:
            for pattern in api_patterns:
                consumers.extend(self._search_in_repository(repository_path, pattern, api_path))
        
        return consumers
    
    def _search_in_repository(self, repo_path: str, pattern: str, api_path: str) -> List[Dict]:
        """Search for pattern in repository files"""
        consumers = []
        
        try:
            from pathlib import Path
            repo = Path(repo_path)
            
            # Common code file extensions
            code_extensions = ['.js', '.jsx', '.ts', '.tsx', '.java', '.py', '.go', '.rb']
            
            for file_path in repo.rglob('*'):
                if file_path.suffix in code_extensions and file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.split('\n')
                            
                            for line_num, line in enumerate(lines, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    consumers.append({
                                        'file_path': str(file_path.relative_to(repo)),
                                        'line_number': line_num,
                                        'context': line.strip()[:100],
                                        'api_path': api_path
                                    })
                                    break  # One match per file is enough
                    except Exception:
                        continue  # Skip files that can't be read
        except Exception:
            pass
        
        return consumers
    
    def find_api_consumers_via_github_api(
        self, 
        api_path: str, 
        api_method: str, 
        repo_identifier: str,
        github_token: Optional[str] = None
    ) -> List[Dict]:
        """
        Find API consumers using GitHub Search API (no cloning required)
        
        This method searches GitHub repositories directly using the GitHub Search API,
        which is useful when cloning repositories is not feasible (e.g., hackathon demos,
        rate limits, or disk space constraints).
        
        Args:
            api_path: API path (e.g., '/api/stocks/buy')
            api_method: HTTP method (e.g., 'POST')
            repo_identifier: Repository identifier (e.g., 'owner/repo')
            github_token: Optional GitHub token for higher rate limits (5000 vs 10 requests/hour)
        
        Returns:
            List of consumer file information with file paths and GitHub URLs
        """
        consumers = []
        
        # Normalize repo identifier
        if '/' not in repo_identifier:
            return consumers
        
        owner, repo = repo_identifier.split('/', 1)
        
        # Build search query - GitHub API search format
        # Escape special characters and build queries for different patterns
        api_path_clean = api_path.strip('/')
        
        # Optimized search - use only the most effective query to reduce API calls
        # Exact path match is most reliable
        search_queries = [
            f'repo:{owner}/{repo} "{api_path}"',
        ]
        
        # Only add one additional query if we have method info (to reduce API calls)
        # if api_method:
        #     method_lower = api_method.lower()
        #     search_queries.append(
        #         f'repo:{owner}/{repo} {method_lower} "{api_path}"'
        #     )
        
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        # Search for each pattern
        seen_files = set()
        for query in search_queries:
            try:
                url = 'https://api.github.com/search/code'
                params = {'q': query}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    for item in items:
                        file_path = item.get('path', '')
                        # Filter to code files only
                        code_extensions = ['.js', '.jsx', '.ts', '.tsx', '.java', '.py', '.go', '.rb', '.php', '.cpp', '.c']
                        if any(file_path.endswith(ext) for ext in code_extensions):
                            # Avoid duplicates
                            if file_path not in seen_files:
                                seen_files.add(file_path)
                                consumers.append({
                                    'file_path': file_path,
                                    'line_number': 0,  # GitHub API doesn't provide exact line numbers
                                    'context': f"Found in {item.get('name', 'file')}",
                                    'api_path': api_path,
                                    'source': 'github_api',
                                    'html_url': item.get('html_url', ''),
                                    'repository': repo_identifier
                                })
                
                elif response.status_code == 403:
                    # Rate limit exceeded - stop all searches for this repo
                    rate_limit_info = response.headers.get('X-RateLimit-Remaining', 'unknown')
                    rate_limit_reset = response.headers.get('X-RateLimit-Reset', 'unknown')
                    print(f"   ⚠️ GitHub API rate limit exceeded for {repo_identifier} (remaining: {rate_limit_info})")
                    if not github_token:
                        print(f"   💡 Tip: Set GITHUB_TOKEN in .env for higher rate limits (5000/hour)")
                        print(f"   💡 Alternative: Set CONSUMER_SEARCH_METHOD=clone to use local cloning instead")
                    # Return early to avoid more rate limit errors
                    return consumers
                elif response.status_code == 422:
                    # Invalid query - skip this query
                    continue
                elif response.status_code == 401:
                    print(f"   ⚠️ GitHub API authentication failed for {repo_identifier}")
                    break
                    
            except requests.RequestException as e:
                print(f"   ⚠️ GitHub API search failed for {repo_identifier}: {e}")
                continue
        
        return consumers

