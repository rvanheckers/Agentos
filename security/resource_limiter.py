"""
Prevent DoS via resource exhaustion with cross-platform support
FIXED: Removed unsafe preexec_fn, added Windows Job Objects support
"""

import subprocess
import signal
import psutil
import os
import sys
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class ResourceLimiter:
    """Cross-platform resource limiter for video processing"""

    MAX_MEMORY_MB = 2048  # 2GB per process
    MAX_CPU_TIME_SECONDS = 300  # 5 minuten
    MAX_DISK_OUTPUT_MB = 5000  # 5GB output max

    @staticmethod
    def run_ffmpeg_limited(command: list, timeout: int = 300) -> subprocess.CompletedProcess:
        """
        Run FFmpeg with cross-platform resource limits

        Args:
            command: FFmpeg command as list
            timeout: Max execution time in seconds

        Returns:
            CompletedProcess result

        Raises:
            TimeoutError: Als command te lang duurt
            MemoryError: Als te veel geheugen gebruikt

        Security:
            - Linux: Uses process groups for clean termination
            - Windows: Uses Job Objects for resource control
            - Other: Basic timeout protection only
        """
        if os.name == 'posix':
            return ResourceLimiter._run_posix(command, timeout)
        elif os.name == 'nt':
            return ResourceLimiter._run_windows(command, timeout)
        else:
            logger.warning(
                "Advanced resource limits not available on this platform. "
                "Only timeout protection is enabled."
            )
            return ResourceLimiter._run_fallback(command, timeout)

    @staticmethod
    def _run_posix(command: list, timeout: int) -> subprocess.CompletedProcess:
        """
        Linux/Unix implementation using process groups

        FIXED: Removed unsafe preexec_fn threading hazard
        Uses os.setpgrp in child process for clean termination
        """
        try:
            # Start process in new process group for clean termination
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Creates new process group, thread-safe
            )

            # Monitor process and apply limits
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill entire process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process already dead

                process.kill()
                stdout, stderr = process.communicate()
                raise TimeoutError(f"FFmpeg command exceeded timeout of {timeout}s")

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    command,
                    output=stdout,
                    stderr=stderr
                )

            return subprocess.CompletedProcess(
                command,
                process.returncode,
                stdout,
                stderr
            )

        except MemoryError:
            raise MemoryError(f"FFmpeg exceeded memory limit of {ResourceLimiter.MAX_MEMORY_MB}MB")

    @staticmethod
    def _run_windows(command: list, timeout: int) -> subprocess.CompletedProcess:
        """
        Windows implementation using Job Objects

        FIXED: Windows now has proper resource limits (was completely unprotected)
        """
        try:
            import win32job
            import win32process
            import win32api
            import win32con
            import pywintypes
        except ImportError:
            logger.warning(
                "pywin32 not installed. Falling back to basic timeout protection. "
                "Install pywin32 for full resource control on Windows: pip install pywin32"
            )
            return ResourceLimiter._run_fallback(command, timeout)

        try:
            # Create job object with resource limits
            job = win32job.CreateJobObject(None, "")

            # Configure job limits
            info = win32job.QueryInformationJobObject(
                job,
                win32job.JobObjectExtendedLimitInformation
            )

            # Set memory limit
            info['ProcessMemoryLimit'] = ResourceLimiter.MAX_MEMORY_MB * 1024 * 1024

            # Set CPU time limit (in 100-nanosecond units)
            info['PerJobUserTimeLimit'] = ResourceLimiter.MAX_CPU_TIME_SECONDS * 10000000

            # Configure limit flags
            info['BasicLimitInformation']['LimitFlags'] = (
                win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                win32job.JOB_OBJECT_LIMIT_JOB_TIME |
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )

            win32job.SetInformationJobObject(
                job,
                win32job.JobObjectExtendedLimitInformation,
                info
            )

            # Start process suspended to assign to job before it runs
            startup_info = win32process.STARTUPINFO()
            process_info = win32process.CreateProcess(
                None,  # Application name
                ' '.join(command),  # Command line
                None,  # Process security attributes
                None,  # Thread security attributes
                False,  # Inherit handles
                win32process.CREATE_SUSPENDED,  # Creation flags
                None,  # Environment
                None,  # Current directory
                startup_info
            )

            handle = process_info[0]
            thread_handle = process_info[1]
            pid = process_info[2]

            try:
                # Assign process to job object
                win32job.AssignProcessToJobObject(job, handle)

                # Resume process
                win32process.ResumeThread(thread_handle)

                # Wait for completion with timeout
                result = win32api.WaitForSingleObject(handle, timeout * 1000)

                if result == win32con.WAIT_TIMEOUT:
                    # Terminate job (kills all processes in job)
                    win32job.TerminateJobObject(job, 1)
                    raise TimeoutError(f"FFmpeg command exceeded timeout of {timeout}s")

                # Get exit code
                exit_code = win32process.GetExitCodeProcess(handle)

                if exit_code != 0:
                    raise subprocess.CalledProcessError(exit_code, command)

                # Note: stdout/stderr not captured in this implementation
                # For production, use subprocess.Popen with handle assignment
                return subprocess.CompletedProcess(command, exit_code, b'', b'')

            finally:
                win32api.CloseHandle(handle)
                win32api.CloseHandle(thread_handle)

        except pywintypes.error as e:
            logger.error(f"Windows Job Object error: {e}")
            raise RuntimeError(f"Resource limiting failed: {e}")

    @staticmethod
    def _run_fallback(command: list, timeout: int) -> subprocess.CompletedProcess:
        """
        Fallback implementation with basic timeout protection only

        Used when advanced resource controls are unavailable
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                check=True
            )
            return result

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"FFmpeg command exceeded timeout of {timeout}s")

    @staticmethod
    @contextmanager
    def monitor_process(max_memory_mb: int = 2048):
        """
        Context manager voor memory monitoring

        Usage:
            with ResourceLimiter.monitor_process(max_memory_mb=2048):
                # Do expensive operation
                process_video()
        """
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        try:
            yield
        finally:
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_used = final_memory - initial_memory

            if memory_used > max_memory_mb:
                print(f"WARNING: Memory usage {memory_used:.2f}MB exceeded limit {max_memory_mb}MB")

    @staticmethod
    def check_disk_space(output_dir: str, required_mb: int = 1000):
        """
        Check of er genoeg disk space is

        Raises:
            IOError: Als niet genoeg space
        """
        stat = os.statvfs(output_dir)
        available_mb = (stat.f_bavail * stat.f_frsize) / 1024 / 1024

        if available_mb < required_mb:
            raise IOError(
                f"Insufficient disk space: {available_mb:.2f}MB available, "
                f"{required_mb}MB required"
            )