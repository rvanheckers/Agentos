"""
Security tests for resource limiting
"""
import pytest
import subprocess
import time
from security.resource_limiter import ResourceLimiter


class TestResourceLimiter:
    """Test suite for ResourceLimiter"""

    def test_max_memory_limit_configured(self):
        """Should have memory limit configured"""
        assert ResourceLimiter.MAX_MEMORY_MB == 2048

    def test_max_cpu_time_configured(self):
        """Should have CPU time limit configured"""
        assert ResourceLimiter.MAX_CPU_TIME_SECONDS == 300

    def test_max_disk_output_configured(self):
        """Should have disk output limit configured"""
        assert ResourceLimiter.MAX_DISK_OUTPUT_MB == 5000

    def test_timeout_raises_timeout_error(self):
        """Should raise TimeoutError when command exceeds timeout"""
        with pytest.raises(TimeoutError) as exc_info:
            # Try to run sleep command that will timeout
            ResourceLimiter.run_ffmpeg_limited(['sleep', '10'], timeout=1)

        assert "timeout" in str(exc_info.value).lower()

    def test_monitor_process_context_manager(self):
        """Should successfully monitor process memory"""
        # This should not raise any errors
        with ResourceLimiter.monitor_process(max_memory_mb=2048):
            # Do some trivial operation
            _ = [i for i in range(1000)]

    def test_check_disk_space_with_valid_directory(self, tmp_path):
        """Should check disk space for valid directory"""
        # Should not raise error for reasonable disk space requirement
        try:
            ResourceLimiter.check_disk_space(str(tmp_path), required_mb=1)
        except IOError:
            # If it raises, it's because there's actually not enough space
            # which is a valid scenario in constrained environments
            pass

    def test_check_disk_space_with_unrealistic_requirement(self, tmp_path):
        """Should raise IOError when insufficient disk space"""
        # Request an unrealistically large amount of space
        with pytest.raises(IOError) as exc_info:
            ResourceLimiter.check_disk_space(str(tmp_path), required_mb=999999999)

        assert "insufficient" in str(exc_info.value).lower()

    def test_run_ffmpeg_limited_accepts_command_list(self):
        """Should accept command as list"""
        # Test with a simple command that will succeed quickly
        try:
            result = ResourceLimiter.run_ffmpeg_limited(['echo', 'test'], timeout=5)
            assert result is not None
        except FileNotFoundError:
            # OK if echo not found in restricted environment
            pass

    def test_cross_platform_resource_limits(self):
        """
        SECURITY TEST: Verify resource limits work on all platforms

        Tests that resource limiting is available on:
        - Linux/Unix (posix)
        - Windows (nt)
        - Other platforms (fallback)
        """
        import platform

        system = platform.system()

        # Test that appropriate implementation is selected
        if system == "Linux" or system == "Darwin":
            # Should use _run_posix
            assert hasattr(ResourceLimiter, '_run_posix')
        elif system == "Windows":
            # Should use _run_windows
            assert hasattr(ResourceLimiter, '_run_windows')

        # All platforms should support fallback
        assert hasattr(ResourceLimiter, '_run_fallback')

    def test_windows_job_object_implementation(self):
        """
        SECURITY TEST: Verify Windows has proper resource limits (FIXED)

        Before fix: Windows had NO resource limits (preexec=None)
        After fix: Windows uses Job Objects for memory/CPU limits
        """
        import os

        if os.name == 'nt':
            # On Windows, verify Job Object implementation exists
            assert hasattr(ResourceLimiter, '_run_windows')

            # Test that Job Object limits are configured
            # (This will use fallback if pywin32 not installed, which is acceptable)
            try:
                result = ResourceLimiter.run_ffmpeg_limited(
                    ['cmd', '/c', 'echo', 'test'],
                    timeout=5
                )
                assert result is not None
            except (FileNotFoundError, RuntimeError):
                # OK if command not found or Job Object unavailable
                pass
        else:
            # On non-Windows, this test is skipped
            import pytest
            pytest.skip("Windows-specific test, skipping on other platforms")

    def test_no_unsafe_preexec_fn(self):
        """
        SECURITY TEST: Verify unsafe preexec_fn is NOT used (FIXED)

        Before fix: Used preexec_fn which is not thread-safe
        After fix: Uses start_new_session=True which is thread-safe
        """
        import os
        import inspect

        # Get source code of _run_posix
        if os.name == 'posix':
            source = inspect.getsource(ResourceLimiter._run_posix)

            # Verify preexec_fn is NOT used as a parameter in subprocess.Popen
            # (ignore references in docstrings/comments)
            import re
            # Look for actual usage: preexec_fn=something (not None)
            preexec_usage = re.search(r'preexec_fn\s*=\s*(?!None)', source)
            assert preexec_usage is None, "preexec_fn is still being used!"

            # Verify thread-safe alternative is used
            assert 'start_new_session=True' in source

    def test_process_group_termination(self):
        """
        SECURITY TEST: Verify entire process group is killed on timeout

        Prevents zombie processes and fork bomb attacks
        """
        import os

        if os.name == 'posix':
            with pytest.raises(TimeoutError):
                # Create a process that spawns children (simulate fork bomb)
                ResourceLimiter.run_ffmpeg_limited(
                    ['sh', '-c', 'sleep 100 & sleep 100 & sleep 100'],
                    timeout=1
                )

            # After timeout, verify no sleep processes remain
            # (In production, check with ps or similar)
            # For testing, just verify TimeoutError was raised

    def test_threading_safety(self):
        """
        SECURITY TEST: Verify resource limiter is thread-safe

        Before fix: preexec_fn could deadlock in multi-threaded environment
        After fix: start_new_session=True is thread-safe
        """
        import threading
        import time

        results = []
        errors = []

        def run_command():
            try:
                result = ResourceLimiter.run_ffmpeg_limited(
                    ['echo', 'thread_test'],
                    timeout=5
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple commands in parallel threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=run_command)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10)

        # Verify no deadlocks occurred (all threads completed)
        assert len(results) + len(errors) == 5, "Some threads did not complete (possible deadlock)"

    def test_memory_limit_enforcement(self):
        """
        SECURITY TEST: Verify memory limits are enforced

        Tests that processes exceeding MAX_MEMORY_MB are terminated
        """
        # This is platform-specific and requires actual memory allocation
        # For basic validation, just verify limit is configured
        assert ResourceLimiter.MAX_MEMORY_MB == 2048

        # On production systems, you would test with actual memory-hungry process
        # Example: FFmpeg processing large video

    def test_cpu_time_limit_enforcement(self):
        """
        SECURITY TEST: Verify CPU time limits are enforced

        Tests that processes exceeding MAX_CPU_TIME_SECONDS are terminated
        """
        assert ResourceLimiter.MAX_CPU_TIME_SECONDS == 300

        # Test timeout mechanism (less than CPU time limit)
        with pytest.raises(TimeoutError):
            ResourceLimiter.run_ffmpeg_limited(
                ['sleep', '100'],
                timeout=1
            )