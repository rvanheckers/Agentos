"""
Constraint Enforcer - Hoofdtool voor Script Size Monitoring in AgentOS

Wat doet het: Scant alle Python bestanden en waarschuwt als ze te groot worden
Hoe werkt het: 🟢 groen (goed) → 🟡 geel (let op) → 🟠 oranje (te groot) → 🔴 rood (probleem)
Limieten: 3000-4000 regels code per bestand (configureerbaar)
Gebruikt door: Developers om code kwaliteit te bewaken
Start met: python constraint_enforcer.py (vanuit script-monitoring directory)
"""
from pathlib import Path
from typing import Dict, Any, List
from utils.file_utils import get_project_structure, count_lines_in_file
# Context verification imports
try:
    from utils.verification_engine import VerificationEngine, VerificationLevel, VerificationResult
    from utils.context_knowledge_base import get_context_kb
    CONTEXT_VERIFICATION_AVAILABLE = True
except ImportError as e:
    print(f"Context verification not available: {e}")
    CONTEXT_VERIFICATION_AVAILABLE = False

class SmartConstraintEnforcer:
    """Simple gradient enforcement according to SMART-REBUILD-GUIDE.md"""
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.levels = {"green": {"max": 0.8, "icon": "🟢"}, "yellow": {"max": 1.0, "icon": "🟡"}, "orange": {"max": 1.2, "icon": "🟠"}, "red": {"max": float('inf'), "icon": "🔴"}}
        self.BASE_LINES = 3000
        self.MAX_LINES = 4000
        self.INFRASTRUCTURE_MAX = 300
        self._load_custom_limits()
        self.limits = {"main.py": 700, "automation/doc_generator.py": 200, "automation/visual_architecture.py": 250, "automation/validator.py": 150, "automation/dashboard.py": 220, "automation/backup.py": 120, "agents/placement_agent.py": 250, "agents/milestone_agent.py": 180, "constraint_enforcer.py": 350, "utils/vibecoder_dashboard.py": 1000, "utils/vibecoder_context_guardian.py": 200, "utils/milestone_manager.py": 200}
        # Initialize context verification (defer status update to avoid circular dependency)
        self.context_verification_enabled = CONTEXT_VERIFICATION_AVAILABLE
        if self.context_verification_enabled:
            try:
                self.context_kb = get_context_kb(str(self.project_path))
                self.verification_engine = VerificationEngine(str(self.project_path))
            except Exception as e:
                print(f"Context verification initialization failed: {e}")
                self.context_verification_enabled = False
                self.verification_engine = None
                self.context_kb = None
        else:
            self.verification_engine = None
            self.context_kb = None

    def get_current_status(self) -> Dict[str, Any]:
        """Get current gradient status"""
        get_project_structure(self.project_path)
        core_lines = 0
        file_status = {}
        # Check hardcoded core files with specific limits
        for file_path, limit in self.limits.items():
            full_path = self.project_path / file_path
            if full_path.exists():
                lines = count_lines_in_file(full_path)
                core_lines += lines
                file_status[file_path] = {
                    "lines": lines,
                    "limit": limit,
                    "usage_pct": round((lines / limit) * 100, 1),
                    "level": self._get_file_level(lines, limit),
                    "tracked": "specific_limit"
                }
        # Scan ALL code files by type for files over limits
        from utils.file_utils import find_code_files
        all_code_files = find_code_files(self.project_path)
        
        # Different limits per file type
        type_limits = {
            '.py': 500,   # Python - business logic
            '.js': 400,   # JavaScript - frontend logic  
            '.ts': 400,   # TypeScript - frontend logic
            '.tsx': 300,  # React components
            '.vue': 300,  # Vue components  
            '.css': 200,  # CSS stylesheets
            '.scss': 200, # SCSS stylesheets
            '.html': 150, # HTML templates
            '.json': 100, # Config files
            '.yaml': 50,  # YAML config
            '.yml': 50    # YAML config
        }
        
        for file_type, files in all_code_files.items():
            limit = type_limits.get(file_type, 300)  # Default 300 lines
            
            for file_path in files:
                rel_path = str(file_path.relative_to(self.project_path))
                if rel_path in self.limits:
                    continue  # Already handled above
                    
                lines = count_lines_in_file(file_path)
                if file_type == '.py':
                    core_lines += lines  # Only Python counts toward core
                
                # Report files over their type-specific limit
                if lines >= limit:
                    level = "red" if lines >= limit * 2 else "orange" if lines >= limit * 1.5 else "yellow"
                    file_status[rel_path] = {
                        "lines": lines, 
                        "limit": limit,
                        "file_type": file_type.strip('.').upper(),
                        "usage_pct": round((lines / limit) * 100, 1),
                        "level": level, 
                        "tracked": f"auto_detected_{file_type.strip('.')}"
                    }
        # Check infrastructure
        infrastructure = {}
        infra_path = self.project_path / "constraint_enforcer.py"
        if infra_path.exists():
            lines = count_lines_in_file(infra_path)
            infrastructure["constraint_enforcer.py"] = {"lines": lines, "limit": self.INFRASTRUCTURE_MAX, "usage_pct": round((lines / self.INFRASTRUCTURE_MAX) * 100, 1), "level": self._get_file_level(lines, self.INFRASTRUCTURE_MAX)}

        # Overall gradient level and violations
        usage_pct = (core_lines / self.BASE_LINES) * 100
        level = self._get_gradient_level(usage_pct / 100)
        violations = []
        if core_lines > self.MAX_LINES:
            violations.append(f"Total core lines {core_lines} exceeds max {self.MAX_LINES}")
        for file_path, status in file_status.items():
            if isinstance(status["limit"], int) and status["lines"] > status["limit"]:
                violations.append(f"{file_path}: {status['lines']} lines exceeds limit {status['limit']}")
            elif status.get("tracked") == "discovered" and status["lines"] > 100:
                violations.append(f"{file_path}: {status['lines']} lines in untracked file (consider adding limit)")
        # Prepare status result
        status_result = {"total_lines": core_lines, "base_limit": self.BASE_LINES, "max_limit": self.MAX_LINES, "total_usage_pct": round(usage_pct, 1), "enforcement_level": level, "enforcement_icon": self.levels[level]["icon"], "files": file_status, "infrastructure": infrastructure, "violations": violations, "gradient_analysis": {"current_level": level, "usage_ratio": round(core_lines / self.BASE_LINES, 2),
                "recommendation": self._get_recommendation(level, core_lines, file_status)
            }
        }
        # Update context knowledge base with current gradient status
        if self.context_verification_enabled and self.context_kb:
            try:
                self.context_kb.update_gradient_status(level, round(usage_pct, 1))
            except Exception as e:
                print(f"Failed to update context knowledge base: {e}")

        return status_result

    def _get_file_level(self, lines: int, limit: int) -> str:
        """Get gradient level for individual file"""
        return self._get_gradient_level(lines / limit)

    def _get_gradient_level(self, ratio: float) -> str:
        """Get overall gradient level"""
        for level, config in self.levels.items():
            if ratio <= config["max"]:
                return level
        return "red"

    def _get_recommendation(self, level: str, core_lines: int = 0, file_status: dict = None) -> str:
        """Get smart recommendation with concrete numbers and actionable advice"""
        remaining = self.MAX_LINES - core_lines
        red_threshold = int(self.BASE_LINES * 1.2)
        to_red = red_threshold - core_lines
        if level == "green":
            return f"✅ Continue development ({remaining} lines remaining to max)"
        elif level == "yellow":
            return f"⚠️ WARNING: Plan refactoring soon ({remaining} lines remaining, {to_red} until RED)"
        elif level == "orange":
            suggestion = f"Increase BASE_LINES to {core_lines + 50}, MAX_LINES to {core_lines + 200}" if to_red < 50 else "Refactor largest files"
            largest_files = sorted([(k, v['lines']) for k, v in (file_status or {}).items() if isinstance(v.get('lines'), int)], key=lambda x: x[1], reverse=True)[:2]
            files_info = f" (largest: {', '.join([f'{filename}:{lines}' for filename, lines in largest_files])})" if largest_files else ""
            return f"🟠 CAPACITY WARNING: Only {remaining} lines remaining! Consider: {suggestion}{files_info}"
        elif level == "red":
            return f"🔴 MANDATORY: Refactor before adding code! Over limit by {abs(remaining)} lines"
        return "Unknown level"

    def _discover_core_files(self) -> List[Path]:
        """Discover all core files that should be tracked in AgentOS project"""
        core_files = []

        # AgentOS relevant file extensions
        extensions = [".py", ".js", ".json", ".ts", ".tsx", ".vue"]

        # Include root level files
        for ext in [".py", ".js", ".json"]:  # Most common at root
            for file_path in self.project_path.glob(f"*{ext}"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    core_files.append(file_path)

        # AgentOS core directories
        core_directories = [
            "api", "services", "workers", "agents2", "database", "websockets",
            "ui-admin/src", "ui-v2/src", "ui-admin-clean/assets/js",
            "scripts", "script-monitoring"
        ]

        # Include files in core directories
        for core_dir in core_directories:
            core_dir_path = self.project_path / core_dir
            if core_dir_path.exists() and core_dir_path.is_dir():
                for ext in extensions:
                    for file_path in core_dir_path.rglob(f"*{ext}"):
                        if file_path.is_file() and not file_path.name.startswith('.'):
                            # Skip node_modules and other ignore directories
                            if "node_modules" not in str(file_path) and ".git" not in str(file_path):
                                core_files.append(file_path)
        return core_files

    def _load_custom_limits(self):
        """Load custom limits from file if they exist"""
        limits_file = self.project_path / "script-monitoring" / "vibecoder_limits.json"
        if limits_file.exists():
            try:
                import json
                with open(limits_file, 'r') as f:
                    custom_limits = json.load(f)
                    self.BASE_LINES = custom_limits.get('base_lines', self.BASE_LINES)
                    self.MAX_LINES = custom_limits.get('max_lines', self.MAX_LINES)
                    self.INFRASTRUCTURE_MAX = custom_limits.get('infrastructure_max', self.INFRASTRUCTURE_MAX)
                    if 'file_limits' in custom_limits:
                        self.limits.update(custom_limits['file_limits'])
            except Exception as e:
                print(f"Warning: Failed to load custom limits: {e}")

    def update_limits(self, base_lines: int = None, max_lines: int = None, infrastructure_max: int = None, file_limits: dict = None) -> dict:
        """Update gradient limits and save to file"""
        try:
            # Update limits if provided
            if base_lines is not None:
                self.BASE_LINES = max(100, base_lines)  # Minimum safety check
            if max_lines is not None:
                self.MAX_LINES = max(self.BASE_LINES + 100, max_lines)  # Must be higher than base
            if infrastructure_max is not None:
                self.INFRASTRUCTURE_MAX = max(50, infrastructure_max)
            if file_limits:
                self.limits.update(file_limits)

            # Save to file
            limits_data = {
                'base_lines': self.BASE_LINES,
                'max_lines': self.MAX_LINES,
                'infrastructure_max': self.INFRASTRUCTURE_MAX,
                'file_limits': self.limits
            }

            limits_file = self.project_path / "script-monitoring" / "vibecoder_limits.json"
            import json
            with open(limits_file, 'w') as f:
                json.dump(limits_data, f, indent=2)

            return {
                'status': 'success',
                'message': 'Limits updated successfully',
                'new_limits': {
                    'base_lines': self.BASE_LINES,
                    'max_lines': self.MAX_LINES,
                    'infrastructure_max': self.INFRASTRUCTURE_MAX
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to update limits: {str(e)}'
            }

    def get_limits(self) -> dict:
        """Get current limits for UI display"""
        return {
            'base_lines': self.BASE_LINES,
            'max_lines': self.MAX_LINES,
            'infrastructure_max': self.INFRASTRUCTURE_MAX,
            'file_limits': self.limits.copy()
        }

def get_enforcer(project_path: str = ".") -> SmartConstraintEnforcer:
    """Get enforcer instance"""
    return SmartConstraintEnforcer(project_path)

def enforce_constraints(action_description: str = "action") -> bool:
    """Check if action is allowed under current gradient"""
    enforcer = get_enforcer()
    status = enforcer.get_current_status()
    if status["enforcement_level"] == "red":
        print(f"🔴 BLOCKED: {action_description} - Must refactor first (RED level)")
        return False
    elif status["enforcement_level"] == "orange":
        print(f"🟠 WARNING: {action_description} - Soft limit reached, be careful")
        return True
    elif status["enforcement_level"] == "yellow":
        print(f"🟡 CAUTION: {action_description} - Approaching limits")
        return True
    else:
        print(f"🟢 OK: {action_description} - Within limits")
        return True

def enforce_constraints_with_context_verification(action_description: str = "action",
                                                ai_input: str = None,
                                                verification_level: str = "standard",
                                                session_id: str = "default") -> Dict[str, Any]:
    """
    Enhanced constraint enforcement with AI context verification
    This is the bulletproof version that guarantees AI understands context
    """
    enforcer = get_enforcer()
    # Step 1: Check gradient constraints (existing logic)
    gradient_status = enforcer.get_current_status()
    gradient_allowed = gradient_status["enforcement_level"] != "red"
    # Step 2: Verify AI context understanding (new logic)
    context_verification = None
    if enforcer.context_verification_enabled and ai_input:

        # Map verification level string to enum
        level_mapping = {
            "routine": VerificationLevel.ROUTINE,
            "standard": VerificationLevel.STANDARD,
            "commercial": VerificationLevel.COMMERCIAL,
            "critical": VerificationLevel.CRITICAL
        }
        verification_enum = level_mapping.get(verification_level, VerificationLevel.STANDARD)
        try:
            context_verification = enforcer.verification_engine.verify_context_understanding(
                ai_input=ai_input,
                verification_level=verification_enum,
                session_id=session_id
            )
        except Exception as e:
            context_verification = VerificationResult(
                verified=False,
                confidence=0.0,
                method="error",
                duration_ms=0,
                context_fingerprint="error",
                verification_level=verification_enum,
                details={"error": str(e)},
                failed_points=["verification_system_error"],
                suggestions=[f"Context verification failed: {str(e)}"]
            )

    # Step 3: Combine results and make decision
    if not gradient_allowed:
        return {
            "status": "blocked",
            "reason": "gradient_limit_exceeded",
            "message": f"🔴 BLOCKED: {action_description} - Must refactor first (RED gradient level)",
            "gradient_status": gradient_status,
            "context_verification": context_verification,
            "allowed": False
        }

    if context_verification and not context_verification.verified:
        return {
            "status": "blocked",
            "reason": "context_verification_failed",
            "message": "🛡️ CONTEXT VERIFICATION FAILED: AI must demonstrate understanding before proceeding",
            "gradient_status": gradient_status,
            "context_verification": {
                "verified": context_verification.verified,
                "confidence": context_verification.confidence,
                "method": context_verification.method,
                "duration_ms": context_verification.duration_ms,
                "failed_points": context_verification.failed_points,
                "suggestions": context_verification.suggestions
            },
            "allowed": False,
            "next_steps": context_verification.suggestions
        }

    # Both checks passed
    confidence_info = ""
    if context_verification:
        confidence_info = f" (Context: {context_verification.confidence:.1%} confidence, {context_verification.duration_ms:.1f}ms)"

    level_icon = gradient_status["enforcement_icon"]
    level_name = gradient_status["enforcement_level"].upper()
    return {
        "status": "allowed",
        "reason": "all_checks_passed",
        "message": f"{level_icon} {level_name}: {action_description} - Approved{confidence_info}",
        "gradient_status": gradient_status,
        "context_verification": {
            "verified": context_verification.verified if context_verification else None,
            "confidence": context_verification.confidence if context_verification else None,
            "method": context_verification.method if context_verification else "not_requested",
            "duration_ms": context_verification.duration_ms if context_verification else 0
        } if context_verification else None,
        "allowed": True
    }
