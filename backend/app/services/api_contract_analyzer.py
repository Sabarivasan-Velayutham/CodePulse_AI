"""
API Contract Analyzer
Analyzes API contract changes and detects breaking changes
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class APIContractChange:
    """Represents a change to an API contract"""
    
    def __init__(self, endpoint: str, method: str, change_type: str, details: Dict):
        self.endpoint = endpoint
        self.method = method
        self.change_type = change_type  # ADDED, REMOVED, MODIFIED, BREAKING
        self.details = details


class APIContractAnalyzer:
    """Analyzes API contract changes"""
    
    def __init__(self):
        pass
    
    def compare_contracts(self, before_contracts: List[Dict], after_contracts: List[Dict]) -> List[APIContractChange]:
        """
        Compare before and after API contracts to detect changes
        
        Args:
            before_contracts: List of API contracts before change
            after_contracts: List of API contracts after change
        
        Returns:
            List of detected changes
        """
        changes = []
        
        # Create lookup maps
        before_map = {(c['method'], c['path']): c for c in before_contracts}
        after_map = {(c['method'], c['path']): c for c in after_contracts}
        
        # Find removed endpoints (BREAKING)
        for key, contract in before_map.items():
            if key not in after_map:
                changes.append(APIContractChange(
                    endpoint=contract['path'],
                    method=contract['method'],
                    change_type='BREAKING',
                    details={
                        'reason': 'Endpoint removed',
                        'severity': 'CRITICAL',
                        'before': contract
                    }
                ))
        
        # Find added endpoints (NON-BREAKING)
        for key, contract in after_map.items():
            if key not in before_map:
                changes.append(APIContractChange(
                    endpoint=contract['path'],
                    method=contract['method'],
                    change_type='ADDED',
                    details={
                        'reason': 'New endpoint added',
                        'severity': 'LOW',
                        'after': contract
                    }
                ))
        
        # Find modified endpoints
        for key in before_map:
            if key in after_map:
                before = before_map[key]
                after = after_map[key]
                
                modification = self._detect_modification(before, after)
                if modification:
                    changes.append(modification)
        
        return changes
    
    def _detect_modification(self, before: Dict, after: Dict) -> Optional[APIContractChange]:
        """Detect if an endpoint was modified and if it's breaking"""
        modifications = []
        is_breaking = False
        
        # Check parameter changes
        before_params = {p['name']: p for p in before.get('parameters', [])}
        after_params = {p['name']: p for p in after.get('parameters', [])}
        
        # Removed parameters (BREAKING if required)
        for param_name, param in before_params.items():
            if param_name not in after_params:
                if param.get('required', True):
                    modifications.append(f"Required parameter '{param_name}' removed")
                    is_breaking = True
                else:
                    modifications.append(f"Optional parameter '{param_name}' removed")
        
        # Added required parameters (BREAKING)
        for param_name, param in after_params.items():
            if param_name not in before_params:
                if param.get('required', True):
                    modifications.append(f"New required parameter '{param_name}' added")
                    is_breaking = True
                else:
                    modifications.append(f"New optional parameter '{param_name}' added")
        
        # Parameter type changes (BREAKING)
        for param_name in before_params:
            if param_name in after_params:
                before_type = before_params[param_name].get('type', 'any')
                after_type = after_params[param_name].get('type', 'any')
                if before_type != after_type:
                    modifications.append(f"Parameter '{param_name}' type changed: {before_type} → {after_type}")
                    is_breaking = True
        
        # Return type changes (BREAKING)
        if before.get('return_type') != after.get('return_type'):
            if before.get('return_type') and after.get('return_type'):
                modifications.append(f"Return type changed: {before.get('return_type')} → {after.get('return_type')}")
                is_breaking = True
        
        if modifications:
            return APIContractChange(
                endpoint=before['path'],
                method=before['method'],
                change_type='BREAKING' if is_breaking else 'MODIFIED',
                details={
                    'reason': '; '.join(modifications),
                    'severity': 'CRITICAL' if is_breaking else 'MEDIUM',
                    'before': before,
                    'after': after,
                    'modifications': modifications
                }
            )
        
        return None
    
    def calculate_breaking_change_score(self, changes: List[APIContractChange], consumer_count: int) -> float:
        """
        Calculate risk score for API contract changes
        
        Args:
            changes: List of detected changes
            consumer_count: Number of API consumers
        
        Returns:
            Risk score (0-10)
        """
        score = 0.0
        
        # Base score from change types
        for change in changes:
            if change.change_type == 'BREAKING':
                score += 3.0  # High base score for breaking changes
            elif change.change_type == 'MODIFIED':
                score += 1.5
            elif change.change_type == 'ADDED':
                score += 0.5  # Low score for additions
        
        # Consumer impact multiplier
        if consumer_count > 10:
            score *= 1.5
        elif consumer_count > 5:
            score *= 1.3
        elif consumer_count > 0:
            score *= 1.1
        
        # Cap at 10
        return min(score, 10.0)

