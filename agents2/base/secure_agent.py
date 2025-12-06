"""
Base class voor beveiligde agents
"""

from security.video_validator import VideoSecurityValidator
from security.path_sanitizer import PathSanitizer
from security.resource_limiter import ResourceLimiter
from security.exceptions import SecurityError
from typing import Dict, Any


class SecureVideoAgent:
    """
    Base class die alle agents moeten gebruiken
    """

    def __init__(self):
        self.validator = VideoSecurityValidator()
        self.path_sanitizer = PathSanitizer
        self.resource_limiter = ResourceLimiter

    def process_video_safely(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Template method voor veilige video processing

        Usage in agents:
            class FaceDetector(SecureVideoAgent):
                def _process_validated_video(self, video_path, metadata):
                    # Your detection logic here
                    pass
        """
        try:
            # 1. Validate input path
            raw_path = input_data.get('video_path')
            if not raw_path:
                return {"success": False, "error": "No video_path provided"}

            safe_input_path = self.path_sanitizer.validate_input_path(raw_path)

            # 2. Validate video file
            metadata = self.validator.validate_or_raise(str(safe_input_path))

            # 3. Check disk space (if output path provided)
            if 'output_path' in input_data:
                safe_output_path = self.path_sanitizer.validate_output_path(
                    input_data['output_path']
                )
                self.resource_limiter.check_disk_space(str(safe_output_path))
            else:
                safe_output_path = None

            # 4. Process with resource monitoring
            with self.resource_limiter.monitor_process(max_memory_mb=2048):
                result = self._process_validated_video(
                    video_path=safe_input_path,
                    output_path=safe_output_path,
                    metadata=metadata,
                    input_data=input_data
                )

            return result

        except SecurityError as e:
            return {
                "success": False,
                "error": f"Security validation failed: {str(e)}",
                "error_type": "security"
            }
        except TimeoutError as e:
            return {
                "success": False,
                "error": f"Processing timeout: {str(e)}",
                "error_type": "timeout"
            }
        except Exception as e:
            # Don't expose internal paths in error messages!
            return {
                "success": False,
                "error": "Internal processing error",
                "error_type": "internal"
            }

    def _process_validated_video(
        self,
        video_path,
        output_path,
        metadata,
        input_data
    ) -> Dict[str, Any]:
        """
        Override this in subclasses
        Video is already validated at this point
        """
        raise NotImplementedError("Subclass must implement _process_validated_video")