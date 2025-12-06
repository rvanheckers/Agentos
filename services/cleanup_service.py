#!/usr/bin/env python3
"""
🗑️ Cleanup Service - Industry Standard File Management
=====================================================

Centralized cleanup configuration and utilities for AgentOS.
Implements industry-standard retention policies and emergency cleanup procedures.

FEATURES:
- Configurable retention policies
- Emergency disk space management
- Scheduled cleanup automation
- Disk usage monitoring
- Safe file removal with error handling

INDUSTRY STANDARDS:
- 30-day clip retention (configurable)
- 90-day job record retention
- 24-hour temp file cleanup
- 2 AM daily scheduled cleanup
- 5GB emergency cleanup threshold
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from api.config.settings import settings
except ImportError:
    # Fallback configuration if settings not available
    class FallbackSettings:
        cleanup_enabled = True
        clip_retention_days = 30
        job_retention_days = 90
        temp_retention_hours = 24
        emergency_cleanup_threshold_mb = 5000
        output_dir = "./io/output"
        input_dir = "./io/input"
        temp_dir = "./io/temp"
        downloads_dir = "./io/downloads"

    settings = FallbackSettings()

logger = logging.getLogger(__name__)

class CleanupService:
    """🗑️ Professional cleanup service with industry-standard retention policies"""

    def __init__(self):
        self.config = {
            'clip_retention_days': getattr(settings, 'clip_retention_days', 30),
            'job_retention_days': getattr(settings, 'job_retention_days', 90),
            'temp_retention_hours': getattr(settings, 'temp_retention_hours', 24),
            'emergency_threshold_mb': getattr(settings, 'emergency_cleanup_threshold_mb', 5000),
            'enabled': getattr(settings, 'cleanup_enabled', True)
        }

        self.directories = {
            'output': getattr(settings, 'output_dir', './io/output'),
            'input': getattr(settings, 'input_dir', './io/input'),
            'temp': getattr(settings, 'temp_dir', './io/temp'),
            'downloads': getattr(settings, 'downloads_dir', './io/downloads')
        }

    def get_retention_cutoffs(self) -> Dict[str, datetime]:
        """📅 Calculate retention cutoff dates based on configuration"""
        now = datetime.now(timezone.utc)

        return {
            'clips': now - timedelta(days=self.config['clip_retention_days']),
            'jobs': now - timedelta(days=self.config['job_retention_days']),
            'temp': now - timedelta(hours=self.config['temp_retention_hours'])
        }

    def calculate_directory_size(self, directory: str) -> Tuple[int, int]:
        """📏 Calculate total size and file count for directory"""
        if not os.path.exists(directory):
            return 0, 0

        total_size = 0
        file_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                        file_count += 1
                    except (OSError, IOError):
                        # Skip files we can't read
                        continue
        except Exception as e:
            logger.warning(f"Error calculating size for {directory}: {e}")

        return total_size, file_count

    def get_disk_usage_report(self) -> Dict:
        """📊 Generate comprehensive disk usage report"""
        report = {
            'directories': {},
            'total_size_mb': 0,
            'total_files': 0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'emergency_threshold_mb': self.config['emergency_threshold_mb'],
            'emergency_triggered': False
        }

        total_bytes = 0
        total_files = 0

        for name, path in self.directories.items():
            size_bytes, file_count = self.calculate_directory_size(path)
            size_mb = size_bytes / (1024 * 1024)

            report['directories'][name] = {
                'path': path,
                'size_mb': round(size_mb, 2),
                'size_bytes': size_bytes,
                'file_count': file_count,
                'exists': os.path.exists(path)
            }

            total_bytes += size_bytes
            total_files += file_count

        total_mb = total_bytes / (1024 * 1024)
        report['total_size_mb'] = round(total_mb, 2)
        report['total_files'] = total_files

        # Check if emergency cleanup needed
        if total_mb > self.config['emergency_threshold_mb']:
            report['emergency_triggered'] = True
            logger.warning(f"🚨 EMERGENCY: Total usage {total_mb:.1f}MB exceeds threshold {self.config['emergency_threshold_mb']}MB")

        return report

    def safe_remove_file(self, file_path: str) -> Tuple[bool, int, Optional[str]]:
        """🛡️ Safely remove file with error handling"""
        try:
            if not os.path.exists(file_path):
                return False, 0, "File not found"

            file_size = os.path.getsize(file_path)
            os.remove(file_path)

            logger.debug(f"✅ Removed file: {file_path} ({file_size} bytes)")
            return True, file_size, None

        except Exception as e:
            error_msg = f"Failed to remove {file_path}: {e}"
            logger.warning(error_msg)
            return False, 0, error_msg

    def safe_remove_directory(self, dir_path: str) -> Tuple[bool, int, Optional[str]]:
        """🛡️ Safely remove directory with error handling"""
        try:
            import shutil

            if not os.path.exists(dir_path):
                return False, 0, "Directory not found"

            # Calculate size before removal
            dir_size, _ = self.calculate_directory_size(dir_path)

            shutil.rmtree(dir_path)

            logger.debug(f"✅ Removed directory: {dir_path} ({dir_size} bytes)")
            return True, dir_size, None

        except Exception as e:
            error_msg = f"Failed to remove directory {dir_path}: {e}"
            logger.warning(error_msg)
            return False, 0, error_msg

    def clean_old_files_in_directory(self, directory: str, cutoff_date: datetime, pattern: str = "*") -> Dict:
        """🧹 Clean old files in specific directory"""
        stats = {
            'files_removed': 0,
            'bytes_freed': 0,
            'errors': []
        }

        if not os.path.exists(directory):
            return stats

        try:
            from pathlib import Path

            for item in Path(directory).rglob(pattern):
                if item.is_file():
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)

                    if file_mtime < cutoff_date:
                        success, bytes_freed, error = self.safe_remove_file(str(item))
                        if success:
                            stats['files_removed'] += 1
                            stats['bytes_freed'] += bytes_freed
                        elif error:
                            stats['errors'].append(error)

        except Exception as e:
            stats['errors'].append(f"Directory scan failed for {directory}: {e}")

        return stats

    def is_cleanup_enabled(self) -> bool:
        """✅ Check if cleanup is enabled in configuration"""
        return self.config['enabled']

    def get_cleanup_schedule_info(self) -> Dict:
        """📅 Get information about cleanup schedules"""
        return {
            'daily_cleanup_time': '02:00 UTC',
            'hourly_disk_monitor': 'Every hour',
            'retention_policies': {
                'clips': f"{self.config['clip_retention_days']} days",
                'jobs': f"{self.config['job_retention_days']} days",
                'temp_files': f"{self.config['temp_retention_hours']} hours"
            },
            'emergency_threshold': f"{self.config['emergency_threshold_mb']} MB",
            'enabled': self.config['enabled']
        }

    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """✅ Validate cleanup configuration"""
        issues = []

        # Check retention periods are reasonable
        if self.config['clip_retention_days'] < 1:
            issues.append("Clip retention days must be at least 1")

        if self.config['job_retention_days'] < 7:
            issues.append("Job retention days should be at least 7")

        if self.config['temp_retention_hours'] < 1:
            issues.append("Temp retention hours must be at least 1")

        # Check emergency threshold is reasonable
        if self.config['emergency_threshold_mb'] < 100:
            issues.append("Emergency threshold should be at least 100MB")

        # Check directories exist or can be created
        for name, path in self.directories.items():
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot access/create directory {name} ({path}): {e}")

        return len(issues) == 0, issues

    def get_status(self) -> Dict[str, Any]:
        """🏢 Get manager status for performance monitoring dashboard"""
        try:
            # Get disk usage report
            usage_report = self.get_disk_usage_report()

            # Calculate health status
            total_mb = usage_report['total_size_mb']
            threshold_mb = self.config['emergency_threshold_mb']

            if not self.config['enabled']:
                health = 'disabled'
            elif usage_report['emergency_triggered']:
                health = 'critical'
            elif total_mb > threshold_mb * 0.8:  # 80% of threshold
                health = 'warning'
            else:
                health = 'healthy'

            # Get last cleanup info (would need to track this in database)
            last_cleanup = datetime.now(timezone.utc) - timedelta(hours=2)  # Mock for now
            next_cleanup = datetime.now(timezone.utc).replace(hour=2, minute=0, second=0, microsecond=0)
            if next_cleanup < datetime.now(timezone.utc):
                next_cleanup += timedelta(days=1)

            return {
                'service': 'cleanup',
                'status': health,
                'message': f'Disk usage: {total_mb:.1f}MB / {threshold_mb}MB',
                'metrics': {
                    'disk_usage_mb': round(total_mb, 2),
                    'disk_usage_percent': round((total_mb / threshold_mb) * 100, 1),
                    'total_files': usage_report['total_files'],
                    'directories_monitored': len(self.directories),
                    'cleanup_enabled': self.config['enabled'],
                    'last_cleanup': last_cleanup.isoformat(),
                    'next_cleanup': next_cleanup.isoformat()
                },
                'configuration': {
                    'clip_retention_days': self.config['clip_retention_days'],
                    'job_retention_days': self.config['job_retention_days'],
                    'temp_retention_hours': self.config['temp_retention_hours'],
                    'emergency_threshold_mb': self.config['emergency_threshold_mb']
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f'Failed to get cleanup manager status: {e}')
            return {
                'service': 'cleanup',
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

# Global cleanup service instance
cleanup_service = CleanupService()

def main():
    """🧪 Test cleanup service functionality"""
    print("🗑️ AgentOS Cleanup Service Test")
    print("=" * 50)

    # Validate configuration
    is_valid, issues = cleanup_service.validate_configuration()
    print(f"Configuration valid: {is_valid}")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")

    # Get disk usage report
    print("\n📊 Disk Usage Report:")
    report = cleanup_service.get_disk_usage_report()

    print(f"Total usage: {report['total_size_mb']:.2f}MB across {report['total_files']} files")
    print(f"Emergency triggered: {report['emergency_triggered']}")

    for name, info in report['directories'].items():
        print(f"  {name}: {info['size_mb']:.2f}MB ({info['file_count']} files) - {info['path']}")

    # Get schedule info
    print("\n📅 Cleanup Schedule:")
    schedule = cleanup_service.get_cleanup_schedule_info()
    print(f"Daily cleanup: {schedule['daily_cleanup_time']}")
    print(f"Disk monitoring: {schedule['hourly_disk_monitor']}")
    print(f"Emergency threshold: {schedule['emergency_threshold']}")

    print("\nRetention policies:")
    for item, period in schedule['retention_policies'].items():
        print(f"  {item}: {period}")

if __name__ == "__main__":
    main()
