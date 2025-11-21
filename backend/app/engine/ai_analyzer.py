"""
AI-powered code analysis using Google Gemini
"""

import google.generativeai as genai
import os
import json
import re
from typing import Dict, List
from dotenv import load_dotenv 

# 1. Load variables from the .env file into os.environ
load_dotenv() 

# --- CRITICAL FIX ---
# Configure Gemini with the API key from the environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ FATAL: GEMINI_API_KEY environment variable not set.")
    # You might want to raise an Exception here to stop the app
else:
    genai.configure(api_key=api_key)
# --------------------


class AIAnalyzer:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash') 
        print("✅ Gemini AI initialized")

    async def analyze_impact(
        self,
        file_path: str,
        code_diff: str,
        dependencies: Dict,
        database_dependencies: Dict = None,
        repository_path: str = None
    ) -> Dict:
        """
        Main AI analysis function

        Args:
            file_path: Path to changed file
            code_diff: Git diff of changes
            dependencies: Dependencies from DEPENDS
            database_dependencies: Database table usage in the file
            repository_path: Path to repository root (for reading related files)

        Returns:
            AI-generated insights
        """
        print(f"🤖 Running AI analysis for {file_path}...")

        # Build comprehensive prompt
        prompt = self._build_analysis_prompt(
            file_path, code_diff, dependencies, database_dependencies, repository_path)

        try:
            import asyncio
            
            # --- AI FIX: Add safety settings to prevent blocking ---
            safety_settings = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }

            # --- FINAL FIX: Increase max_output_tokens and add timeout ---
            config = {
                'temperature': 0.2,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 8192, # Reduced from 8192 to prevent timeout
            }
            # ---------------------------------------------
            
            # Run with timeout (30 seconds)
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config=config,
                        safety_settings=safety_settings
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                print("⚠️ AI analysis timed out after 60 seconds")
                return self._fallback_analysis()

            # --- More robust check for empty/blocked content ---
            if not response.parts or not response.parts[0].text:
                block_reason = "Unknown"
                try:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                except Exception:
                    pass # Silently fail if feedback object is weird
                raise Exception(f"AI response was empty or blocked. Block reason: {block_reason}")
            
            response_text = response.parts[0].text
            # ------------------------------------

            insights = self._parse_ai_response(response_text) # <-- Use the safe variable

            print(f"✅ AI analysis complete")
            return insights

        except Exception as e:
            print(f"❌ AI analysis error: {e}")
            return self._fallback_analysis()

    def _build_analysis_prompt(
        self,
        file_path: str,
        code_diff: str,
        dependencies: Dict,
        database_dependencies: Dict = None,
        repository_path: str = None
    ) -> str:
        """Build comprehensive analysis prompt with code snippets from related files"""

        # Extract key info
        direct_deps = dependencies.get("direct_dependencies", [])
        indirect_deps = dependencies.get("indirect_dependencies", [])
        
        # Extract code snippets from related files and database usage
        related_code_section = self._extract_related_code_snippets(
            file_path, dependencies, database_dependencies, repository_path
        )

        prompt = f"""
You are an expert software architect analyzing code changes in a banking application.
## CODE CHANGE DETAILS

File: {file_path}
Type: Banking/Financial System
Criticality: HIGH (handles financial transactions)

## CHANGES MADE
{code_diff}

## DETECTED DEPENDENCIES

Direct Dependencies ({len(direct_deps)}):
{self._format_dependencies(direct_deps[:10])}  # Top 10

Indirect Dependencies ({len(indirect_deps)}):
{self._format_dependencies(indirect_deps[:5])}  # Top 5

## DATABASE DEPENDENCIES
{database_dependencies.get("tables", []) and f"Database Tables Used ({len(database_dependencies.get('tables', []))}):" or "Database Tables Used: None"}
{self._format_database_dependencies(database_dependencies) if database_dependencies else "   None"}

{related_code_section}

## ANALYSIS REQUIRED

IMPORTANT: Write in clear, professional language that is easily understandable. Include relevant technical details (method names, class names, table names, query types) where appropriate. Balance accessibility with technical depth - explain technical concepts when needed but don't oversimplify.

Analyze this change and provide insights in JSON format:

{{
  "summary": "2-3 sentence summary explaining what this change does, which components are affected, and the main business/technical impact. Include specific file names, method names, or table names when relevant.",
  "risks": [
    {{
      "risk": "Risk title/name (e.g., 'Increased False Positives and Operational Overhead')",
      "technical_context": "Technical details explaining the risk with specific code references, method names, file paths, or database operations",
      "business_impact": "Business consequences and impact on operations, customers, or revenue",
      "cascading_effects": "Potential downstream effects on other systems or processes"
    }}
  ],
  "regulatory_concerns": "Any compliance issues with technical context. Example: 'Modifications to transaction audit logging may affect SOX compliance reporting if audit trail format changes'",
  "affected_business_flows": [
    "List specific business processes with technical details. Example: 'Customer payment processing (PaymentProcessor.java, TransactionDAO.java)' or 'Account balance reconciliation (BalanceService, Account table)'"
  ],
  "recommendations": [
    "Each recommendation should correspond to a risk by index (recommendation[0] addresses risk[0], etc.). Provide actionable recommendations with technical context. Example: 'Conduct comprehensive testing of FraudDetection.java with the new thresholds. Review and update unit tests for the detectFraud() method to cover edge cases around the $10,000 threshold'",
    "Include specific files, methods, or components to check. Example: 'Verify database connection pool configuration in DataSourceConfig before deployment'",
    "Mention testing strategies, code review focus areas, or deployment considerations with technical specifics"
  ],
  "deployment_advice": "Technical deployment guidance. Example: 'Deploy during low-traffic maintenance window (2-4 AM). Ensure database migration scripts are tested in staging. Monitor PaymentProcessor metrics for first 30 minutes post-deployment'"
}}

## CONTEXT

Banking Domain Keywords to Consider:
- Payment processing: High criticality
- Fraud detection: Critical security
- Account balance: Data consistency critical
- Regulatory reporting: Compliance requirement
- Transaction data: Audit trail required

Common Banking Risks:
- Data consistency issues
- Regulatory compliance violations
- Customer impact (UI/notifications)
- Financial calculation errors
- Security vulnerabilities

IMPORTANT WRITING GUIDELINES:
- Use clear, professional language that is easily understandable
- Include relevant technical details: method names, class names, file paths, table names, query types
- Explain technical concepts when introducing them, but don't oversimplify
- Balance accessibility with technical depth - provide enough detail for developers to take action
- Reference specific code components, dependencies, and database interactions
- Include both technical impact and business consequences
- Use technical terminology appropriately (e.g., "foreign key constraint", "transaction rollback", "API endpoint")
- Provide actionable recommendations with specific files, methods, or components to review

Provide specific, actionable insights focused on banking domain risks with appropriate technical context.
Use the code snippets above to understand how this change affects related files and database operations.
"""
        return prompt
    
    def _extract_related_code_snippets(
        self,
        file_path: str,
        dependencies: Dict,
        database_dependencies: Dict = None,
        repository_path: str = None
    ) -> str:
        """
        Extract code snippets from related files (dependencies and reverse dependencies)
        to show how the changed file is used in the codebase
        
        Args:
            file_path: Path to changed file
            dependencies: Dependency information
            database_dependencies: Database table usage
            repository_path: Path to repository root
        
        Returns:
            Formatted string with code snippets from related files
        """
        if not repository_path:
            return "## RELATED CODE CONTEXT\n\n   Code snippets from related files not available (repository path not provided)."
        
        snippets = []
        max_files = 3  # Limit to top 3 related files to avoid token limits
        
        # Get reverse dependencies (files that depend on this file)
        reverse_deps = dependencies.get("reverse_direct_dependencies", [])[:max_files]
        
        if reverse_deps:
            snippets.append("## RELATED CODE CONTEXT (Files that use this changed file)")
            snippets.append("")
            
            for dep in reverse_deps:
                source_file = dep.get("source", "")
                if not source_file:
                    continue
                
                # Try to find the file
                full_path = None
                possible_paths = [
                    os.path.join(repository_path, source_file),
                    source_file,
                    os.path.join(os.getcwd(), "sample-repo", source_file),
                    os.path.join("/sample-repo", source_file),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        full_path = path
                        break
                
                if full_path:
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            file_lines = f.readlines()
                        
                        # Get line numbers where this file is used
                        line_nums = dep.get("line_numbers", [])
                        if not line_nums:
                            line_nums = [dep.get("line", 0)] if dep.get("line", 0) > 0 else []
                        
                        if line_nums:
                            line_num = line_nums[0]  # Use first line number
                            # Extract code around usage (5 lines before, 10 lines after)
                            start_line = max(0, line_num - 6)
                            end_line = min(len(file_lines), line_num + 10)
                            
                            code_context = file_lines[start_line:end_line]
                            if code_context:
                                snippets.append(f"   File: {source_file} (uses {file_path.split('/')[-1]})")
                                snippets.append(f"      Line {line_num}:")
                                snippets.append(f"      ```")
                                for i, line in enumerate(code_context):
                                    if i == min(5, len(code_context) - 1):  # Highlight usage line
                                        snippets.append(f"      >>> {line.rstrip()}")
                                    else:
                                        snippets.append(f"         {line.rstrip()}")
                                snippets.append(f"      ```")
                                snippets.append("")
                    except Exception as e:
                        # Skip if file can't be read
                        pass
        
        # Also show database usage snippets if available
        if database_dependencies and database_dependencies.get("tables"):
            snippets.append("## DATABASE USAGE IN THIS FILE")
            snippets.append("")
            
            for table_info in database_dependencies.get("tables", [])[:2]:  # Top 2 tables
                table_name = table_info["table_name"]
                usages = table_info.get("usages", [])
                
                if usages:
                    usage = usages[0]  # First usage
                    context = usage.get("context", "")
                    query_type = usage.get("query_type", "")
                    
                    if context:
                        snippets.append(f"   Table: {table_name} ({query_type})")
                        snippets.append(f"      {context[:200]}")
                        snippets.append("")
        
        if not snippets or len(snippets) <= 2:
            return "## RELATED CODE CONTEXT\n\n   Code snippets from related files not available."
        
        return "\n".join(snippets)

    def _format_dependencies(self, deps: List[Dict]) -> str:
        """Format dependencies for prompt"""
        if not deps:
            return "   None"

        formatted = []
        for dep in deps:
            formatted.append(
                f"   - {dep['source']} {dep['type']} {dep['target']}"
            )
        return "\n".join(formatted)
    
    def _format_database_dependencies(self, database_dependencies: Dict) -> str:
        """Format database dependencies for prompt"""
        if not database_dependencies or not database_dependencies.get("tables"):
            return "   None"
        
        formatted = []
        for table_info in database_dependencies.get("tables", [])[:10]:  # Top 10
            table_name = table_info["table_name"]
            usage_count = table_info["usage_count"]
            columns = table_info.get("columns", [])
            formatted.append(
                f"   - {table_name} ({usage_count} usages, columns: {', '.join(columns[:5]) if columns else 'N/A'})"
            )
        return "\n".join(formatted)

    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse AI response text to structured data"""
        try:
            # Remove markdown code blocks if present
            # Handle ```json ... ``` or ``` ... ```
            json_str = response_text.strip()
            
            # Remove markdown code block markers
            if json_str.startswith("```"):
                # Find the first newline after ```
                first_newline = json_str.find("\n")
                if first_newline != -1:
                    json_str = json_str[first_newline+1:]
            
            if json_str.endswith("```"):
                # Find the last ``` before the end
                last_marker = json_str.rfind("```")
                if last_marker != -1:
                    json_str = json_str[:last_marker]
            
            json_str = json_str.strip()
            
            # Find the start of the JSON (first {)
            start = json_str.find("{")
            if start == -1:
                raise json.JSONDecodeError("No '{' found in response", json_str, 0)

            # Find the end of the JSON (last matching })
            # Count braces to find the matching closing brace
            brace_count = 0
            end = start
            for i in range(start, len(json_str)):
                if json_str[i] == '{':
                    brace_count += 1
                elif json_str[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
            
            if brace_count != 0:
                # Fallback to rfind if brace matching fails
                end = json_str.rfind("}")
                if end == -1:
                    raise json.JSONDecodeError("No matching '}' found in response", json_str, 0)
            
            json_str = json_str[start:end+1]
            
            # Clean up known bad characters and fix encoding issues
            json_str = json_str.replace(r'\"', '"')  # Fix escaped quotes
            json_str = json_str.replace(r"G", " ")  # Fix non-breaking spaces
            # Fix "ET" -> "GET" and "GGGET" -> "GET" encoding issues (multiple G's)
            json_str = re.sub(r'\bG+ET\b', 'GET', json_str)  # GGET, GGGET, etc. -> GET
            json_str = json_str.replace(" ET ", " GET ")  # Fix "ET" -> "GET"
            json_str = json_str.replace(" ET/", " GET/")  # Fix "ET/" -> "GET/"
            json_str = json_str.replace("ET ", "GET ")  # Fix "ET " -> "GET "
            json_str = json_str.replace("\"ET ", "\"GET ")  # Fix in quotes
            json_str = json_str.replace(" ET\"", " GET\"")  # Fix in quotes
            
            parsed = json.loads(json_str)
            
            # Fix "ET" in the parsed data recursively
            parsed = self._fix_encoding_in_dict(parsed)
            
            return parsed

        except json.JSONDecodeError as e:
            print(f"❌ AI response parsing failed: {e}")
            print(f"Response text (first 500 chars): {response_text[:500]}")
            
            # If JSON parsing fails, create structured response from text
            # Try to extract summary from the text
            summary = response_text[:500] + "..." if len(response_text) > 500 else response_text
            # Remove markdown if present
            if "```" in summary:
                summary = summary.split("```")[-1].strip()
            
            return {
                "summary": summary,
                "risks": ["AI response parsing failed - manual review needed"],
                "regulatory_concerns": "Unable to parse",
                "affected_business_flows": [],
                "recommendations": ["Review AI response manually"],
                "deployment_advice": "Proceed with caution"
            }
    
    def _fix_encoding_in_dict(self, obj):
        """Recursively fix encoding issues in parsed JSON"""
        if isinstance(obj, dict):
            return {k: self._fix_encoding_in_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._fix_encoding_in_dict(item) for item in obj]
        elif isinstance(obj, str):
            # Fix "ET" -> "GET" in strings
            return obj.replace(" ET ", " GET ").replace(" ET/", " GET/").replace("ET ", "GET ")
        else:
            return obj

    def _fallback_analysis(self) -> Dict:
        """Fallback analysis if AI fails"""
        return {
            "summary": "AI analysis unavailable. Manual review recommended.",
            "risks": [
                "Unable to perform automated impact analysis",
                "Proceed with manual code review",
                "Verify all dependencies manually"
            ],
            "regulatory_concerns": "Manual compliance review required",
            "affected_business_flows": [],
            "recommendations": [
                "Conduct manual impact analysis",
                "Involve senior architect",
                "Extended testing recommended"
            ],
            "deployment_advice": "Hold deployment until manual review complete"
        }

    async def generate_test_scenarios(
        self,
        method_code: str,
        method_name: str
    ) -> List[Dict]:
        """Generate test scenarios for a method"""

        prompt = f"""
Generate test scenarios for this banking application method:

Method: {method_name}
Code:
```java
{method_code}
```

Generate 5-8 test scenarios covering:
1. Happy path
2. Edge cases
3. Error conditions
4. Boundary values
5. Banking-specific scenarios

Return as JSON array:
[
  {{
    "name": "test_happyPath",
    "description": "Tests normal successful flow",
    "test_data": {{"amount": 1000, "type": "DOMESTIC"}},
    "expected": "success",
    "priority": "P0"
  }}
]
"""

        try:
            # Removed the unsupported 'response_mime_type' here as well
            response = self.model.generate_content(prompt)
            scenarios = self._parse_ai_response(response.text)

            if isinstance(scenarios, list):
                return scenarios
            else:
                return []
        except:
            return []
    
    async def analyze_schema_impact(
        self,
        schema_change,
        code_dependencies: List[Dict],
        db_relationships: Dict,
        repository_path: str = None
    ) -> Dict:
        """
        Analyze impact of database schema change
        
        Args:
            schema_change: SchemaChange object
            code_dependencies: List of code files that use the table
            db_relationships: Database relationships (foreign keys, etc.)
            repository_path: Path to repository root (for reading code files)
        
        Returns:
            AI-generated insights for schema change
        """
        print(f"🤖 Running AI analysis for schema change: {schema_change.table_name}")
        
        prompt = self._build_schema_analysis_prompt(
            schema_change, code_dependencies, db_relationships, repository_path
        )
        
        try:
            import asyncio
            
            safety_settings = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
            
            config = {
                'temperature': 0.2,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config=config,
                        safety_settings=safety_settings
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                print("⚠️ AI schema analysis timed out after 60 seconds")
                return self._fallback_schema_analysis()
            
            if not response.parts or not response.parts[0].text:
                return self._fallback_schema_analysis()
            
            response_text = response.parts[0].text
            insights = self._parse_ai_response(response_text)
            
            print(f"✅ AI schema analysis complete")
            return insights
            
        except Exception as e:
            print(f"❌ AI schema analysis error: {e}")
            return self._fallback_schema_analysis()
    
    def _build_schema_analysis_prompt(
        self,
        schema_change,
        code_dependencies: List[Dict],
        db_relationships: Dict,
        repository_path: str = None
    ) -> str:
        """Build prompt for schema change analysis - includes actual code snippets"""
        
        affected_files = [dep["file_path"] for dep in code_dependencies]
        forward_tables = [rel.get("target_table") or rel.get("table_name") for rel in db_relationships.get("forward", [])]
        reverse_tables = [rel.get("source_table") or rel.get("table_name") for rel in db_relationships.get("reverse", [])]
        
        # Build relationship details
        relationship_details = []
        for rel in db_relationships.get("forward", [])[:5]:
            rel_type = rel.get("type", "RELATIONSHIP")
            target = rel.get("target_table") or rel.get("table_name", "unknown")
            relationship_details.append(f"   - {rel_type}: References {target}")
        
        for rel in db_relationships.get("reverse", [])[:5]:
            rel_type = rel.get("type", "RELATIONSHIP")
            source = rel.get("source_table") or rel.get("table_name", "unknown")
            relationship_details.append(f"   - {rel_type}: Referenced by {source}")
        
        # Determine table criticality based on name and relationships
        table_name_lower = schema_change.table_name.lower()
        is_critical = any(keyword in table_name_lower for keyword in [
            "transaction", "payment", "account", "balance", "fraud", "customer", "transfer"
        ])
        
        # Calculate counts for prompt
        affected_file_count = len(affected_files)
        reverse_table_count = len(reverse_tables)
        total_relationships = len(forward_tables) + len(reverse_tables)
        
        # Extract code snippets from affected files
        code_snippets_section = self._extract_code_snippets(
            code_dependencies, 
            schema_change.table_name,
            schema_change.column_name,
            repository_path
        )
        
        prompt = f"""
You are an expert database architect analyzing schema changes in a banking application.

## SCHEMA CHANGE CONTEXT

Table: {schema_change.table_name}
Table Criticality: {"CRITICAL" if is_critical else "STANDARD"} (based on banking domain keywords)
Column: {schema_change.column_name or "Not specified - table-level change"}
SQL Statement: {schema_change.sql_statement or "Not available - detected via database trigger"}

## IMPACT ANALYSIS

Affected Code Files ({affected_file_count}):
{chr(10).join(f"   - {f} ({code_dependencies[i].get('usage_count', 1)} usages)" for i, f in enumerate(affected_files[:10])) if affected_files else "   None detected"}

Database Relationships ({total_relationships} total):
{chr(10).join(relationship_details) if relationship_details else "   No explicit relationships detected"}

Forward Relationships (tables this table references): {len(forward_tables)}
{chr(10).join(f"   - {t}" for t in forward_tables[:5]) if forward_tables else "   None"}

Reverse Relationships (tables that reference this): {reverse_table_count}
{chr(10).join(f"   - {t}" for t in reverse_tables[:5]) if reverse_tables else "   None"}

{code_snippets_section}

## ANALYSIS REQUIRED

IMPORTANT: You may not know the exact change type (ADD/DROP/MODIFY). Focus on:
1. **Impact Analysis**: Based on code dependencies and database relationships
2. **Risk Assessment**: Based on table criticality and connection complexity
3. **Dependency Impact**: How changes to this table affect connected systems
4. **Banking Domain Risks**: Financial data integrity, compliance, audit trails

IMPORTANT: Write in clear, professional language that is easily understandable. Include relevant technical details (table names, column names, file paths, query types, relationship types) where appropriate. Balance accessibility with technical depth.

Analyze this schema change and provide insights in JSON format:

{{
  "summary": "2-3 sentence summary explaining the schema change impact, which code files are affected, and potential technical/business consequences. Include specific table names, column names, and affected file paths when relevant.",
  "risks": [
    {{
      "risk": "Risk title/name (e.g., 'Breaking Changes to Application Code')",
      "technical_context": "Technical details with specific code references, file paths, query types, or database operations. Example: 'Schema change to TRANSACTIONS table may break SELECT queries in TransactionDAO.java (lines 45-67) that reference the modified column'",
      "business_impact": "Business consequences and impact. Example: 'Foreign key constraint changes could cause cascading deletes affecting BALANCE_HISTORY table, potentially impacting account reconciliation processes'",
      "cascading_effects": "Potential downstream effects on other systems, tables, or processes"
    }}
  ],
  "regulatory_concerns": "Compliance issues with technical context. Example: 'Removing audit_timestamp column from TRANSACTIONS table may violate SOX compliance requirements for transaction audit trails'",
  "recommendations": [
    "Each recommendation should correspond to a risk by index (recommendation[0] addresses risk[0], etc.). Provide actionable recommendations with technical specifics. Example: 'Review and update all SQL queries in TransactionDAO.java, PaymentProcessor.java that reference the modified column. Update ORM mappings if using JPA/Hibernate'",
    "Include specific files, methods, or database operations to check. Example: 'Verify foreign key constraints in related tables (BALANCE_HISTORY, PAYMENT_LOG) before deployment'",
    "Mention testing strategies, migration scripts, or rollback procedures with technical details"
  ],
  "deployment_advice": "Technical deployment guidance. Example: 'Deploy during maintenance window. Execute database migration script in staging first. Update application code in TransactionDAO.java before schema change. Monitor query performance on TRANSACTIONS table post-deployment'",
  "data_migration_required": "Yes/No with technical explanation. Example: 'Yes - Column type change from VARCHAR to DECIMAL requires data migration script to convert existing string values to numeric format'",
  "backward_compatibility": "Technical explanation with specifics. Example: 'No - Old code expecting VARCHAR column will fail. All {affected_file_count} affected files must be updated before deployment'"
}}

## BANKING CONTEXT

Critical Considerations:
- Data integrity: Schema changes can break financial calculations
- Audit trails: Column changes may affect compliance reporting
- Transaction processing: Changes during business hours are risky
- Data migration: May require downtime
- Foreign key constraints: Can cascade to related tables
- Index changes: May affect query performance

Common Schema Change Risks:
- Breaking application code that expects old schema
- Data loss during column drops
- Performance degradation from index changes
- Compliance violations from missing audit columns
- Transaction failures from constraint violations

IMPORTANT WRITING GUIDELINES:
- Use clear, professional language that is easily understandable
- Include relevant technical details: table names, column names, file paths, query types, relationship types, method names
- Explain technical concepts when introducing them, but don't oversimplify
- Balance accessibility with technical depth - provide enough detail for developers and DBAs to take action
- Reference specific code files, database tables, foreign keys, indexes, and query patterns
- Include both technical impact (e.g., "SELECT queries will fail", "foreign key constraint violations") and business consequences
- Use appropriate technical terminology (e.g., "foreign key constraint", "index performance", "query execution plan", "ORM mapping")
- Provide actionable recommendations with specific files, methods, tables, or SQL operations to review

Provide specific, actionable insights focused on database schema change risks in banking domain with appropriate technical context.
Use the actual code snippets above to identify specific risks and provide code-aware recommendations with technical details.
"""
        return prompt
    
    def _extract_code_snippets(
        self,
        code_dependencies: List[Dict],
        table_name: str,
        column_name: str = None,
        repository_path: str = None
    ) -> str:
        """
        Extract code snippets from affected files showing how the table/collection is used
        
        Args:
            code_dependencies: List of code dependency dictionaries
            table_name: Table/collection name
            column_name: Optional column/field name
            repository_path: Path to repository root
        
        Returns:
            Formatted string with code snippets
        """
        if not code_dependencies or not repository_path:
            return "## CODE SNIPPETS\n\n   Code snippets not available (repository path not provided)."
        
        snippets = []
        max_files = 5  # Limit to top 5 files to avoid token limits
        max_snippets_per_file = 2  # Limit snippets per file
        
        for dep in code_dependencies[:max_files]:
            file_path = dep.get("file_path", "")
            usages = dep.get("usages", [])
            
            if not file_path or not usages:
                continue
            
            # Try to read the actual file
            full_path = None
            possible_paths = [
                os.path.join(repository_path, file_path),
                file_path,  # Already absolute
                os.path.join(os.getcwd(), "sample-repo", file_path),
                os.path.join("/sample-repo", file_path),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    full_path = path
                    break
            
            if not full_path:
                # File not found, use context from usages
                file_snippets = []
                for usage in usages[:max_snippets_per_file]:
                    context = usage.get("context", "")
                    line_num = usage.get("line_number", 0)
                    query_type = usage.get("query_type", "")
                    
                    if context:
                        file_snippets.append(f"      Line {line_num} ({query_type}): {context[:150]}")
                
                if file_snippets:
                    snippets.append(f"   File: {file_path}")
                    snippets.extend(file_snippets)
                continue
            
            # Read file and extract code around usage lines
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_lines = f.readlines()
                
                file_snippets = []
                processed_lines = set()  # Avoid duplicate snippets for same line
                
                for usage in usages[:max_snippets_per_file]:
                    line_num = usage.get("line_number", 0)
                    query_type = usage.get("query_type", "")
                    
                    if line_num <= 0 or line_num in processed_lines:
                        continue
                    
                    processed_lines.add(line_num)
                    
                    # Extract code around the usage line (5 lines before, 10 lines after)
                    start_line = max(0, line_num - 6)  # 0-indexed, so -6 for 5 lines before
                    end_line = min(len(file_lines), line_num + 10)  # 10 lines after
                    
                    code_context = file_lines[start_line:end_line]
                    code_snippet = "".join(code_context).strip()
                    
                    if code_snippet:
                        # Highlight the line where table is used
                        snippet_lines = code_snippet.split('\n')
                        if len(snippet_lines) > 0:
                            # Find the actual usage line in the snippet
                            usage_line_idx = min(5, len(snippet_lines) - 1)  # Usually around line 5-6
                            
                            file_snippets.append(f"      Line {line_num} ({query_type}):")
                            file_snippets.append(f"      ```")
                            for i, line in enumerate(snippet_lines):
                                # Mark the usage line
                                if i == usage_line_idx:
                                    file_snippets.append(f"      >>> {line.rstrip()}")
                                else:
                                    file_snippets.append(f"         {line.rstrip()}")
                            file_snippets.append(f"      ```")
                
                if file_snippets:
                    snippets.append(f"   File: {file_path}")
                    snippets.extend(file_snippets)
                    snippets.append("")  # Empty line between files
                    
            except Exception as e:
                # If file read fails, use context from usage
                context = usages[0].get("context", "") if usages else ""
                if context:
                    snippets.append(f"   File: {file_path}")
                    snippets.append(f"      Context: {context[:200]}")
                    snippets.append("")
        
        if not snippets:
            return "## CODE SNIPPETS\n\n   Code snippets not available (files could not be read)."
        
        return "## CODE SNIPPETS (How the table/collection is used in code)\n\n" + "\n".join(snippets)
    
    def _fallback_schema_analysis(self) -> Dict:
        """Fallback analysis for schema changes"""
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
            "deployment_advice": "Deploy during maintenance window",
            "data_migration_required": True,
            "backward_compatibility": "Unknown - requires manual review"
        }
    
    async def analyze_api_contract_impact(
        self,
        file_path: str,
        code_diff: str,
        api_changes: List,
        consumers: Dict,
        repository_path: str = None
    ) -> Dict:
        """
        Analyze impact of API contract changes
        
        Args:
            file_path: Path to changed file
            code_diff: Git diff showing changes
            api_changes: List of API contract changes
            consumers: Dictionary mapping API endpoints to consumer files
            repository_path: Path to repository root
        
        Returns:
            AI-generated insights for API contract changes
        """
        print(f"🤖 Running AI analysis for API contract changes in {file_path}...")
        
        prompt = self._build_api_contract_analysis_prompt(
            file_path, code_diff, api_changes, consumers, repository_path
        )
        
        try:
            import asyncio
            
            safety_settings = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
            }
            
            config = {
                'temperature': 0.2,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config=config,
                        safety_settings=safety_settings
                    ),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                print("⚠️ AI API contract analysis timed out after 60 seconds")
                return self._fallback_api_contract_analysis(api_changes, consumers)
            
            if not response.parts or not response.parts[0].text:
                return self._fallback_api_contract_analysis(api_changes, consumers)
            
            response_text = response.parts[0].text
            insights = self._parse_ai_response(response_text)
            
            print(f"✅ AI API contract analysis complete")
            return insights
            
        except Exception as e:
            print(f"❌ AI API contract analysis error: {e}")
            return self._fallback_api_contract_analysis(api_changes, consumers)
    
    def _build_api_contract_analysis_prompt(
        self,
        file_path: str,
        code_diff: str,
        api_changes: List,
        consumers: Dict,
        repository_path: str = None
    ) -> str:
        """Build prompt for API contract change analysis"""
        
        breaking_changes = [c for c in api_changes if hasattr(c, 'change_type') and c.change_type == 'BREAKING']
        total_consumers = sum(len(cons) for cons in consumers.values())
        
        # Format API changes
        changes_text = []
        for change in api_changes:
            if hasattr(change, 'endpoint'):
                changes_text.append(f"   - {change.method} {change.endpoint}: {change.change_type}")
                if hasattr(change, 'details'):
                    changes_text.append(f"     Reason: {change.details.get('reason', 'N/A')}")
        
        # Format consumers
        consumers_text = []
        for api_key, consumer_list in list(consumers.items())[:10]:  # Top 10
            consumers_text.append(f"   - {api_key}: {len(consumer_list)} consumers")
            for consumer in consumer_list[:3]:  # Top 3 per API
                consumers_text.append(f"     • {consumer.get('file_path', 'unknown')} (line {consumer.get('line_number', 0)})")
        
        prompt = f"""
You are an expert API architect analyzing API contract changes in a microservices banking application.

## API CONTRACT CHANGE DETAILS

File: {file_path}
Type: API Endpoint Definition
Criticality: HIGH (API changes affect multiple services)

## CODE CHANGES MADE
{code_diff}

## DETECTED API CONTRACT CHANGES

Total Changes: {len(api_changes)}
Breaking Changes: {len(breaking_changes)}

Changes:
{chr(10).join(changes_text) if changes_text else "   None detected"}

## API CONSUMERS AFFECTED

Total Consumers: {total_consumers}

Consumer Details:
{chr(10).join(consumers_text) if consumers_text else "   No consumers found"}

## ANALYSIS REQUIRED

IMPORTANT: Write in clear, professional language that is easily understandable. Include relevant technical details (endpoint paths, HTTP methods, parameter names, consumer file paths) where appropriate. Balance accessibility with technical depth.

Analyze these API contract changes and provide insights in JSON format:

{{
  "summary": "2-3 sentence summary explaining the API contract changes, which consumers are affected, and potential impact. Include specific endpoint paths, HTTP methods, and consumer file names when relevant.",
  "risks": [
    {{
      "risk": "Risk title/name (e.g., 'Breaking Change: Required Parameter Added')",
      "technical_context": "Technical details with specific endpoint paths, HTTP methods, parameter names, or consumer file paths. Example: 'POST /api/payments/process now requires cardNumber parameter. Frontend/src/payment/PaymentForm.jsx (line 45) does not send this parameter and will fail'",
      "business_impact": "Business consequences and impact. Example: 'Payment processing will fail for all users, causing transaction failures and customer complaints'",
      "cascading_effects": "Potential downstream effects on other systems or processes"
    }}
  ],
  "regulatory_concerns": "Compliance issues with technical context. Example: 'API changes affecting payment endpoints may require PCI-DSS compliance review if authentication mechanisms are modified'",
  "recommendations": [
    "Each recommendation should correspond to a risk by index (recommendation[0] addresses risk[0], etc.). Provide actionable recommendations with technical specifics. Example: 'Make cardNumber parameter optional initially, then deprecate old version. Update Frontend/src/payment/PaymentForm.jsx to include cardNumber field'",
    "Include specific files, endpoints, or API consumers to update. Example: 'Coordinate with frontend team to update PaymentForm.jsx, mobile app team to update PaymentService.swift before deploying API change'",
    "Mention API versioning strategies, migration plans, or deployment considerations with technical details"
  ],
  "deployment_advice": "Technical deployment guidance. Example: 'Deploy during maintenance window. Use API versioning (v1, v2) to maintain backward compatibility. Update all {total_consumers} consumers before removing old API version. Monitor API error rates for first hour post-deployment'",
  "migration_strategy": "Technical migration strategy. Example: 'Phase 1: Deploy new API version (v2) alongside v1. Phase 2: Update all consumers to use v2. Phase 3: Deprecate v1 after 30 days. Phase 4: Remove v1'"
}}

## MICROSERVICES CONTEXT

Critical Considerations:
- API breaking changes affect multiple services simultaneously
- Frontend, mobile apps, and other microservices depend on API contracts
- API versioning is essential for backward compatibility
- Consumer coordination is critical before breaking changes

Common API Change Risks:
- Breaking changes cause immediate failures in consumer services
- Missing required parameters cause validation errors
- Response structure changes break consumer parsing logic
- Endpoint removal causes 404 errors
- Authentication changes break all consumers

IMPORTANT WRITING GUIDELINES:
- Use clear, professional language that is easily understandable
- Include relevant technical details: endpoint paths, HTTP methods, parameter names, consumer file paths, line numbers
- Explain technical concepts when introducing them, but don't oversimplify
- Balance accessibility with technical depth - provide enough detail for developers to take action
- Reference specific API endpoints, consumer files, and migration strategies
- Include both technical impact (e.g., "API calls will fail", "validation errors") and business consequences
- Use appropriate technical terminology (e.g., "API versioning", "backward compatibility", "consumer coordination")
- Provide actionable recommendations with specific files, endpoints, or services to update

Provide specific, actionable insights focused on API contract change risks in microservices architecture with appropriate technical context.
"""
        return prompt
    
    def _fallback_api_contract_analysis(self, api_changes: List, consumers: Dict) -> Dict:
        """Fallback analysis for API contract changes"""
        breaking_count = len([c for c in api_changes if hasattr(c, 'change_type') and c.change_type == 'BREAKING'])
        total_consumers = sum(len(cons) for cons in consumers.values())
        
        return {
            "summary": f"Detected {len(api_changes)} API contract changes ({breaking_count} breaking). {total_consumers} consumers may be affected.",
            "risks": [
                {
                    "risk": "Breaking API Changes Detected",
                    "technical_context": f"{breaking_count} breaking changes will cause API consumers to fail",
                    "business_impact": f"{total_consumers} consumers will be affected, potentially causing service outages",
                    "cascading_effects": "Service failures may cascade to dependent systems"
                }
            ] if breaking_count > 0 else [],
            "regulatory_concerns": "API changes may affect service level agreements and customer experience",
            "recommendations": [
                "Review all breaking changes before deployment",
                f"Update all {total_consumers} API consumers before deploying changes",
                "Consider API versioning for backward compatibility",
                "Coordinate with frontend, mobile, and microservices teams"
            ] if breaking_count > 0 else [
                "Changes are non-breaking - safe to deploy"
            ],
            "deployment_advice": "Coordinate consumer updates before deploying breaking changes",
            "migration_strategy": "Use API versioning to maintain backward compatibility during migration"
        }

