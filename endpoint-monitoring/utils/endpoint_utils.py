#!/usr/bin/env python3
"""
Endpoint Utils - READ-ONLY hulpfuncties voor endpoint analysis

Wat doet het: Biedt safe utility functies voor endpoint monitoring
Voor wie: De endpoint monitoring suite
Gebruikt door: run_endpoint_check.py voor analysis taken
Waarom: Herbruikbare functies voor endpoint health checks
Safety: Alle functies zijn READ-ONLY - wijzigen niets aan je code
"""

import re
import json
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime, timedelta

class EndpointAnalyzer:
    """READ-ONLY endpoint analysis utilities"""
    
    @staticmethod
    def normalize_endpoint_path(path: str) -> str:
        """
        Normalize endpoint path for comparison
        Example: /api/jobs/{job_id} -> /api/jobs/{id}
        """
        # Replace all path parameters with generic {id}
        normalized = re.sub(r'\{[^}]+\}', '{id}', path)
        
        # Remove trailing slashes
        normalized = normalized.rstrip('/')
        
        # Remove version prefixes for comparison
        normalized = re.sub(r'^/v\d+', '', normalized)
        
        return normalized
    
    @staticmethod
    def detect_similar_endpoints(endpoints: List[Dict]) -> List[Dict]:
        """
        Detect endpoints that might be duplicates based on path similarity
        Returns list of potential duplicate groups
        """
        groups = {}
        
        for endpoint in endpoints:
            # Create a signature for grouping
            normalized_path = EndpointAnalyzer.normalize_endpoint_path(endpoint['path'])
            method = endpoint.get('method', 'GET')
            
            # Group by normalized path
            if normalized_path not in groups:
                groups[normalized_path] = []
            
            groups[normalized_path].append({
                'original': endpoint,
                'method': method,
                'signature': f"{method}:{normalized_path}"
            })
        
        # Find groups with multiple methods (potential duplicates)
        duplicates = []
        for path, group in groups.items():
            if len(group) > 1:
                # Check if different methods on same resource
                methods = [item['method'] for item in group]
                if len(set(methods)) > 1:
                    duplicates.append({
                        'path': path,
                        'endpoints': group,
                        'concern': 'Multiple methods on same resource',
                        'severity': 'INFO'
                    })
                else:
                    # Same method, different actual paths - potential real duplicate
                    duplicates.append({
                        'path': path,
                        'endpoints': group,
                        'concern': 'Potential duplicate endpoints',
                        'severity': 'WARNING'
                    })
        
        return duplicates
    
    @staticmethod
    def analyze_endpoint_naming_patterns(endpoints: List[Dict]) -> Dict[str, Any]:
        """
        Analyze naming patterns in endpoints for consistency (READ-ONLY)
        """
        patterns = {
            'rest_compliant': 0,
            'non_rest': 0,
            'action_based': 0,
            'resource_based': 0,
            'inconsistent_naming': []
        }
        
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET')
            
            # Check REST compliance
            if EndpointAnalyzer._is_rest_compliant(path, method):
                patterns['rest_compliant'] += 1
            else:
                patterns['non_rest'] += 1
            
            # Check if action-based vs resource-based
            if '/action' in path or re.search(r'/\w+(?:_\w+)+(?:/|$)', path):
                patterns['action_based'] += 1
            else:
                patterns['resource_based'] += 1
            
            # Check naming consistency
            if EndpointAnalyzer._has_inconsistent_naming(path):
                patterns['inconsistent_naming'].append(path)
        
        return patterns
    
    @staticmethod
    def _is_rest_compliant(path: str, method: str) -> bool:
        """Check if endpoint follows REST conventions"""
        # Basic REST pattern: /resource or /resource/{id} or /resource/{id}/subresource
        rest_pattern = r'^/\w+(/\{[^}]+\})?(/\w+)?(/\{[^}]+\})?$'
        
        # Allow for API versioning
        versioned_pattern = r'^/v\d+' + rest_pattern[1:]
        
        return bool(re.match(rest_pattern, path) or re.match(versioned_pattern, path))
    
    @staticmethod
    def _has_inconsistent_naming(path: str) -> bool:
        """Check for inconsistent naming patterns"""
        # Look for mixed naming conventions
        segments = [seg for seg in path.split('/') if seg and not seg.startswith('{')]
        
        has_underscore = any('_' in seg for seg in segments)
        has_hyphen = any('-' in seg for seg in segments)
        has_camelcase = any(re.search(r'[a-z][A-Z]', seg) for seg in segments)
        
        # Inconsistent if mixing conventions
        convention_count = sum([has_underscore, has_hyphen, has_camelcase])
        return convention_count > 1
    
    @staticmethod
    def calculate_endpoint_complexity_score(endpoints: List[Dict]) -> Dict[str, Any]:
        """
        Calculate complexity score for endpoint architecture (READ-ONLY)
        """
        total_endpoints = len(endpoints)
        
        if total_endpoints == 0:
            return {'score': 0, 'rating': 'N/A', 'factors': {}}
        
        # Factors that contribute to complexity
        factors = {
            'total_count': min(total_endpoints / 50.0, 2.0),  # Max 2 points for count
            'deep_nesting': 0,
            'parameter_density': 0,
            'method_distribution': 0
        }
        
        # Analyze nesting depth
        max_depth = 0
        param_count = 0
        method_counts = {}
        
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET')
            
            # Count nesting depth
            depth = len([seg for seg in path.split('/') if seg and not seg.startswith('{')])
            max_depth = max(max_depth, depth)
            
            # Count parameters
            param_count += len(re.findall(r'\{[^}]+\}', path))
            
            # Count methods
            method_counts[method] = method_counts.get(method, 0) + 1
        
        # Calculate factor scores
        factors['deep_nesting'] = min(max_depth / 5.0, 1.0)  # Max 1 point
        factors['parameter_density'] = min(param_count / total_endpoints / 2.0, 1.0)  # Max 1 point
        
        # Method distribution (more balanced = less complex)
        method_values = list(method_counts.values())
        if method_values:
            method_variance = sum((x - sum(method_values)/len(method_values))**2 for x in method_values) / len(method_values)
            factors['method_distribution'] = min(method_variance / 100.0, 1.0)  # Max 1 point
        
        # Total complexity score (0-5)
        total_score = sum(factors.values())
        
        # Rating
        if total_score < 1.5:
            rating = '🟢 SIMPLE'
        elif total_score < 2.5:
            rating = '🟡 MODERATE'
        elif total_score < 3.5:
            rating = '🟠 COMPLEX'
        else:
            rating = '🔴 VERY COMPLEX'
        
        return {
            'score': round(total_score, 2),
            'rating': rating,
            'factors': factors,
            'details': {
                'max_nesting_depth': max_depth,
                'avg_parameters_per_endpoint': round(param_count / total_endpoints, 2) if total_endpoints > 0 else 0,
                'method_distribution': method_counts
            }
        }
    
    @staticmethod
    def read_governance_files(governance_paths: List[Path]) -> Dict[str, str]:
        """
        Read governance documentation files (READ-ONLY)
        Returns dict with filename -> content
        """
        governance_content = {}
        
        for path in governance_paths:
            if path.exists() and path.is_file():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        governance_content[path.name] = f.read()
                except Exception as e:
                    governance_content[path.name] = f"Error reading file: {e}"
            else:
                governance_content[path.name] = "File not found"
        
        return governance_content
    
    @staticmethod
    def extract_governance_rules(governance_content: str) -> List[str]:
        """
        Extract rules from governance documentation (READ-ONLY parsing)
        """
        rules = []
        
        # Look for numbered rules, bullet points, or checkboxes
        rule_patterns = [
            r'^\d+\.\s+(.+)$',  # 1. Rule text
            r'^\*\s+(.+)$',     # * Rule text
            r'^-\s+(.+)$',      # - Rule text
            r'^\s*✅\s+(.+)$',  # ✅ Rule text
            r'^\s*❌\s+(.+)$',  # ❌ Rule text
        ]
        
        lines = governance_content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in rule_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    rule_text = match.group(1).strip()
                    if len(rule_text) > 10:  # Filter out short/meaningless matches
                        rules.append(rule_text)
                    break
        
        return rules[:20]  # Limit to top 20 rules to avoid spam
    
    @staticmethod
    def scan_api_logs_for_warnings(log_path: str = "../logs/api.log") -> Dict[str, List[str]]:
        """
        🔍 KOK WAARSCHUWINGEN - Scan API logs voor FastAPI duplicate Operation ID warnings
        
        Returns: Dict met warning types en details
        """
        warnings = {
            "duplicate_operation_ids": [],
            "404_errors": [],
            "route_conflicts": []
        }
        
        try:
            if not Path(log_path).exists():
                return warnings
            
            # Lees de laatste 1000 regels voor recente issues
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
            for line in recent_lines:
                # Detecteer FastAPI Operation ID duplicaten
                if "Duplicate Operation ID" in line:
                    # Extract operation name from warning
                    match = re.search(r'Duplicate Operation ID (\w+)', line)
                    if match:
                        operation_name = match.group(1)
                        warnings["duplicate_operation_ids"].append({
                            "operation": operation_name,
                            "line": line.strip(),
                            "issue": "🍳 Kok is verward: dubbel recept gevonden"
                        })
                
                # Detecteer 404 endpoints
                elif "404 Not Found" in line:
                    # Extract endpoint path
                    match = re.search(r'"[A-Z]+ ([^"]+) HTTP/', line)
                    if match:
                        endpoint_path = match.group(1)
                        warnings["404_errors"].append({
                            "path": endpoint_path,
                            "line": line.strip(),
                            "issue": "🚫 Klant bestelt iets dat niet bestaat"
                        })
                
                # Detecteer mogelijke route conflicten
                elif "routing" in line.lower() and ("error" in line.lower() or "warning" in line.lower()):
                    warnings["route_conflicts"].append({
                        "line": line.strip(),
                        "issue": "⚠️ Route problemen gedetecteerd"
                    })
                        
        except Exception as e:
            # Als we de logs niet kunnen lezen, geen probleem
            pass
            
        return warnings

class SafeFileReader:
    """Ultra-safe file reading utilities - READ-ONLY guaranteed"""
    
    @staticmethod
    def safe_read_json(filepath: Path) -> Optional[Dict]:
        """Safely read JSON file without any write operations"""
        try:
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    @staticmethod
    def safe_read_text(filepath: Path) -> Optional[str]:
        """Safely read text file without any write operations"""
        try:
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    @staticmethod
    def check_file_exists(filepath: Path) -> bool:
        """Check if file exists without any modifications"""
        try:
            return filepath.exists() and filepath.is_file()
        except Exception:
            return False

# Export main utilities
__all__ = ['EndpointAnalyzer', 'SafeFileReader']