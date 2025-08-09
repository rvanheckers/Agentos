#!/usr/bin/env python3
"""
Database Logger Mixin - Voor Agent Database Logging
===================================================

Deze module voegt database logging toe aan alle agents.
Elke agent kan deze mixin gebruiken om processing steps te loggen.

Usage in agent:
from agents2.database_logger import DatabaseLoggerMixin

class VideoDownloader(DatabaseLoggerMixin):
    def __init__(self):
        super().__init__()
        self.agent_name = "video_downloader"

    def execute(self, input_data):
        with self.log_execution(input_data.get('job_id'), 1) as logger:
            try:
                result = self.do_work()
                logger.set_output(result)
                return result
            except Exception as e:
                logger.set_error(str(e))
                raise
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any
import json


class DatabaseLoggerMixin:
    """
    Mixin class die database logging toevoegt aan agents
    """

    def __init__(self):
        self.agent_name = getattr(self, 'agent_name', self.__class__.__name__)

    @contextmanager
    def log_execution(self, job_id: str, step_number: int, input_data: Any = None):
        """
        Context manager voor het loggen van agent execution

        Usage:
            with self.log_execution(job_id, 1, input_data) as logger:
                result = do_work()
                logger.set_output(result)
        """
        # Import hier om circular imports te voorkomen
        try:
            from core.database_manager import PostgreSQLManager
            db = PostgreSQLManager()
        except ImportError:
            # Fallback als database niet beschikbaar is
            yield DummyLogger()
            return

        started_at = datetime.utcnow()

        # Start logging in database
        step_id = db.log_processing_step(
            job_id=job_id,
            agent_name=self.agent_name,
            step_number=step_number,
            success=False,  # Start met False
            started_at=started_at,
            completed_at=None,  # Nog niet completed
            input_data=json.dumps(input_data) if input_data else None
        )

        logger = StepLogger(step_id, db)

        try:
            yield logger
            # Als we hier komen zonder exception, was het succesvol
            logger.mark_success()
        except Exception as e:
            # Exception occurred, mark as failed
            logger.mark_failure(str(e))
            raise
        finally:
            # Update completion time
            logger.complete()


class StepLogger:
    """
    Helper class voor het loggen van een specifieke processing step
    """

    def __init__(self, step_id: str, db_manager):
        self.step_id = step_id
        self.db = db_manager
        self.success = False
        self.error_message = None
        self.output_data = None

    def set_output(self, output_data: Any):
        """Set output data voor deze step"""
        self.output_data = json.dumps(output_data) if output_data else None

    def set_error(self, error_message: str):
        """Set error message voor deze step"""
        self.error_message = error_message
        self.success = False

    def mark_success(self):
        """Mark deze step als succesvol"""
        self.success = True
        self.error_message = None

    def mark_failure(self, error_message: str):
        """Mark deze step als gefaald"""
        self.success = False
        self.error_message = error_message

    def complete(self):
        """Complete de step en update database"""
        self.db.update_processing_step(
            step_id=self.step_id,
            success=self.success,
            completed_at=datetime.utcnow(),
            error_message=self.error_message,
            output_data=self.output_data
        )


class DummyLogger:
    """
    Dummy logger voor als database niet beschikbaar is
    """

    def set_output(self, output_data: Any):
        pass

    def set_error(self, error_message: str):
        pass

    def mark_success(self):
        pass

    def mark_failure(self, error_message: str):
        pass

    def complete(self):
        pass


# Helper function voor direct gebruik
def log_agent_step(agent_name: str, job_id: str, step_number: int,
                   input_data: Any = None, output_data: Any = None,
                   success: bool = True, error_message: str = None):
    """
    Direct een processing step loggen zonder context manager

    Voor simpele agents die geen complexe logging nodig hebben
    """
    try:
        from core.database_manager import PostgreSQLManager
        db = PostgreSQLManager()

        db.log_processing_step(
            job_id=job_id,
            agent_name=agent_name,
            step_number=step_number,
            success=success,
            error_message=error_message,
            input_data=json.dumps(input_data) if input_data else None,
            output_data=json.dumps(output_data) if output_data else None,
            duration_seconds=0  # Voor direct logging zonder timing
        )

    except ImportError:
        # Database niet beschikbaar, skip logging
        pass
    except Exception as e:
        # Logging fout, maar niet crashen
        print(f"⚠️ Database logging failed: {e}")


if __name__ == "__main__":
    # Test de database logger
    print("🧪 Testing Database Logger...")

    # Test met dummy data
    log_agent_step(
        agent_name="test_agent",
        job_id="test-job-123",
        step_number=1,
        input_data={"test": "data"},
        output_data={"result": "success"},
        success=True
    )

    print("✅ Database Logger test completed")
