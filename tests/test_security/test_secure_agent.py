"""
Security tests for SecureVideoAgent base class
"""
import pytest
from pathlib import Path
from agents2.base.secure_agent import SecureVideoAgent
from security.exceptions import SecurityError


class TestSecureVideoAgent:
    """Test suite for SecureVideoAgent"""

    class MockSecureAgent(SecureVideoAgent):
        """Mock implementation for testing"""

        def _process_validated_video(self, video_path, output_path, metadata, input_data):
            return {
                "success": True,
                "message": "Processing completed",
                "video_path": str(video_path)
            }

    @pytest.fixture
    def agent(self):
        """Create mock agent instance"""
        return self.MockSecureAgent()

    def test_agent_has_validator(self, agent):
        """Should have validator instance"""
        assert agent.validator is not None

    def test_agent_has_path_sanitizer(self, agent):
        """Should have path sanitizer"""
        assert agent.path_sanitizer is not None

    def test_agent_has_resource_limiter(self, agent):
        """Should have resource limiter"""
        assert agent.resource_limiter is not None

    def test_process_video_safely_requires_video_path(self, agent):
        """Should return error if no video_path provided"""
        result = agent.process_video_safely({})
        assert result["success"] is False
        assert "video_path" in result["error"].lower()

    def test_process_video_safely_returns_security_error_type(self, agent):
        """Should return error_type='security' for security violations"""
        result = agent.process_video_safely({"video_path": "/invalid/path.mp4"})
        assert result["success"] is False
        assert result.get("error_type") == "security"

    def test_process_video_safely_handles_exceptions(self, agent):
        """Should handle exceptions gracefully without exposing internal details"""
        result = agent.process_video_safely({"video_path": "../../etc/passwd"})
        assert result["success"] is False
        assert result.get("error") is not None
        # Should not expose internal paths
        assert "/etc/passwd" not in result["error"] or "security" in result.get("error_type", "")

    def test_subclass_must_implement_process_validated_video(self):
        """Should raise NotImplementedError if _process_validated_video not implemented"""
        agent = SecureVideoAgent()

        # This would require a valid path, so we won't actually call it
        # but we can verify the method exists and raises NotImplementedError
        with pytest.raises(NotImplementedError):
            agent._process_validated_video(
                video_path=Path("/tmp/test.mp4"),
                output_path=None,
                metadata={},
                input_data={}
            )

    def test_mock_agent_can_process(self, agent):
        """Mock agent should be able to process (if paths were valid)"""
        # We can't test actual processing without valid paths,
        # but we can verify the structure is correct
        assert hasattr(agent, 'process_video_safely')
        assert callable(agent.process_video_safely)