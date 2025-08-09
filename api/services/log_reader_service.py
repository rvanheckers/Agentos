"""
Log Reader Service - Centraal log management voor AgentOS

Leest en analyseert log bestanden voor admin dashboard monitoring.
Biedt gestructureerde toegang tot verschillende log categorieën.
Parseert zowel plain text als JSON logs voor real-time inzicht.
Gebruikt door system.py routes voor log viewing functionaliteit.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class LogEntry:
    """Structured log entry voor consistent parsing"""
    timestamp: str
    level: str
    component: str
    message: str
    module: Optional[str] = None
    line: Optional[int] = None
    function: Optional[str] = None
    extra_data: Optional[Dict] = None

class LogReaderService:
    """Service voor het lezen en parsen van AgentOS log files"""

    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self._ensure_log_directory()

        # Mapping van categories naar log files
        self.category_files = {
            "all": ["agentos.log", "api.log", "admin.log", "worker.log", "websocket.log"],
            "api": ["api.log", "agentos.log"],
            "workers": ["worker.log", "agentos.log"],
            "admin": ["admin.log", "agentos.log"],
            "websocket": ["websocket.log", "agentos.log"],
            "errors": ["errors.log"],
            "io": ["io.log"],
            "structured": ["structured.jsonl"]
        }

        # Regex patterns voor log parsing
        self.log_patterns = {
            "detailed": re.compile(
                r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
                r"(?P<component>[^-]+) - "
                r"(?P<level>[A-Z]+) - "
                r"(?P<function>[^:]+):(?P<line>\d+) - "
                r"(?P<message>.*)"
            ),
            "simple": re.compile(
                r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
                r"(?P<level>[A-Z]+) - "
                r"(?P<message>.*)"
            ),
            "io": re.compile(
                r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+) - "
                r"IO - "
                r"(?P<component>[^-]+) - "
                r"(?P<message>.*)"
            )
        }

    def _ensure_log_directory(self):
        """Ensure log directory exists"""
        if not self.log_directory.exists():
            self.log_directory.mkdir(parents=True, exist_ok=True)

    def get_logs_by_category(self, category: str = "all", lines: int = 100) -> Dict[str, Any]:
        """
        Get logs by category

        Args:
            category: Log category (all, api, workers, errors, admin, websocket, io, structured)
            lines: Number of lines to return

        Returns:
            Dict with logs, total_lines, category, and source_files
        """

        if category not in self.category_files:
            raise ValueError(f"Unknown category: {category}. Available: {list(self.category_files.keys())}")

        log_files = self.category_files[category]
        all_logs = []
        source_files = []

        for log_file in log_files:
            file_path = self.log_directory / log_file
            if file_path.exists():
                try:
                    file_logs = self._read_log_file(file_path, lines)
                    all_logs.extend(file_logs)
                    source_files.append(log_file)
                except Exception:
                    # Log parsing error - continue with other files
                    continue

        # Sort by timestamp (newest first)
        all_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Limit results
        limited_logs = all_logs[:lines]

        # Convert to dict format
        logs_dict = [self._log_entry_to_dict(log) for log in limited_logs]

        return {
            "logs": logs_dict,
            "total_lines": len(limited_logs),
            "category": category,
            "source_files": source_files
        }

    def get_worker_logs(self, worker_id: str, lines: int = 100) -> Dict[str, Any]:
        """
        Get logs for a specific worker

        Args:
            worker_id: Worker identifier
            lines: Number of lines to return

        Returns:
            Dict with worker logs
        """

        # Get all worker logs
        worker_logs = self.get_logs_by_category("workers", lines * 2)  # Get more to filter

        # Filter for specific worker
        filtered_logs = []
        for log in worker_logs["logs"]:
            if (worker_id in log["message"] or
                worker_id in log.get("component", "") or
                (log.get("extra_data") and worker_id in str(log["extra_data"]))):
                filtered_logs.append(log)

        # Limit results
        limited_logs = filtered_logs[:lines]

        return {
            "worker_id": worker_id,
            "logs": limited_logs,
            "total_lines": len(limited_logs),
            "source_files": ["worker.log", "agentos.log"]
        }

    def _read_log_file(self, file_path: Path, max_lines: int = 100) -> List[LogEntry]:
        """
        Read and parse a log file

        Args:
            file_path: Path to log file
            max_lines: Maximum lines to read

        Returns:
            List of LogEntry objects
        """

        logs = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read from end of file for recent logs
                lines = self._tail_file(f, max_lines)

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Parse based on file type
                    if file_path.name.endswith('.jsonl'):
                        log_entry = self._parse_json_log(line)
                    else:
                        log_entry = self._parse_text_log(line, file_path.name)

                    if log_entry:
                        logs.append(log_entry)

        except Exception:
            # Return empty list if file can't be read
            pass

        return logs

    def _tail_file(self, file_obj, lines: int) -> List[str]:
        """Get last N lines from file efficiently"""

        try:
            # Simple implementation - read all lines and take last N
            all_lines = file_obj.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception:
            return []

    def _parse_json_log(self, line: str) -> Optional[LogEntry]:
        """Parse JSON structured log line"""

        try:
            data = json.loads(line)

            return LogEntry(
                timestamp=data.get("timestamp", ""),
                level=data.get("level", "INFO"),
                component=data.get("logger", "unknown"),
                message=data.get("message", ""),
                module=data.get("module"),
                line=data.get("line"),
                function=data.get("function"),
                extra_data=data.get("extra_data")
            )

        except json.JSONDecodeError:
            return None

    def _parse_text_log(self, line: str, filename: str) -> Optional[LogEntry]:
        """Parse text log line using regex patterns"""

        # Try different patterns based on filename
        if filename.startswith("io."):
            pattern = self.log_patterns["io"]
        else:
            # Try detailed pattern first, then simple
            pattern = self.log_patterns["detailed"]

        match = pattern.match(line)
        if match:
            groups = match.groupdict()

            return LogEntry(
                timestamp=groups.get("timestamp", ""),
                level=groups.get("level", "INFO"),
                component=groups.get("component", "unknown"),
                message=groups.get("message", ""),
                module=None,
                line=int(groups.get("line", 0)) if groups.get("line") else None,
                function=groups.get("function")
            )

        # Try simple pattern if detailed didn't work
        if filename.startswith("io."):
            return None

        simple_match = self.log_patterns["simple"].match(line)
        if simple_match:
            groups = simple_match.groupdict()

            return LogEntry(
                timestamp=groups.get("timestamp", ""),
                level=groups.get("level", "INFO"),
                component="unknown",
                message=groups.get("message", ""),
            )

        # If no pattern matches, create basic entry
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            level="INFO",
            component="unknown",
            message=line
        )

    def _log_entry_to_dict(self, log_entry: LogEntry) -> Dict[str, Any]:
        """Convert LogEntry to dictionary for API response"""

        result = {
            "timestamp": log_entry.timestamp,
            "level": log_entry.level,
            "component": log_entry.component,
            "message": log_entry.message
        }

        if log_entry.module:
            result["module"] = log_entry.module

        if log_entry.line:
            result["line"] = log_entry.line

        if log_entry.function:
            result["function"] = log_entry.function

        if log_entry.extra_data:
            result["extra_data"] = log_entry.extra_data

        return result

    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""

        stats = {
            "total_log_files": 0,
            "file_sizes": {},
            "last_modified": {},
            "available_categories": list(self.category_files.keys())
        }

        for log_file in self.log_directory.glob("*.log*"):
            stats["total_log_files"] += 1
            stats["file_sizes"][log_file.name] = log_file.stat().st_size
            stats["last_modified"][log_file.name] = datetime.fromtimestamp(
                log_file.stat().st_mtime
            ).isoformat()

        return stats

# Global service instance
log_reader_service = LogReaderService()

def get_logs_by_category(category: str = "all", lines: int = 100) -> Dict[str, Any]:
    """Convenience function for getting logs by category"""
    return log_reader_service.get_logs_by_category(category, lines)

def get_worker_logs(worker_id: str, lines: int = 100) -> Dict[str, Any]:
    """Convenience function for getting worker logs"""
    return log_reader_service.get_worker_logs(worker_id, lines)

def get_log_stats() -> Dict[str, Any]:
    """Convenience function for getting log statistics"""
    return log_reader_service.get_log_stats()
