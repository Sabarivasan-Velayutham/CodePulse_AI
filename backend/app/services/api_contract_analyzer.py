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
        
        # Track which before endpoints have been matched to path changes
        matched_before_endpoints = set()
        
        # First, check for path changes (same method, similar path)
        # This must be done before checking for removed endpoints to avoid double-counting
        for after_key, after_contract in after_map.items():
            if after_key not in before_map:
                # Check if this might be a path change
                for before_key, before_contract in before_map.items():
                    if (before_contract['method'] == after_contract['method'] and 
                        before_key not in after_map and
                        self._is_similar_path(before_contract['path'], after_contract['path'])):
                        # This is a path change (BREAKING)
                        matched_before_endpoints.add(before_key)
                        changes.append(APIContractChange(
                            endpoint=after_contract['path'],
                            method=after_contract['method'],
                            change_type='BREAKING',
                            details={
                                'reason': f"Endpoint path changed from '{before_contract['path']}' to '{after_contract['path']}'",
                                'severity': 'CRITICAL',
                                'before': before_contract,
                                'after': after_contract
                            }
                        ))
                        break
        
        # Find removed endpoints (BREAKING) - exclude those already matched as path changes
        for key, contract in before_map.items():
            if key not in after_map and key not in matched_before_endpoints:
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
        
        # Find added endpoints (truly new, not path changes)
        # Path changes were already handled above
        for key, contract in after_map.items():
            if key not in before_map:
                # Check if this was already handled as a path change
                is_path_change = False
                for before_key in before_map:
                    if (before_map[before_key]['method'] == contract['method'] and
                        before_key in matched_before_endpoints and
                        self._is_similar_path(before_map[before_key]['path'], contract['path'])):
                        is_path_change = True
                        break
                
                if not is_path_change:
                    # Truly new endpoint (NON-BREAKING)
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
    
    def _is_similar_path(self, path1: str, path2: str) -> bool:
        """
        Check if two paths are similar (likely a path change)
        Examples:
        - /api/stocks/{id}/price vs /api/stocks/{id}/current-price -> True
        - /api/stocks/{id} vs /api/stocks/{id}/price -> False (different structure)
        - /api/transactions/account/{accountId} vs /api/transactions/by-account/{accountId} -> True
        """
        # Normalize paths (remove leading/trailing slashes, convert to lowercase)
        p1 = path1.strip('/').lower()
        p2 = path2.strip('/').lower()
        
        # If paths are identical, they're not similar (they're the same)
        if p1 == p2:
            return False
        
        # Split into segments
        segments1 = p1.split('/')
        segments2 = p2.split('/')
        
        # Must have same number of segments to be a path change
        if len(segments1) != len(segments2):
            return False
        
        # Count differences
        differences = 0
        for s1, s2 in zip(segments1, segments2):
            # Normalize path variables {id} -> {id}
            s1_norm = re.sub(r'\{[^}]+\}', '{}', s1)
            s2_norm = re.sub(r'\{[^}]+\}', '{}', s2)
            
            if s1_norm != s2_norm:
                differences += 1
                # If more than one segment differs, probably not a simple path change
                if differences > 1:
                    return False
        
        # If exactly one segment differs, it's likely a path change
        return differences == 1
    
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

