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
            Risk score object with breakdown
        """
        print(f"📊 Calculating risk score for {file_path}...")

        # Initialize scores
        technical_score = 0.0
        domain_score = 0.0
        ai_score = 0.0
        temporal_score = 0.0

        # 1. TECHNICAL RISK (0-4 points)
        technical_score = self._calculate_technical_risk(dependencies, metrics)

        # 2. DOMAIN RISK (0-3 points)
        domain_score = self._calculate_domain_risk(file_path, dependencies, database_dependencies)

        # 3. AI-BASED RISK (0-2 points)
        ai_score = self._calculate_ai_risk(ai_insights)

        # 4. TEMPORAL RISK (multiplier 1.0-2.0x)
        temporal_multiplier = self._calculate_temporal_risk()

        # Calculate base score
        base_score = (technical_score + domain_score +
                      ai_score) * temporal_multiplier

        # Normalize to 0-10 scale
        final_score = min(base_score, 10.0)

        # Determine risk level
        risk_level, color = self._determine_risk_level(final_score)

        result = {
            "score": round(final_score, 1),
            "level": risk_level,
            "color": color,
            "breakdown": {
                "technical": round(technical_score, 1),
                "domain": round(domain_score, 1),
                "ai_analysis": round(ai_score, 1),
                "temporal_multiplier": round(temporal_multiplier, 2)
            },
            "factors": {
                "dependency_count": len(dependencies.get("direct_dependencies", [])),
                "critical_modules": self._count_critical_modules(dependencies),
                "file_criticality": self._assess_file_criticality(file_path)
            }
        }

        print(f"✅ Risk Score: {final_score}/10 - {risk_level}")

        return result

    def _calculate_technical_risk(self, dependencies: Dict, metrics: Dict) -> float:
        """Calculate technical complexity risk (0-4 points)"""
        score = 0.0

        # Factor 1: Number of dependencies
        direct_deps = len(dependencies.get("direct_dependencies", []))
        indirect_deps = len(dependencies.get("indirect_dependencies", []))

        total_deps = direct_deps + indirect_deps

        if total_deps > 20:
            score += 2.0
        elif total_deps > 10:
            score += 1.5
        elif total_deps > 5:
            score += 1.0
        else:
            score += 0.5

        # Factor 2: Code complexity (if available)
        if metrics:
            complexity = metrics.get("cyclomatic_complexity", 1)
            if complexity > 15:
                score += 1.5
            elif complexity > 10:
                score += 1.0
            elif complexity > 5:
                score += 0.5

            # Lines changed
            lines_changed = metrics.get("lines_changed", 0)
            if lines_changed > 100:
                score += 0.5
            elif lines_changed > 50:
                score += 0.3

        return min(score, 4.0)

    def _calculate_domain_risk(self, file_path: str, dependencies: Dict, database_dependencies: Dict = None) -> float:
        """Calculate banking domain-specific risk (0-3 points)"""
        score = 0.0

        # Check if file is critical based on name
        file_name = file_path.lower()
        for pattern in self.critical_keywords:
            if pattern in file_name:
                score += 0.5
                break

        # Check affected dependencies for critical modules
        critical_count = self._count_critical_modules(dependencies)

        if critical_count >= 3:
            score += 2.0
        elif critical_count >= 2:
            score += 1.5
        elif critical_count >= 1:
            score += 1.0

        # Check for database dependencies (enhanced)
        has_db_dependency = False
        for dep in dependencies.get("direct_dependencies", []):
            if "DAO" in dep.get("target", "") or "Table" in dep.get("target", ""):
                has_db_dependency = True
                score += 0.5
                break
        
        # Additional risk if code directly uses database tables
        if database_dependencies and database_dependencies.get("tables"):
            table_count = len(database_dependencies.get("tables", []))
            if table_count > 5:
                score += 1.0  # High risk - many tables affected
            elif table_count > 2:
                score += 0.5  # Medium risk
            else:
                score += 0.3  # Low risk

        return min(score, 3.0)

    def _calculate_ai_risk(self, ai_insights: Dict) -> float:
        """Calculate risk based on AI insights (0-2 points)"""
        score = 0.0

        # Check number of risks identified
        risks = ai_insights.get("risks", [])
        risk_count = len(risks)

        if risk_count >= 4:
            score += 1.5
        elif risk_count >= 2:
            score += 1.0
        elif risk_count >= 1:
            score += 0.5

        # Check for regulatory concerns
        regulatory = ai_insights.get("regulatory_concerns", "")
        if regulatory and regulatory.lower() not in ["none", "n/a", "unable to parse"]:
            score += 0.5

        return min(score, 2.0)

    def _calculate_temporal_risk(self) -> float:
        """Calculate time-based risk multiplier (1.0-2.0x)"""
        multiplier = 1.0

        now = datetime.now()

        # Friday afternoon/evening (risky deployment time)
        if now.weekday() == 4:  # Friday
            if now.hour >= 14:  # After 2 PM
                multiplier *= 1.3

        # Month-end (high-risk period for banking)
        if now.day >= 28:
            multiplier *= 1.2

        # Quarter-end (extra high-risk)
        if now.month in [3, 6, 9, 12] and now.day >= 28:
            multiplier *= 1.5

        return min(multiplier, 2.0)

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
        if score >= 6:
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
            Risk score object
        """
        print(f"📊 Calculating schema change risk for {schema_change.table_name}...")
        
        # Initialize scores
        change_type_score = 0.0
        code_impact_score = 0.0
        db_relationship_score = 0.0
        ai_score = 0.0
        
        # 1. TABLE CRITICALITY RISK (0-3 points)
        # Base risk on table name and relationships, not exact change type
        table_name_lower = schema_change.table_name.lower()
        
        # Determine table criticality
        critical_keywords = ["transaction", "payment", "account", "balance", "fraud", "customer", "transfer"]
        is_critical_table = any(keyword in table_name_lower for keyword in critical_keywords)
        
        if is_critical_table:
            change_type_score = 2.5  # High base risk for critical tables
        else:
            change_type_score = 1.5  # Medium base risk for standard tables
        
        # Adjust based on relationships (more connections = higher risk)
        total_relationships = len(db_relationships.get("forward", [])) + len(db_relationships.get("reverse", []))
        if total_relationships > 5:
            change_type_score += 0.5  # Very interconnected = higher risk
        elif total_relationships > 2:
            change_type_score += 0.3  # Moderately interconnected
        
        change_type_score = min(change_type_score, 3.0)  # Cap at 3.0
        
        # 2. CODE IMPACT RISK (0-3 points)
        affected_files = len(code_dependencies)
        total_usages = sum(dep.get("usage_count", 1) for dep in code_dependencies)
        
        if affected_files > 10:
            code_impact_score = 3.0
        elif affected_files > 5:
            code_impact_score = 2.0
        elif affected_files > 2:
            code_impact_score = 1.5
        elif affected_files > 0:
            code_impact_score = 1.0
        
        # Additional risk if column-specific change affects many usages
        if schema_change.column_name and total_usages > 20:
            code_impact_score += 0.5
        
        code_impact_score = min(code_impact_score, 3.0)
        
        # 3. DATABASE RELATIONSHIP RISK (0-2 points)
        forward_count = len(db_relationships.get("forward", []))
        reverse_count = len(db_relationships.get("reverse", []))
        
        if reverse_count > 5:  # Many tables depend on this
            db_relationship_score = 2.0
        elif reverse_count > 2:
            db_relationship_score = 1.5
        elif reverse_count > 0:
            db_relationship_score = 1.0
        
        if forward_count > 3:  # This table depends on many others
            db_relationship_score += 0.5
        
        db_relationship_score = min(db_relationship_score, 2.0)
        
        # 4. AI-BASED RISK (0-2 points)
        ai_score = self._calculate_ai_risk(ai_insights)
        
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
            "factors": {
                "affected_code_files": affected_files,
                "total_usages": total_usages,
                "forward_relationships": forward_count,
                "reverse_relationships": reverse_count,
                "table_name": schema_change.table_name,
                "table_criticality": "CRITICAL" if is_critical_table else "STANDARD"
            }
        }
        
        print(f"✅ Schema Risk Score: {final_score}/10 - {risk_level}")
        
        return result