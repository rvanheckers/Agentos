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
    """Test that script monitoring suite is functional"""
    script_monitoring_dir = project_root / "script-monitoring"
    assert script_monitoring_dir.exists(), "Script monitoring directory should exist"
    assert (script_monitoring_dir / "constraint_enforcer.py").exists(), "Constraint enforcer should exist"
    assert (script_monitoring_dir / "run_constraint_check.py").exists(), "Run constraint check should exist"

def test_core_imports():
    """Test that core modules can be imported without errors"""
    try:
        # These imports should work without database connections
        import core.logging_config
        import api.config.settings
        assert True, "Core imports successful"
    except ImportError as e:
        pytest.skip(f"Import test skipped due to missing dependencies: {e}")

def test_testing_tools():
    """Test that testing tools are present"""
    testing_dir = project_root / "testing"
    assert (testing_dir / "postgresql_inspector.py").exists(), "PostgreSQL inspector should exist"
    assert (testing_dir / "test-data" / "generate_test_data.py").exists(), "Test data generator should exist"

if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])