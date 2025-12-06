#!/usr/bin/env python3
"""
IO Folder Cleanup Script
========================
Houdt alleen de 3 nieuwste jobs in io/input en io/output folders.
Oudere jobs worden verwijderd (data zit in database).
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import argparse

class IOCleanup:
    def __init__(self, base_path: str = None, max_jobs: int = 3, dry_run: bool = False):
        """
        Initialize cleanup manager

        Args:
            base_path: Path to AgentOS folder (auto-detect if None)
            max_jobs: Maximum number of jobs to keep per folder (default: 3)
            dry_run: If True, only show what would be deleted without actually deleting
        """
        if base_path is None:
            # Auto-detect base path
            script_path = Path(__file__).resolve()
            self.base_path = script_path.parent.parent
        else:
            self.base_path = Path(base_path)

        self.io_path = self.base_path / "io"
        self.input_path = self.io_path / "input"
        self.output_path = self.io_path / "output"
        self.max_jobs = max_jobs
        self.dry_run = dry_run

        # Stats tracking
        self.stats = {
            'folders_scanned': 0,
            'folders_kept': 0,
            'folders_deleted': 0,
            'space_freed_mb': 0
        }

    def get_folder_info(self, folder_path: Path) -> Dict:
        """Get folder information including size and modification time"""
        try:
            # Get folder size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

            # Get modification time (newest file in folder)
            newest_time = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        mtime = os.path.getmtime(filepath)
                        newest_time = max(newest_time, mtime)

            # If no files, use folder modification time
            if newest_time == 0:
                newest_time = os.path.getmtime(folder_path)

            return {
                'path': folder_path,
                'name': folder_path.name,
                'size_bytes': total_size,
                'size_mb': total_size / (1024 * 1024),
                'modified_time': newest_time,
                'modified_datetime': datetime.fromtimestamp(newest_time)
            }
        except Exception as e:
            print(f"⚠️ Error getting info for {folder_path}: {e}")
            return None

    def cleanup_folder(self, target_path: Path) -> Tuple[List[Dict], List[Dict]]:
        """
        Clean up a single folder (input or output)
        Returns (kept_folders, deleted_folders)
        """
        if not target_path.exists():
            print(f"📁 Folder doesn't exist: {target_path}")
            return [], []

        # Get all job folders (UUID named folders)
        job_folders = []
        for folder in target_path.iterdir():
            if folder.is_dir():
                # Check if folder name looks like UUID (basic check)
                folder_name = folder.name
                if len(folder_name) == 36 and folder_name.count('-') == 4:
                    info = self.get_folder_info(folder)
                    if info:
                        job_folders.append(info)
                        self.stats['folders_scanned'] += 1

        # Sort by modification time (newest first)
        job_folders.sort(key=lambda x: x['modified_time'], reverse=True)

        # Split into keep and delete
        keep_folders = job_folders[:self.max_jobs]
        delete_folders = job_folders[self.max_jobs:]

        # Update stats
        self.stats['folders_kept'] += len(keep_folders)

        # Delete old folders
        for folder_info in delete_folders:
            folder_path = folder_info['path']
            size_mb = folder_info['size_mb']

            if self.dry_run:
                print(f"  🗑️  [DRY RUN] Would delete: {folder_path.name}")
                print(f"     Size: {size_mb:.2f} MB")
                print(f"     Modified: {folder_info['modified_datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                try:
                    shutil.rmtree(folder_path)
                    print(f"  ✅ Deleted: {folder_path.name} ({size_mb:.2f} MB)")
                    self.stats['folders_deleted'] += 1
                    self.stats['space_freed_mb'] += size_mb
                except Exception as e:
                    print(f"  ❌ Failed to delete {folder_path.name}: {e}")

        return keep_folders, delete_folders

    def run(self):
        """Run the cleanup process"""
        print("="*60)
        print("🧹 IO FOLDER CLEANUP")
        print("="*60)
        print(f"Base path: {self.base_path}")
        print(f"Max jobs per folder: {self.max_jobs}")
        print(f"Mode: {'DRY RUN (no actual deletion)' if self.dry_run else 'LIVE (will delete folders)'}")
        print()

        # Clean input folder
        print("📂 Cleaning INPUT folder...")
        input_kept, input_deleted = self.cleanup_folder(self.input_path)
        print(f"  Kept: {len(input_kept)} folders")
        if input_kept:
            for folder in input_kept:
                print(f"    ✓ {folder['name']} ({folder['size_mb']:.2f} MB)")
        print(f"  To delete: {len(input_deleted)} folders")
        print()

        # Clean output folder
        print("📂 Cleaning OUTPUT folder...")
        output_kept, output_deleted = self.cleanup_folder(self.output_path)
        print(f"  Kept: {len(output_kept)} folders")
        if output_kept:
            for folder in output_kept:
                print(f"    ✓ {folder['name']} ({folder['size_mb']:.2f} MB)")
        print(f"  To delete: {len(output_deleted)} folders")
        print()

        # Summary
        print("="*60)
        print("📊 CLEANUP SUMMARY")
        print("="*60)
        print(f"Folders scanned: {self.stats['folders_scanned']}")
        print(f"Folders kept: {self.stats['folders_kept']}")
        print(f"Folders deleted: {self.stats['folders_deleted']}")
        print(f"Space freed: {self.stats['space_freed_mb']:.2f} MB")

        if self.dry_run:
            print()
            print("ℹ️ This was a DRY RUN. No folders were actually deleted.")
            print("Run without --dry-run to perform actual cleanup.")

        return self.stats

def main():
    """Main entry point for CLI usage"""
    parser = argparse.ArgumentParser(description='Clean up IO folders, keeping only recent jobs')
    parser.add_argument('--max-jobs', type=int, default=3,
                        help='Maximum number of jobs to keep per folder (default: 3)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without actually deleting')
    parser.add_argument('--path', type=str, default=None,
                        help='Path to AgentOS folder (auto-detect if not provided)')

    args = parser.parse_args()

    # Run cleanup
    cleaner = IOCleanup(
        base_path=args.path,
        max_jobs=args.max_jobs,
        dry_run=args.dry_run
    )

    stats = cleaner.run()

    # Return exit code based on success
    if stats['folders_scanned'] > 0:
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())