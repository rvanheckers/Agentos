"""
Prevent path traversal attacks
"""

from pathlib import Path
import os
from security.exceptions import SecurityError


class PathSanitizer:
    """Beveiligde path handling"""

    # Allowed directories (configureer per environment)
    ALLOWED_INPUT_DIRS = [
        Path("/var/agentos/uploads"),
        Path("/tmp/agentos/input"),
        # Development: AgentOS io directories
        Path(__file__).parent.parent / "io" / "input",
        Path(__file__).parent.parent / "io" / "output"
    ]

    ALLOWED_OUTPUT_DIRS = [
        Path("/var/agentos/output"),
        Path("/tmp/agentos/output"),
        # Development: AgentOS io directories
        Path(__file__).parent.parent / "io" / "output",
        Path(__file__).parent.parent / "io" / "input"  # Sometimes temp files here
    ]

    @classmethod
    def validate_input_path(cls, user_path: str) -> Path:
        """
        Valideer input video path

        Raises:
            SecurityError: Als path buiten allowed dirs
        """
        # Resolve to absolute path (prevents ../.. tricks)
        try:
            # Use strict=False to allow resolving paths that don't exist yet
            # or are relative (like ./io/input/...)
            resolved = Path(user_path).resolve(strict=False)
        except Exception as e:
            raise SecurityError(f"Invalid path: {user_path} - {e}")

        # Check if within allowed directories
        for allowed_dir in cls.ALLOWED_INPUT_DIRS:
            try:
                # Resolve allowed_dir as well to ensure comparison works
                allowed_absolute = Path(allowed_dir).resolve()
                resolved.relative_to(allowed_absolute)
                return resolved  # Valid!
            except ValueError:
                continue  # Not in this dir, try next

        # Not in any allowed directory
        raise SecurityError(
            f"Path outside allowed directories: {resolved}"
        )

    @classmethod
    def validate_output_path(cls, user_path: str) -> Path:
        """
        Valideer output path (creates if not exists)

        Raises:
            SecurityError: Als path buiten allowed dirs
        """
        # Resolve to absolute path (strict=False allows non-existing paths)
        requested = Path(user_path).resolve(strict=False)

        # Check if within allowed output directories
        for allowed_dir in cls.ALLOWED_OUTPUT_DIRS:
            try:
                # Resolve allowed_dir as well to ensure comparison works
                allowed_absolute = Path(allowed_dir).resolve()
                requested.relative_to(allowed_absolute)

                # Create directory if needed (safe now)
                requested.mkdir(parents=True, exist_ok=True)

                return requested  # Valid!
            except ValueError:
                continue

        # Not in any allowed directory
        raise SecurityError(
            f"Output path outside allowed directories: {requested}"
        )

    @classmethod
    def configure_for_development(cls):
        """
        Minder strenge rules voor development
        """
        project_root = Path(__file__).parent.parent

        cls.ALLOWED_INPUT_DIRS.append(project_root / "test_videos")
        cls.ALLOWED_OUTPUT_DIRS.append(project_root / "output")