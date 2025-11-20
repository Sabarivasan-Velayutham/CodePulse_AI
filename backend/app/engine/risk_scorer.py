"""
Risk scoring algorithm for code changes
"""

from typing import Dict, List
from datetime import datetime


class RiskScorer:
    def __init__(self):
        # Critical banking keywords
        self.critical_keywords = [
            "payment", "transaction", "fraud", "balance",
            "account", "transfer", "regulatory", "compliance",
            "audit", "security", "authentication"
        ]

        # High-risk file patterns
        self.high_risk_patterns = [
            "Payment", "Fraud", "Transaction", "Balance",
            "Security", "Auth", "Regulatory"
        ]

    def calculate_risk(
        self,
        file_path: str,
        dependencies: Dict,
        ai_insights: Dict,
        metrics: Dict = None,
        database_dependencies: Dict = None
    ) -> Dict:
        """
        Calculate comprehensive risk score

        Returns:
            Risk score object with breakdown and explanations
        """
        print(f"📊 Calculating risk score for {file_path}...")

        # Initialize scores and explanations
        technical_result = self._calculate_technical_risk(dependencies, metrics)
        domain_result = self._calculate_domain_risk(file_path, dependencies, database_dependencies)
        ai_result = self._calculate_ai_risk(ai_insights)

        technical_score = technical_result["score"]
        domain_score = domain_result["score"]
        ai_score = ai_result["score"]

        # Calculate base score (no temporal multiplier)
        base_score = technical_score + domain_score + ai_score

        # Normalize to 0-10 scale
        final_score = min(base_score * 1.11, 10.0)  # Scale from 0-9 to 0-10

        # Determine risk level
        risk_level, color = self._determine_risk_level(final_score)

        result = {
            "score": round(final_score, 1),
            "level": risk_level,
            "color": color,
            "breakdown": {
                "technical": round(technical_score, 1),
                "domain": round(domain_score, 1),
                "ai_analysis": round(ai_score, 1)
            },
            "explanations": {
                "technical": technical_result["explanation"],
                "domain": domain_result["explanation"],
                "ai_analysis": ai_result["explanation"]
            },
            "factors": {
                "dependency_count": len(dependencies.get("direct_dependencies", [])),
                "critical_modules": self._count_critical_modules(dependencies),
                "file_criticality": self._assess_file_criticality(file_path)
            }
        }

        print(f"✅ Risk Score: {final_score}/10 - {risk_level}")

        return result


    def _calculate_technical_risk(self, dependencies: Dict, metrics: Dict) -> Dict:
        """Calculate technical complexity risk (0-4 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []

        # Factor 1: Number of dependencies
        direct_deps = len(dependencies.get("direct_dependencies", []))
        indirect_deps = len(dependencies.get("indirect_dependencies", []))
        total_deps = direct_deps + indirect_deps

        factors.append(f"Total dependencies: {total_deps} ({direct_deps} direct, {indirect_deps} indirect)")

        if total_deps > 20:
            score += 2.0
            explanations.append(f"Very high dependency count ({total_deps} total) increases complexity and risk of cascading failures")
        elif total_deps > 10:
            score += 1.5
            explanations.append(f"High dependency count ({total_deps} total) indicates significant coupling")
        elif total_deps > 5:
            score += 1.0
            explanations.append(f"Moderate dependency count ({total_deps} total) suggests moderate complexity")
        else:
            score += 0.5
            explanations.append(f"Low dependency count ({total_deps} total) indicates manageable complexity")

        # Factor 2: Code complexity (if available)
        if metrics:
            complexity = metrics.get("cyclomatic_complexity", 1)
            factors.append(f"Cyclomatic complexity: {complexity}")

            if complexity > 15:
                score += 1.5
                explanations.append(f"Very high cyclomatic complexity ({complexity}) makes code hard to test and maintain")
            elif complexity > 10:
                score += 1.0
                explanations.append(f"High cyclomatic complexity ({complexity}) increases testing difficulty")
            elif complexity > 5:
                score += 0.5
                explanations.append(f"Moderate cyclomatic complexity ({complexity}) is acceptable but should be monitored")

            # Lines changed
            lines_changed = metrics.get("lines_changed", 0)
            if lines_changed > 0:
                factors.append(f"Lines changed: {lines_changed}")
                if lines_changed > 100:
                    score += 0.5
                    explanations.append(f"Large change size ({lines_changed} lines) increases risk of introducing bugs")
                elif lines_changed > 50:
                    score += 0.3
                    explanations.append(f"Moderate change size ({lines_changed} lines) requires careful review")

        final_score = min(score, 4.0)
        
        explanation = {
            "score": final_score,
            "max_score": 4.0,
            "factors": factors,
            "details": explanations,
            "description": "Technical Risk measures code complexity, dependency count, and change size. Higher complexity increases the likelihood of bugs and makes changes harder to review."
        }

        return {"score": final_score, "explanation": explanation}

    def _calculate_domain_risk(self, file_path: str, dependencies: Dict, database_dependencies: Dict = None) -> Dict:
        """Calculate banking domain-specific risk (0-3 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []

        # Check if file is critical based on name
        file_name = file_path.lower()
        file_criticality = self._assess_file_criticality(file_path)
        factors.append(f"File criticality: {file_criticality}")

        for pattern in self.critical_keywords:
            if pattern in file_name:
                score += 0.5
                explanations.append(f"File contains critical keyword '{pattern}' - affects sensitive banking operations")
                break

        # Check affected dependencies for critical modules
        critical_count = self._count_critical_modules(dependencies)
        factors.append(f"Critical modules affected: {critical_count}")

        if critical_count >= 3:
            score += 2.0
            explanations.append(f"High number of critical modules affected ({critical_count}) - changes could impact multiple sensitive systems")
        elif critical_count >= 2:
            score += 1.5
            explanations.append(f"Multiple critical modules affected ({critical_count}) - requires careful coordination")
        elif critical_count >= 1:
            score += 1.0
            explanations.append(f"One critical module affected ({critical_count}) - moderate business impact risk")

        # Check for database dependencies (enhanced)
        has_db_dependency = False
        for dep in dependencies.get("direct_dependencies", []):
            if "DAO" in dep.get("target", "") or "Table" in dep.get("target", ""):
                has_db_dependency = True
                score += 0.5
                explanations.append("Code directly interacts with database layer - data integrity risks")
                break
        
        # Additional risk if code directly uses database tables
        if database_dependencies and database_dependencies.get("tables"):
            table_count = len(database_dependencies.get("tables", []))
            factors.append(f"Database tables accessed: {table_count}")
            if table_count > 5:
                score += 1.0
                explanations.append(f"Many database tables accessed ({table_count}) - high data consistency risk")
            elif table_count > 2:
                score += 0.5
                explanations.append(f"Multiple database tables accessed ({table_count}) - moderate data consistency risk")
            else:
                score += 0.3
                explanations.append(f"Limited database access ({table_count} table(s)) - lower data consistency risk")

        final_score = min(score, 3.0)
        
        explanation = {
            "score": final_score,
            "max_score": 3.0,
            "factors": factors,
            "details": explanations,
            "description": "Domain Risk evaluates business impact based on file criticality, affected critical modules, and database interactions. Banking systems require extra caution for financial data integrity."
        }

        return {"score": final_score, "explanation": explanation}

    def _calculate_ai_risk(self, ai_insights: Dict) -> Dict:
        """Calculate risk based on AI insights (0-2 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []

        # Check number of risks identified
        risks = ai_insights.get("risks", [])
        risk_count = len(risks)
        factors.append(f"AI-identified risks: {risk_count}")

        if risk_count >= 4:
            score += 1.5
            explanations.append(f"AI analysis identified {risk_count} significant risks - comprehensive review required")
        elif risk_count >= 2:
            score += 1.0
            explanations.append(f"AI analysis identified {risk_count} risks - careful review recommended")
        elif risk_count >= 1:
            score += 0.5
            explanations.append(f"AI analysis identified {risk_count} risk - standard review process")
        else:
            explanations.append("AI analysis found no significant risks")

        # Check for regulatory concerns
        regulatory = ai_insights.get("regulatory_concerns", "")
        if regulatory and regulatory.lower() not in ["none", "n/a", "unable to parse"]:
            score += 0.5
            factors.append("Regulatory concerns identified")
            explanations.append("AI detected potential regulatory compliance issues - legal/compliance review recommended")

        final_score = min(score, 2.0)
        
        explanation = {
            "score": final_score,
            "max_score": 2.0,
            "factors": factors,
            "details": explanations,
            "description": "AI Analysis Risk uses machine learning to identify potential issues, security concerns, and compliance risks that may not be immediately obvious from code structure alone."
        }

        return {"score": final_score, "explanation": explanation}

    def _calculate_temporal_risk(self) -> Dict:
        """Calculate time-based risk multiplier (1.0-2.0x) with explanation"""
        multiplier = 1.0
        factors = []
        explanations = []

        now = datetime.now()
        day_name = now.strftime("%A")
        factors.append(f"Time: {day_name}, {now.strftime('%B %d, %Y at %H:%M')}")

        # Friday afternoon/evening (risky deployment time)
        if now.weekday() == 4:  # Friday
            if now.hour >= 14:  # After 2 PM
                multiplier *= 1.3
                explanations.append("Friday afternoon deployment - limited time for rollback if issues occur")

        # Month-end (high-risk period for banking)
        if now.day >= 28:
            multiplier *= 1.2
            explanations.append("Month-end period - critical for financial reporting and reconciliation")

        # Quarter-end (extra high-risk)
        if now.month in [3, 6, 9, 12] and now.day >= 28:
            multiplier *= 1.5
            explanations.append("Quarter-end period - highest risk for financial systems during reporting cycles")

        if multiplier == 1.0:
            explanations.append("Standard deployment window - optimal time for changes")

        final_multiplier = min(multiplier, 2.0)
        
        explanation = {
            "multiplier": final_multiplier,
            "factors": factors,
            "details": explanations,
            "description": "Temporal Risk adjusts the overall risk score based on when the change is being deployed. Banking systems are particularly sensitive during month-end and quarter-end periods."
        }

        return {"multiplier": final_multiplier, "explanation": explanation}

    def _count_critical_modules(self, dependencies: Dict) -> int:
        """Count how many critical modules are affected"""
        critical_count = 0

        all_deps = (
            dependencies.get("direct_dependencies", []) +
            dependencies.get("indirect_dependencies", [])
        )

        for dep in all_deps:
            target = dep.get("target", "").lower()
            for keyword in self.critical_keywords:
                if keyword in target:
                    critical_count += 1
                    break

        return critical_count

    def _assess_file_criticality(self, file_path: str) -> str:
        """Assess criticality of the file being changed"""
        file_lower = file_path.lower()

        critical_patterns = ["payment", "fraud",
                             "transaction", "security", "auth"]
        high_patterns = ["account", "balance", "transfer"]

        for pattern in critical_patterns:
            if pattern in file_lower:
                return "CRITICAL"

        for pattern in high_patterns:
            if pattern in file_lower:
                return "HIGH"

        return "MEDIUM"

    def _determine_risk_level(self, score: float) -> tuple:
        """Determine risk level and color based on score"""
        if score >= 7.5:
            return ("CRITICAL", "#dc3545")  # Red
        elif score >= 5.5:
            return ("HIGH", "#fd7e14")  # Orange
        elif score >= 3.5:
            return ("MEDIUM", "#ffc107")  # Yellow
        else:
            return ("LOW", "#28a745")  # Green
    
    def calculate_schema_risk(
        self,
        schema_change,
        code_dependencies: List[Dict],
        db_relationships: Dict,
        ai_insights: Dict
    ) -> Dict:
        """
        Calculate risk score for database schema changes
        
        Args:
            schema_change: SchemaChange object
            code_dependencies: List of code files using the table
            db_relationships: Database relationships
            ai_insights: AI analysis insights
        
        Returns:
            Risk score object with explanations
        """
        print(f"📊 Calculating schema change risk for {schema_change.table_name}...")
        
        # Initialize scores
        table_criticality_result = self._calculate_table_criticality_risk(schema_change, db_relationships)
        code_impact_result = self._calculate_code_impact_risk(code_dependencies, schema_change)
        db_relationship_result = self._calculate_db_relationship_risk(db_relationships)
        ai_result = self._calculate_ai_risk(ai_insights)
        
        change_type_score = table_criticality_result["score"]
        code_impact_score = code_impact_result["score"]
        db_relationship_score = db_relationship_result["score"]
        ai_score = ai_result["score"]
        
        # Calculate base score
        base_score = change_type_score + code_impact_score + db_relationship_score + ai_score
        
        # Normalize to 0-10 scale
        final_score = min(base_score * 1.25, 10.0)  # Scale up to 10
        
        # Determine risk level
        risk_level, color = self._determine_risk_level(final_score)
        
        result = {
            "score": round(final_score, 1),
            "level": risk_level,
            "color": color,
            "breakdown": {
                "table_criticality": round(change_type_score, 1),
                "code_impact": round(code_impact_score, 1),
                "database_relationships": round(db_relationship_score, 1),
                "ai_analysis": round(ai_score, 1)
            },
            "explanations": {
                "table_criticality": table_criticality_result["explanation"],
                "code_impact": code_impact_result["explanation"],
                "database_relationships": db_relationship_result["explanation"],
                "ai_analysis": ai_result["explanation"]
            },
            "factors": {
                "affected_code_files": len(code_dependencies),
                "total_usages": sum(dep.get("usage_count", 1) for dep in code_dependencies),
                "forward_relationships": len(db_relationships.get("forward", [])),
                "reverse_relationships": len(db_relationships.get("reverse", [])),
                "table_name": schema_change.table_name,
                "table_criticality": table_criticality_result["explanation"]["factors"][0] if table_criticality_result["explanation"]["factors"] else "STANDARD"
            }
        }
        
        print(f"✅ Schema Risk Score: {final_score}/10 - {risk_level}")
        
        return result

    def _calculate_table_criticality_risk(self, schema_change, db_relationships: Dict) -> Dict:
        """Calculate table criticality risk (0-3 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []
        
        table_name_lower = schema_change.table_name.lower()
        critical_keywords = ["transaction", "payment", "account", "balance", "fraud", "customer", "transfer"]
        is_critical_table = any(keyword in table_name_lower for keyword in critical_keywords)
        
        if is_critical_table:
            score = 2.5
            factors.append(f"Table criticality: CRITICAL (contains sensitive banking data)")
            explanations.append(f"Table '{schema_change.table_name}' handles critical financial operations - schema changes require extra caution")
        else:
            score = 1.5
            factors.append(f"Table criticality: STANDARD")
            explanations.append(f"Table '{schema_change.table_name}' is a standard table - moderate risk for schema changes")
        
        # Adjust based on relationships
        total_relationships = len(db_relationships.get("forward", [])) + len(db_relationships.get("reverse", []))
        factors.append(f"Total relationships: {total_relationships}")
        
        if total_relationships > 5:
            score += 0.5
            explanations.append(f"Highly interconnected table ({total_relationships} relationships) - changes could cascade to many other tables")
        elif total_relationships > 2:
            score += 0.3
            explanations.append(f"Moderately interconnected table ({total_relationships} relationships) - some cascade risk")
        
        final_score = min(score, 3.0)
        
        explanation = {
            "score": final_score,
            "max_score": 3.0,
            "factors": factors,
            "details": explanations,
            "description": "Table Criticality Risk evaluates the importance of the table being changed and its interconnectedness. Critical tables (transactions, payments, accounts) require extra caution."
        }
        
        return {"score": final_score, "explanation": explanation}

    def _calculate_code_impact_risk(self, code_dependencies: List[Dict], schema_change) -> Dict:
        """Calculate code impact risk (0-3 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []
        
        affected_files = len(code_dependencies)
        total_usages = sum(dep.get("usage_count", 1) for dep in code_dependencies)
        
        factors.append(f"Affected code files: {affected_files}")
        factors.append(f"Total usages: {total_usages}")
        
        if affected_files > 10:
            score = 3.0
            explanations.append(f"Very high code impact - {affected_files} files affected with {total_usages} usages - extensive testing required")
        elif affected_files > 5:
            score = 2.0
            explanations.append(f"High code impact - {affected_files} files affected with {total_usages} usages - thorough testing recommended")
        elif affected_files > 2:
            score = 1.5
            explanations.append(f"Moderate code impact - {affected_files} files affected with {total_usages} usages - standard testing process")
        elif affected_files > 0:
            score = 1.0
            explanations.append(f"Low code impact - {affected_files} file(s) affected with {total_usages} usage(s) - minimal testing needed")
        else:
            explanations.append("No code files directly affected - lower risk but still requires database migration testing")
        
        # Additional risk if column-specific change affects many usages
        if schema_change.column_name and total_usages > 20:
            score += 0.5
            explanations.append(f"Column-specific change affects many usages ({total_usages}) - high risk of breaking existing queries")
        
        final_score = min(score, 3.0)
        
        explanation = {
            "score": final_score,
            "max_score": 3.0,
            "factors": factors,
            "details": explanations,
            "description": "Code Impact Risk measures how many code files and usages are affected by the schema change. More affected code means higher risk of breaking changes."
        }
        
        return {"score": final_score, "explanation": explanation}

    def _calculate_db_relationship_risk(self, db_relationships: Dict) -> Dict:
        """Calculate database relationship risk (0-2 points) with explanation"""
        score = 0.0
        factors = []
        explanations = []
        
        forward_count = len(db_relationships.get("forward", []))
        reverse_count = len(db_relationships.get("reverse", []))
        
        factors.append(f"Forward relationships: {forward_count} (tables this depends on)")
        factors.append(f"Reverse relationships: {reverse_count} (tables that depend on this)")
        
        if reverse_count > 5:
            score = 2.0
            explanations.append(f"Many tables depend on this one ({reverse_count}) - schema change could break dependent tables")
        elif reverse_count > 2:
            score = 1.5
            explanations.append(f"Several tables depend on this one ({reverse_count}) - moderate cascade risk")
        elif reverse_count > 0:
            score = 1.0
            explanations.append(f"Some tables depend on this one ({reverse_count}) - low cascade risk")
        else:
            explanations.append("No tables depend on this one - isolated change with lower risk")
        
        if forward_count > 3:
            score += 0.5
            explanations.append(f"This table depends on many others ({forward_count}) - changes could affect data integrity")
        
        final_score = min(score, 2.0)
        
        explanation = {
            "score": final_score,
            "max_score": 2.0,
            "factors": factors,
            "details": explanations,
            "description": "Database Relationship Risk evaluates how interconnected the table is. Tables with many dependencies have higher risk of cascading failures."
        }
        
        return {"score": final_score, "explanation": explanation}
