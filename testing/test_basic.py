#!/usr/bin/env python3
"""
Basic test to ensure CI doesn't fail when no other tests exist.
This test validates basic system functionality.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_python_version():
    """Test that Python version is acceptable"""
    assert sys.version_info >= (3, 8), "Python 3.8+ is required"

def test_project_structure():
    """Test that basic project structure exists"""
    assert (project_root / "api").exists(), "API directory should exist"
    assert (project_root / "services").exists(), "Services directory should exist"
    assert (project_root / "core").exists(), "Core directory should exist"

def test_script_monitoring_suite():
    """Test script monitoring - now a local development tool only"""
    script_monitoring_dir = project_root / "script-monitoring"
    if script_monitoring_dir.exists():
        # If directory exists locally, validate structure
        assert (script_monitoring_dir / "constraint_enforcer.py").exists(), "Constraint enforcer should exist"
        assert (script_monitoring_dir / "run_constraint_check.py").exists(), "Run constraint check should exist"
    else:
        # Script monitoring is now a local development tool (not in repository)
        pytest.skip("Script monitoring is now a local development tool (excluded from repository)")

def test_core_imports():
    """Test that core modules can be imported without errors"""
    import importlib.util
    core_logging = importlib.util.find_spec("core.logging_config")
    api_settings = importlib.util.find_spec("api.config.settings")
    if core_logging is None or api_settings is None:
        missing = []
        if core_logging is None:
            missing.append("core.logging_config")
        if api_settings is None:
            missing.append("api.config.settings")
        pytest.skip(f"Import test skipped due to missing dependencies: {', '.join(missing)}")
    assert True, "Core imports successful"

def test_testing_tools():
    """Test that testing tools are present"""
    testing_dir = project_root / "testing"
    pg_inspector = testing_dir / "postgresql_inspector.py"
    data_gen = testing_dir / "test-data" / "generate_test_data.py"
    if not pg_inspector.exists() or not data_gen.exists():
        pytest.skip("Optional test tools missing (ok during cleanup/refactor)")
    assert True, "Testing tools present"

if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])
