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
        dependencies: Dict
    ) -> Dict:
        """
        Main AI analysis function

        Args:
            file_path: Path to changed file
            code_diff: Git diff of changes
            dependencies: Dependencies from DEPENDS

        Returns:
            AI-generated insights
        """
        print(f"🤖 Running AI analysis for {file_path}...")

        # Build comprehensive prompt
        prompt = self._build_analysis_prompt(
            file_path, code_diff, dependencies)

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
        dependencies: Dict
    ) -> str:
        """Build comprehensive analysis prompt"""

        # Extract key info
        direct_deps = dependencies.get("direct_dependencies", [])
        indirect_deps = dependencies.get("indirect_dependencies", [])

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

## ANALYSIS REQUIRED

Analyze this change and provide insights in JSON format:

{{
  "summary": "2-3 sentence summary of functional impact",
  "risks": [
    "Risk 1: Specific concern",
    "Risk 2: Another concern",
    "Risk 3: Third concern"
  ],
  "regulatory_concerns": "Any compliance/regulatory issues (SOX, Basel, PCI-DSS)",
  "affected_business_flows": [
    "Business flow 1",
    "Business flow 2"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2"
  ],
  "deployment_advice": "When/how to deploy this change"
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

Provide specific, actionable insights focused on banking domain risks.
"""
        return prompt

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

    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse AI response text to structured data"""
        try:
            # --- AI FIX: Find the JSON block more reliably ---
            # Find the start of the JSON
            start = response_text.find("{")
            if start == -1:
                raise json.JSONDecodeError("No '{' found in response", response_text, 0)

            # Find the end of the JSON
            end = response_text.rfind("}")
            if end == -1:
                raise json.JSONDecodeError("No '}' found in response", response_text, 0)
            
            json_str = response_text[start:end+1]
            
            # Clean up known bad characters from the log
            json_str = json_str.replace(r'\"', '"') # Fix escaped quotes
            json_str = json_str.replace(r"G", " ") # Fix non-breaking spaces
            
            parsed = json.loads(json_str)
            return parsed
            # --- END OF FIX ---

        except json.JSONDecodeError as e:
            print(f"❌ AI response parsing failed: {e}")
            
            # If JSON parsing fails, create structured response from text
            return {
                "summary": response_text[:200] + "...", # Truncate summary
                "risks": ["AI response parsing failed - manual review needed"],
                "regulatory_concerns": "Unable to parse",
                "affected_business_flows": [],
                "recommendations": ["Review AI response manually"],
                "deployment_advice": "Proceed with caution"
            }

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

