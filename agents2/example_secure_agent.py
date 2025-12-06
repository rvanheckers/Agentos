"""
Example: How to create a secure video agent

This demonstrates the proper usage of SecureVideoAgent base class.
All new agents MUST inherit from this class to ensure security.
"""

from agents2.base.secure_agent import SecureVideoAgent
from pathlib import Path
import cv2


class ExampleSecureAgent(SecureVideoAgent):
    """
    Example agent showing secure video processing pattern

    Usage:
        agent = ExampleSecureAgent()
        result = agent.process_video({
            'video_path': '/var/agentos/uploads/video.mp4',
            'output_path': '/var/agentos/output/processed/'
        })
    """

    def __init__(self):
        super().__init__()
        # Initialize your agent-specific resources here
        self.frame_count = 0

    def _process_validated_video(
        self,
        video_path: Path,
        output_path: Path,
        metadata: dict,
        input_data: dict
    ) -> dict:
        """
        Core processing logic - video is already validated!

        At this point you know:
        - Video exists and is accessible
        - Video is under 500MB
        - Video is under 1 hour
        - Video is under 4K resolution
        - Video MIME type is valid
        - Paths are sanitized (no traversal attacks)
        - Disk space is available

        Args:
            video_path: Validated, safe input path
            output_path: Validated, safe output directory
            metadata: Video metadata (duration, resolution, etc)
            input_data: Original input data from user

        Returns:
            dict: Processing result with 'success' key
        """
        try:
            # Example: Process video frame by frame
            cap = cv2.VideoCapture(str(video_path))

            frames_processed = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Your processing logic here
                # Example: Just count frames
                frames_processed += 1

            cap.release()

            return {
                "success": True,
                "frames_processed": frames_processed,
                "duration_seconds": metadata.get("duration_seconds"),
                "resolution": f"{metadata.get('width')}x{metadata.get('height')}",
                "file_size_mb": metadata.get("file_size_mb")
            }

        except Exception as e:
            # Return error without exposing internal details
            return {
                "success": False,
                "error": "Processing failed",
                "error_type": "processing"
            }

    def process_video(self, input_data: dict) -> dict:
        """
        Public API method

        This wraps process_video_safely() from SecureVideoAgent
        which handles all security validation.
        """
        return self.process_video_safely(input_data)


# Example usage
if __name__ == "__main__":
    from security.path_sanitizer import PathSanitizer

    # For development/testing, configure relaxed paths
    PathSanitizer.configure_for_development()

    agent = ExampleSecureAgent()

    # Example with valid input (would need actual video file)
    result = agent.process_video({
        'video_path': '/tmp/test_video.mp4'  # This will fail security check
    })

    print(f"Result: {result}")
    print(f"Error type: {result.get('error_type')}")  # Should be 'security'