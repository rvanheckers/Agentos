#!/usr/bin/env python3
"""
AgentOS Endpoint Health Checker - MAIN SCRIPT

🎯 Wat het doet: Analyseert alle endpoints READ-ONLY en genereert rapport
🛡️ Safety: Past NIETS aan je codebase - alleen lezen en rapporteren
🚀 Gebruik: python3 run_endpoint_check.py

Voor wie: Developers die endpoint health willen monitoren
Waarom: Voorkomt endpoint chaos door vroege detectie van problemen
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import onze endpoint utilities
from utils.endpoint_utils import EndpointAnalyzer

class EndpointHealthChecker:
    """READ-ONLY endpoint analyzer - past niets aan je code"""
    
    def __init__(self, project_root: str = "../"):
        self.project_root = Path(project_root).resolve()
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Governance files paths
        self.governance_docs = [
            self.project_root / "docs" / "endpoints" / "ENDPOINT_GOVERNANCE.md",
            self.project_root / "ENDPOINT_RULES.md"
        ]
        
        # Current endpoints data
        self.openapi_url = "http://localhost:8001/openapi.json"
        self.current_endpoints = []
        self.violations = []
        
    def fetch_current_endpoints(self) -> bool:
        """Fetch current endpoints from running API (READ-ONLY)"""
        try:
            print("🔍 Fetching current endpoints from API...")
            response = requests.get(self.openapi_url, timeout=5)
            if response.status_code == 200:
                openapi_data = response.json()
                self.current_endpoints = self._parse_openapi_endpoints(openapi_data)
                print(f"   ✅ Found {len(self.current_endpoints)} active endpoints")
                return True
            else:
                print(f"   ⚠️  API not running (status {response.status_code})")
                return False
        except requests.RequestException as e:
            print(f"   ⚠️  Cannot connect to API: {e}")
            return False
    
    def _parse_openapi_endpoints(self, openapi_data: Dict) -> List[Dict]:
        """Parse OpenAPI spec into endpoint list (READ-ONLY)"""
        endpoints = []
        paths = openapi_data.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    # Determine endpoint type based on path and tags
                    endpoint_type = self._determine_endpoint_type(path, details.get("tags", []))
                    
                    endpoints.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", "No description"),
                        "tags": details.get("tags", []),
                        "type": endpoint_type,
                        "full_endpoint": f"{method.upper()} {path}"
                    })
        
        return sorted(endpoints, key=lambda x: x["path"])
    
    def _determine_endpoint_type(self, path: str, tags: List[str]) -> str:
        """Determine if endpoint is admin, user, or system"""
        # System endpoints
        if path in ["/", "/health", "/openapi.json", "/docs", "/redoc"]:
            return "system"
        
        # Admin endpoints - check path OR tags
        if path.startswith("/api/admin/") or path.startswith("/admin/"):
            return "admin"
        
        # Check tags for admin indication
        if any("admin" in tag.lower() for tag in tags):
            return "admin"
        
        # WebSocket endpoints
        if path.startswith("/ws/"):
            return "websocket"
        
        # Everything else is user endpoint
        return "user"
    
    def detect_duplicates(self) -> List[Dict]:
        """Detect potential duplicate endpoints (READ-ONLY analysis)"""
        duplicates = []
        seen_patterns = {}
        
        for endpoint in self.current_endpoints:
            # Normalize path for comparison (remove IDs, etc.)
            normalized = self._normalize_path(endpoint["path"])
            key = f"{endpoint['method']}:{normalized}"
            
            if key in seen_patterns:
                duplicates.append({
                    "pattern": key,
                    "endpoints": [seen_patterns[key], endpoint],
                    "concern": "Potential duplicate functionality"
                })
            else:
                seen_patterns[key] = endpoint
        
        return duplicates
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for duplicate detection"""
        import re
        # Replace path parameters with generic placeholder
        normalized = re.sub(r'\{[^}]+\}', '{id}', path)
        # Remove version prefixes
        normalized = re.sub(r'^/v\d+', '', normalized)
        return normalized
    
    def check_governance_compliance(self) -> List[str]:
        """Check if current state complies with governance rules (READ-ONLY)"""
        violations = []
        endpoint_count = len(self.current_endpoints)
        
        # Rule 1: Maximum 50 endpoints (updated for MVP)
        if endpoint_count > 50:
            violations.append(f"❌ Too many endpoints: {endpoint_count}/50 (exceeded by {endpoint_count-50})")
        elif endpoint_count > 45:
            violations.append(f"⚠️  Approaching limit: {endpoint_count}/50 endpoints")
        elif endpoint_count > 40:
            violations.append(f"🟡 Getting full: {endpoint_count}/50 endpoints")
        else:
            violations.append(f"✅ Endpoint count healthy: {endpoint_count}/50")
        
        # Rule 2: Check for proper tagging
        # Exception: / and /health are industry standard to be tagless
        tag_exceptions = ["/", "/health"]
        untagged = [ep for ep in self.current_endpoints if not ep["tags"] and ep["path"] not in tag_exceptions]
        exception_endpoints = [ep for ep in self.current_endpoints if not ep["tags"] and ep["path"] in tag_exceptions]
        
        if exception_endpoints:
            violations.append(f"ℹ️  {len(exception_endpoints)} system endpoints without tags (/ and /health - industry standard)")
        
        if untagged:
            violations.append(f"⚠️  {len(untagged)} endpoints without tags (should be categorized)")
        
        # Rule 3: Check for proper documentation
        undocumented = [ep for ep in self.current_endpoints if ep["summary"] == "No description"]
        if undocumented:
            violations.append(f"⚠️  {len(undocumented)} endpoints without documentation")
        
        return violations
    
    def analyze_endpoint_distribution(self) -> Dict[str, int]:
        """Analyze how endpoints are distributed by category (READ-ONLY)"""
        distribution = {}
        
        for endpoint in self.current_endpoints:
            for tag in endpoint["tags"]:
                distribution[tag] = distribution.get(tag, 0) + 1
        
        return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))
    
    def analyze_endpoint_types(self) -> Dict[str, int]:
        """Analyze endpoint distribution by type (admin/user/system)"""
        type_distribution = {
            "admin": 0,
            "user": 0,
            "system": 0,
            "websocket": 0
        }
        
        for endpoint in self.current_endpoints:
            endpoint_type = endpoint.get("type", "user")
            type_distribution[endpoint_type] = type_distribution.get(endpoint_type, 0) + 1
        
        return type_distribution
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report (READ-ONLY analysis)"""
        duplicates = self.detect_duplicates()
        governance_check = self.check_governance_compliance()
        distribution = self.analyze_endpoint_distribution()
        type_distribution = self.analyze_endpoint_types()
        
        # 🔍 NIEUWE FUNCTIONALITEIT: Scan API logs voor FastAPI warnings
        log_warnings = EndpointAnalyzer.scan_api_logs_for_warnings(str(self.project_root / "logs" / "api.log"))
        
        # Update governance check met log warnings
        if log_warnings["duplicate_operation_ids"]:
            governance_check.append(f"⚠️  FastAPI warnings: {len(log_warnings['duplicate_operation_ids'])} duplicate Operation IDs found")
        
        if log_warnings["404_errors"]:
            unique_404s = set(w["path"] for w in log_warnings["404_errors"])
            if len(unique_404s) > 5:  # Only report if significant
                governance_check.append(f"⚠️  Broken endpoints: {len(unique_404s)} endpoints returning 404 errors")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_endpoints": len(self.current_endpoints),
                "admin_endpoints": type_distribution["admin"],
                "user_endpoints": type_distribution["user"],
                "system_endpoints": type_distribution["system"],
                "potential_duplicates": len(duplicates),
                "governance_violations": len([v for v in governance_check if v.startswith("❌")]),
                "warnings": len([v for v in governance_check if v.startswith("⚠️")]),
                "health_score": self._calculate_health_score(duplicates, governance_check)
            },
            "endpoints": self.current_endpoints,
            "duplicates": duplicates,
            "governance": governance_check,
            "distribution": distribution,
            "type_distribution": type_distribution,
            "log_warnings": log_warnings,  # 🆕 Nieuwe sectie
            "recommendations": self._generate_recommendations(duplicates, governance_check)
        }
        
        return report
    
    def _calculate_health_score(self, duplicates: List, governance: List) -> str:
        """Calculate overall endpoint health score"""
        violations = len([g for g in governance if g.startswith("❌")])
        warnings = len([g for g in governance if g.startswith("⚠️")])
        duplicate_count = len(duplicates)
        
        if violations > 0 or duplicate_count > 5:
            return "🔴 CRITICAL"
        elif warnings > 2 or duplicate_count > 2:
            return "🟠 WARNING"
        elif warnings > 0 or duplicate_count > 0:
            return "🟡 CAUTION"
        else:
            return "🟢 HEALTHY"
    
    def _generate_recommendations(self, duplicates: List, governance: List) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check for legacy admin endpoints
        admin_endpoints = [ep for ep in self.current_endpoints if ep.get("type") == "admin"]
        non_ssot_admin = [ep for ep in admin_endpoints if not ep["path"].startswith("/api/admin/ssot")]
        if non_ssot_admin:
            recommendations.append(f"🚨 LEGACY: {len(non_ssot_admin)} admin endpoints should be disabled (use SSOT instead):")
            for ep in non_ssot_admin:
                recommendations.append(f"   → Disable: {ep['full_endpoint']}")
        
        # Check for missing tags
        no_tag_endpoints = [ep for ep in self.current_endpoints 
                          if not ep["tags"] and ep["path"] not in ["/", "/health"]]
        if no_tag_endpoints:
            recommendations.append(f"🏷️  TAG MISSING: {len(no_tag_endpoints)} endpoints need tags:")
            for ep in no_tag_endpoints[:5]:  # Show first 5
                tag_suggestion = self._suggest_tag(ep)
                recommendations.append(f"   → {ep['full_endpoint']} should have tag: [{tag_suggestion}]")
        
        if duplicates:
            recommendations.append(f"🔧 Review {len(duplicates)} potential duplicate endpoints for consolidation")
        
        violations = [g for g in governance if g.startswith("❌")]
        if violations:
            recommendations.append("📋 Address governance violations before adding new endpoints")
        
        if len(self.current_endpoints) > 40:
            recommendations.append("🎯 Consider refactoring to reduce endpoint count")
        
        if not recommendations:
            recommendations.append("✅ Endpoint architecture is healthy - continue good practices")
        
        return recommendations
    
    def _suggest_tag(self, endpoint: Dict) -> str:
        """Suggest appropriate tag for endpoint"""
        path = endpoint["path"]
        
        if "admin" in path:
            return "admin-dashboard"
        elif "jobs" in path:
            return "jobs"
        elif "agents" in path:
            return "agents"
        elif "upload" in path:
            return "upload"
        elif "queue" in path:
            return "queue"
        else:
            return "general"
    
    def save_report(self, report: Dict) -> Path:
        """Save report to data directory and detect changes"""
        filepath = self.data_dir / "endpoint_report.json"
        
        # Check for previous report to detect changes
        previous_report = None
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    previous_report = json.load(f)
            except:
                pass
        
        # Add change detection to report
        if previous_report:
            report["changes"] = self._detect_changes(previous_report, report)
        else:
            report["changes"] = {"first_run": True}
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    def _detect_changes(self, old_report: Dict, new_report: Dict) -> Dict:
        """Detect changes between reports"""
        changes = {
            "endpoint_count_change": new_report["summary"]["total_endpoints"] - old_report["summary"]["total_endpoints"],
            "admin_endpoint_change": new_report["summary"]["admin_endpoints"] - old_report["summary"]["admin_endpoints"],
            "health_change": {
                "from": old_report["summary"]["health_score"],
                "to": new_report["summary"]["health_score"]
            },
            "warnings_change": new_report["summary"]["warnings"] - old_report["summary"]["warnings"],
            "added_endpoints": [],
            "removed_endpoints": [],
            "tag_changes": []
        }
        
        # Detect endpoint changes
        old_endpoints = {ep["full_endpoint"]: ep for ep in old_report["endpoints"]}
        new_endpoints = {ep["full_endpoint"]: ep for ep in new_report["endpoints"]}
        
        # Find added/removed endpoints
        for endpoint in new_endpoints:
            if endpoint not in old_endpoints:
                changes["added_endpoints"].append(new_endpoints[endpoint])
        
        for endpoint in old_endpoints:
            if endpoint not in new_endpoints:
                changes["removed_endpoints"].append(old_endpoints[endpoint])
        
        # Detect tag changes
        for endpoint in new_endpoints:
            if endpoint in old_endpoints:
                old_tags = set(old_endpoints[endpoint]["tags"])
                new_tags = set(new_endpoints[endpoint]["tags"])
                if old_tags != new_tags:
                    changes["tag_changes"].append({
                        "endpoint": endpoint,
                        "old_tags": list(old_tags),
                        "new_tags": list(new_tags)
                    })
        
        return changes
    
    def print_summary_report(self, report: Dict):
        """Print human-readable summary to terminal"""
        summary = report["summary"]
        
        print("\n🎯 AGENTOS ENDPOINT HEALTH REPORT")
        print("=" * 50)
        print(f"📊 Overall Health: {summary['health_score']}")
        print(f"📈 Total Endpoints: {summary['total_endpoints']}")
        print()
        print("📋 Endpoint Types:")
        print(f"   👤 User Endpoints: {summary['user_endpoints']}")
        print(f"   🔐 Admin Endpoints: {summary['admin_endpoints']}")
        print(f"   ⚙️  System Endpoints: {summary['system_endpoints']}")
        
        # Show actual admin endpoints
        if summary['admin_endpoints'] > 0:
            print("\n   🔐 Admin Endpoints Detail:")
            admin_endpoints = [ep for ep in report["endpoints"] if ep.get("type") == "admin"]
            for ep in admin_endpoints:
                tags = f" [{', '.join(ep['tags'])}]" if ep['tags'] else " [NO TAGS]"
                print(f"      → {ep['full_endpoint']}{tags}")
        
        print()
        print(f"⚠️  Potential Duplicates: {summary['potential_duplicates']}")
        print(f"❌ Governance Violations: {summary['governance_violations']}")
        print(f"🔍 Warnings: {summary['warnings']}")
        print()
        
        # Governance check results
        print("📋 Governance Compliance:")
        for check in report["governance"]:
            print(f"   {check}")
        print()
        
        # Show duplicates if found
        if report["duplicates"]:
            print("🔍 Potential Duplicates Found:")
            for dup in report["duplicates"][:5]:  # Show first 5
                print(f"   ❓ {dup['pattern']}")
            if len(report["duplicates"]) > 5:
                print(f"   ... and {len(report['duplicates']) - 5} more")
            print()
        
        # 🆕 NIEUWE SECTIE: Show log warnings if found
        log_warnings = report.get("log_warnings", {})
        if any(log_warnings.values()):
            print("🔍 Log Analysis Results:")
            
            if log_warnings.get("duplicate_operation_ids"):
                print(f"   🍳 {len(log_warnings['duplicate_operation_ids'])} FastAPI Operation ID conflicts found")
                for warning in log_warnings["duplicate_operation_ids"][:3]:
                    print(f"      → {warning['operation']}: {warning['issue']}")
            
            if log_warnings.get("404_errors"):
                unique_404s = set(w["path"] for w in log_warnings["404_errors"])
                if len(unique_404s) > 5:
                    print(f"   🚫 {len(unique_404s)} endpoints returning 404 errors")
                    # Show most frequent 404s
                    frequent_404s = list(unique_404s)[:5]
                    for path in frequent_404s:
                        print(f"      → {path}")
            
            if log_warnings.get("route_conflicts"):
                print(f"   ⚠️  {len(log_warnings['route_conflicts'])} route conflicts detected")
            
            print()
        
        # Endpoint distribution
        print("📊 Endpoint Distribution by Category:")
        for category, count in list(report["distribution"].items())[:8]:
            print(f"   {count:2d} endpoints - {category}")
        print()
        
        # Recommendations
        print("💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"   {rec}")
        print()
        
        # Show changes if detected
        if "changes" in report and not report["changes"].get("first_run"):
            self.print_changes(report["changes"])
        
        print("✅ Report complete! All analysis performed READ-ONLY.")
        print(f"📁 Detailed report saved to: {self.data_dir}/endpoint_report.json")
    
    def print_changes(self, changes: Dict):
        """Print detected changes"""
        print("🔄 CHANGES DETECTED SINCE LAST RUN:")
        print("-" * 40)
        
        # Endpoint count changes
        if changes["endpoint_count_change"] != 0:
            change = changes["endpoint_count_change"]
            emoji = "📈" if change > 0 else "📉"
            print(f"   {emoji} Total endpoints: {'+' if change > 0 else ''}{change}")
        
        # Admin endpoint changes
        if changes["admin_endpoint_change"] != 0:
            change = changes["admin_endpoint_change"]
            emoji = "🔐" if change > 0 else "✂️"
            print(f"   {emoji} Admin endpoints: {'+' if change > 0 else ''}{change}")
        
        # Health changes
        health_change = changes["health_change"]
        if health_change["from"] != health_change["to"]:
            print(f"   🏥 Health: {health_change['from']} → {health_change['to']}")
        
        # Warning changes
        if changes["warnings_change"] != 0:
            change = changes["warnings_change"]
            emoji = "⚠️" if change > 0 else "✅"
            print(f"   {emoji} Warnings: {'+' if change > 0 else ''}{change}")
        
        # Removed endpoints
        if changes["removed_endpoints"]:
            print(f"   ❌ Removed endpoints:")
            for ep in changes["removed_endpoints"]:
                print(f"      → {ep['full_endpoint']}")
        
        # Added endpoints  
        if changes["added_endpoints"]:
            print(f"   ➕ Added endpoints:")
            for ep in changes["added_endpoints"]:
                print(f"      → {ep['full_endpoint']}")
        
        # Tag changes
        if changes["tag_changes"]:
            print(f"   🏷️  Tag updates:")
            for change in changes["tag_changes"]:
                old_tags = change["old_tags"] or ["NO TAGS"]
                new_tags = change["new_tags"] or ["NO TAGS"]
                print(f"      → {change['endpoint']}: {old_tags} → {new_tags}")
        
        print()

def main():
    """Main function - safe READ-ONLY endpoint analysis"""
    print("🚀 AgentOS Endpoint Health Checker")
    print("🛡️  READ-ONLY MODE - No changes will be made to your codebase")
    print("-" * 60)
    
    try:
        checker = EndpointHealthChecker()
        
        # Try to fetch current endpoints
        api_available = checker.fetch_current_endpoints()
        
        if not api_available:
            print("📋 API not available - cannot perform live analysis")
            print("💡 Start your API server (localhost:8001) for complete analysis")
            return
        
        # Generate comprehensive report
        print("📊 Analyzing endpoint health...")
        report = checker.generate_report()
        
        # Save report
        report_path = checker.save_report(report)
        
        # Print summary
        checker.print_summary_report(report)
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print("💡 This is a READ-ONLY analysis tool - no harm done to your code")

if __name__ == "__main__":
    main()