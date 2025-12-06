#!/usr/bin/env python3
"""
IO Manager - Automatic cleanup when folders exceed limit
========================================================
Real-time cleanup van io folders wanneer er meer dan 3 jobs zijn.
Draait direct na job completion, niet 's nachts.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import logging

# Add scripts directory for IO cleanup
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from io_cleanup import IOCleanup

logger = logging.getLogger(__name__)

class IOManager:
    """
    Manages IO folders with automatic cleanup when limit exceeded
    """

    def __init__(self, max_jobs: int = 3):
        """
        Initialize IO Manager

        Args:
            max_jobs: Maximum jobs to keep per folder before triggering cleanup
        """
        self.max_jobs = max_jobs
        self.base_path = Path(__file__).parent.parent
        self.io_path = self.base_path / "io"

    def count_job_folders(self, folder_path: Path) -> int:
        """Count UUID job folders in given path"""
        if not folder_path.exists():
            return 0

        count = 0
        for folder in folder_path.iterdir():
            if folder.is_dir():
                # Check if folder name looks like UUID
                folder_name = folder.name
                if (len(folder_name) == 36 and
                    folder_name.count('-') == 4 and
                    folder_name != "test_download"):  # Exclude test folders
                    count += 1
        return count

    def check_and_cleanup(self) -> Dict[str, Any]:
        """
        Check if cleanup is needed and trigger if necessary
        Returns cleanup stats or None if no cleanup was needed
        """
        input_count = self.count_job_folders(self.io_path / "input")
        output_count = self.count_job_folders(self.io_path / "output")

        max_count = max(input_count, output_count)

        if max_count > self.max_jobs:
            logger.info(f"🧹 IO cleanup triggered: {input_count} input jobs, {output_count} output jobs (limit: {self.max_jobs})")

            try:
                cleaner = IOCleanup(max_jobs=self.max_jobs, dry_run=False)
                stats = cleaner.run()

                logger.info(f"✅ Auto-cleanup completed: {stats['folders_deleted']} folders deleted, "
                           f"{stats['space_freed_mb']:.2f} MB freed")

                return {
                    'triggered': True,
                    'reason': f'Exceeded limit ({max_count} > {self.max_jobs})',
                    'before_counts': {'input': input_count, 'output': output_count},
                    'stats': stats
                }

            except Exception as e:
                logger.error(f"❌ Auto-cleanup failed: {e}")
                return {'triggered': True, 'error': str(e)}

        return {
            'triggered': False,
            'counts': {'input': input_count, 'output': output_count},
            'limit': self.max_jobs
        }

    def trigger_cleanup_if_needed(self) -> Dict[str, Any]:
        """
        Public method to trigger cleanup check
        Call this after creating new jobs/folders
        """
        return self.check_and_cleanup()

# Global instance
io_manager = IOManager()

def trigger_io_cleanup_if_needed() -> Dict[str, Any]:
    """
    Convenience function to trigger cleanup check
    Use this in your job processing pipeline
    """
    return io_manager.trigger_cleanup_if_needed()