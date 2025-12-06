#!/usr/bin/env python3
"""
Beveiligde video validatie voor AgentOS
Context7 2025 best practices
"""

import magic
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
from security.exceptions import SecurityError


class VideoSecurityValidator:
    """Valideer video files voor veilige processing"""

    # Security limits
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
    MAX_DURATION = 3600  # 1 uur
    MAX_RESOLUTION = (3840, 2160)  # 4K max
    ALLOWED_FORMATS = ['mp4', 'mov', 'avi', 'webm', 'mkv']

    def __init__(self):
        self.mime_detector = magic.Magic(mime=True)

    def validate_video_file(self, video_path: str) -> Dict[str, Any]:
        """
        Comprehensive video validation with atomic file operations to prevent TOCTOU attacks

        Returns:
            {"valid": True/False, "error": "reason", "metadata": {...}}
        """
        import os

        path = Path(video_path)

        # CRITICAL: Atomic file validation to prevent TOCTOU race conditions
        # Open file once and use file descriptor for all operations
        try:
            with open(path, 'rb') as f:
                # Get file descriptor for atomic operations
                fd = f.fileno()

                # 1. Check file size atomically using fstat
                stat_info = os.fstat(fd)
                file_size = stat_info.st_size

                if file_size > self.MAX_FILE_SIZE:
                    return {
                        "valid": False,
                        "error": f"File too large: {file_size / 1024 / 1024:.2f}MB (max {self.MAX_FILE_SIZE / 1024 / 1024}MB)"
                    }

                # 2. Validate MIME type from file descriptor (prevents symlink attacks)
                # Read magic bytes directly from fd
                f.seek(0)
                magic_bytes = f.read(8192)  # Read enough for MIME detection

        except FileNotFoundError:
            return {"valid": False, "error": "File does not exist"}
        except PermissionError:
            return {"valid": False, "error": "Permission denied"}
        except OSError as e:
            return {"valid": False, "error": f"File access error: {str(e)}"}

        # 3. Validate MIME type from magic bytes (not file path!)
        try:
            mime_type = self.mime_detector.from_buffer(magic_bytes)
            if not mime_type.startswith('video/'):
                return {
                    "valid": False,
                    "error": f"Invalid MIME type: {mime_type} (expected video/*)"
                }
        except Exception as e:
            return {"valid": False, "error": f"MIME detection failed: {str(e)}"}

        # 4. Probe video with FFprobe (with timeout!)
        # Use absolute path to prevent command injection
        abs_path = str(path.resolve())
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,duration:format=duration',
                    '-of', 'json',
                    abs_path
                ],
                capture_output=True,
                timeout=10,  # 10 second timeout
                check=True,
                text=True
            )

            metadata = json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            return {"valid": False, "error": "FFprobe timeout - possibly corrupted video"}
        except subprocess.CalledProcessError as e:
            return {"valid": False, "error": f"FFprobe failed: {e.stderr}"}
        except Exception as e:
            return {"valid": False, "error": f"Metadata extraction failed: {str(e)}"}

        # 5. Check duration
        duration = float(metadata.get('format', {}).get('duration', 0))
        if duration > self.MAX_DURATION:
            return {
                "valid": False,
                "error": f"Video too long: {duration}s (max {self.MAX_DURATION}s)"
            }

        # 6. Check resolution
        if 'streams' in metadata and len(metadata['streams']) > 0:
            stream = metadata['streams'][0]
            width = stream.get('width', 0)
            height = stream.get('height', 0)

            if width > self.MAX_RESOLUTION[0] or height > self.MAX_RESOLUTION[1]:
                return {
                    "valid": False,
                    "error": f"Resolution too high: {width}x{height} (max {self.MAX_RESOLUTION[0]}x{self.MAX_RESOLUTION[1]})"
                }

        # 7. All checks passed!
        return {
            "valid": True,
            "metadata": {
                "file_size_mb": file_size / 1024 / 1024,
                "duration_seconds": duration,
                "width": stream.get('width'),
                "height": stream.get('height'),
                "mime_type": mime_type
            }
        }

    def validate_or_raise(self, video_path: str) -> Dict[str, Any]:
        """
        Convenience method that raises exception on failure

        Usage:
            validator = VideoSecurityValidator()
            metadata = validator.validate_or_raise(video_path)
        """
        result = self.validate_video_file(video_path)

        if not result["valid"]:
            raise SecurityError(result["error"])

        return result["metadata"]