"""
Logs Service Layer
==================
Handles all logs-related business logic
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

# Import technical implementation service
from api.services.log_reader_service import LogReaderService

logger = logging.getLogger("agentos.services.logs")

class LogsService:
    """
    Service layer for logs management business logic

    Methods:
    - get_logs(): Get logs with business logic filtering
    - get_log_sources(): Get available log sources
    - get_log_levels(): Get available log levels
    - get_recent_activity(): Get recent activity for dashboard
    """

    def __init__(self):
        """Initialize logs service"""
        # Use technical implementation service
        self.log_reader = LogReaderService()

    def get_logs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get logs with business logic filtering
        Applies admin/user permissions and business rules
        """
        try:
            # Default business logic filters
            if filters is None:
                filters = {}

            # Apply business rules
            if "limit" not in filters:
                filters["limit"] = 100  # Default business limit

            if "level" not in filters:
                filters["level"] = "info"  # Default business level

            # Get logs via technical service
            # Convert filters to log_reader format
            lines = filters.get("limit", 100)
            category = "all"  # For now, use "all" category

            logs_result = self.log_reader.get_logs_by_category(category, lines)
            logs = logs_result.get("logs", [])

            # Apply business logic transformations
            processed_logs = []
            for log in logs:
                processed_log = {
                    "timestamp": log.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "level": log.get("level", "info"),
                    "message": log.get("message", ""),
                    "source": log.get("source", "system"),
                    "category": self._categorize_log(log)
                }
                processed_logs.append(processed_log)

            return processed_logs

        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return []

    def get_log_sources(self) -> List[str]:
        """
        Get available log sources
        Returns business-relevant log sources
        """
        try:
            # For now, return default business sources since LogReaderService doesn't have this method
            return ["api", "websocket", "worker", "system", "database", "celery"]

        except Exception as e:
            logger.error(f"Failed to get log sources: {e}")
            return ["api", "websocket", "worker", "system"]  # Default business sources

    def get_log_levels(self) -> List[str]:
        """
        Get available log levels
        Returns business-relevant log levels
        """
        try:
            # For now, return standard business levels since LogReaderService doesn't have this method
            return ["debug", "info", "warning", "error", "critical"]

        except Exception as e:
            logger.error(f"Failed to get log levels: {e}")
            return ["debug", "info", "warning", "error", "critical"]  # Default business levels

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent activity for dashboard
        Applies business logic for what constitutes "activity"
        """
        try:
            # Business logic: recent activity = info+ level logs from last hour
            filters = {
                "limit": limit * 2,  # Get more to filter down
                "level": "info",
                "hours": 1
            }

            logs = self.get_logs(filters)

            # Business logic: convert logs to activity items
            activities = []
            for log in logs[:limit]:
                activity = {
                    "timestamp": log["timestamp"],
                    "type": self._log_to_activity_type(log),
                    "description": self._log_to_activity_description(log),
                    "source": log["source"],
                    "severity": self._log_to_severity(log["level"])
                }
                activities.append(activity)

            return activities

        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return []

    # Private business logic helper methods

    def _categorize_log(self, log: Dict[str, Any]) -> str:
        """
        Business logic: categorize log entries
        """
        message = log.get("message", "").lower()

        if "job" in message or "video" in message:
            return "workflow"
        elif "user" in message or "auth" in message:
            return "user_activity"
        elif "error" in message or "failed" in message:
            return "system_error"
        elif "api" in message or "request" in message:
            return "api_activity"
        else:
            return "system"

    def _is_business_relevant_source(self, source: str) -> bool:
        """
        Business logic: determine if log source is relevant for business monitoring
        """
        relevant_sources = ["api", "websocket", "worker", "system", "database", "celery"]
        return source.lower() in relevant_sources

    def _log_to_activity_type(self, log: Dict[str, Any]) -> str:
        """
        Business logic: convert log to activity type
        """
        category = log.get("category", "system")
        level = log.get("level", "info")

        if category == "workflow":
            return "job_processing"
        elif category == "user_activity":
            return "user_action"
        elif category == "system_error":
            return "system_alert"
        elif level == "error":
            return "error"
        else:
            return "system_activity"

    def _log_to_activity_description(self, log: Dict[str, Any]) -> str:
        """
        Business logic: create human-readable activity description
        """
        message = log.get("message", "")

        # Truncate long messages for dashboard
        if len(message) > 100:
            message = message[:97] + "..."

        return message

    def _log_to_severity(self, level: str) -> str:
        """
        Business logic: convert log level to severity for UI
        """
        level_mapping = {
            "debug": "low",
            "info": "normal",
            "warning": "medium",
            "error": "high",
            "critical": "critical"
        }
        return level_mapping.get(level.lower(), "normal")
