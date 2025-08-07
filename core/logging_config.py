#!/usr/bin/env python3
"""
AgentOS Centralized Logging Configuration
==========================================

Complete logging infrastructure voor AgentOS met:
- Centralized configuration
- File-based logging met rotation
- IO-level logging capabilities
- Multiple log levels en formats
- Environment-specific configuration
- Performance monitoring
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
import threading
import time

class AgentOSLogger:
    """
    Centralized Logger voor AgentOS
    
    Features:
    - Multiple log levels (DEBUG, INFO, WARN, ERROR, IO)
    - File rotation (dagelijks, size-based)
    - Console + file output
    - Structured logging (JSON format)
    - Performance monitoring
    - IO-level request/response logging
    - Component-specific loggers
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern voor centrale logger"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.loggers: Dict[str, logging.Logger] = {}
        self.config = self._load_config()
        self._setup_logging()
        
        # Custom IO log level
        logging.addLevelName(15, "IO")
        def io(self, message, *args, **kws):
            if self.isEnabledFor(15):
                self._log(15, message, args, **kws)
        logging.Logger.io = io
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logging configuration from environment and config file"""
        
        # Default configuration
        default_config = {
            "version": 1,
            "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
            "log_format": "detailed",  # simple, detailed, json
            "enable_file_logging": True,
            "enable_console_logging": True,
            "enable_io_logging": False,  # High-detail request/response logging
            "log_directory": "logs",
            "max_file_size_mb": 10,
            "backup_count": 3,
            "date_rotation": True,
            "performance_logging": True,
            "component_specific_levels": {
                "api_server": "INFO",
                "workers": "INFO", 
                "agents": "WARN",
                "database": "INFO",
                "queue": "INFO",
                "mcp": "INFO",
                "io": "DEBUG"  # Voor IO-level logging
            }
        }
        
        # Try to load from config file
        config_file = Path("logging_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load logging config: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Setup centralized logging infrastructure"""
        
        # Create logs directory
        log_dir = Path(self.config["log_directory"])
        log_dir.mkdir(exist_ok=True)
        
        # Setup formatters
        self.formatters = self._create_formatters()
        
        # Setup handlers
        self.handlers = self._create_handlers()
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config["log_level"]))
        
        # Add handlers to root logger
        for handler in self.handlers.values():
            root_logger.addHandler(handler)
            
        # Setup component-specific loggers
        self._setup_component_loggers()
    
    def _create_formatters(self) -> Dict[str, logging.Formatter]:
        """Create different log formatters"""
        
        formatters = {}
        
        # Simple format
        formatters["simple"] = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        
        # Detailed format  
        formatters["detailed"] = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # JSON format for structured logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'extra_data'):
                    log_entry.update(record.extra_data)
                    
                return json.dumps(log_entry)
        
        formatters["json"] = JSONFormatter()
        
        # IO format for request/response logging
        formatters["io"] = logging.Formatter(
            "%(asctime)s - IO - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S.%f"
        )
        
        return formatters
    
    def _create_handlers(self) -> Dict[str, logging.Handler]:
        """Create log handlers for different outputs"""
        
        handlers = {}
        
        # Console handler
        if self.config["enable_console_logging"]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.formatters[self.config["log_format"]])
            console_handler.setLevel(getattr(logging, self.config["log_level"]))
            handlers["console"] = console_handler
        
        # Main application log file
        if self.config["enable_file_logging"]:
            log_file = Path(self.config["log_directory"]) / "agentos.log"
            
            if self.config["date_rotation"]:
                # Daily rotation
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    log_file,
                    when="midnight",
                    interval=1,
                    backupCount=self.config["backup_count"],
                    encoding="utf-8"
                )
            else:
                # Size-based rotation
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=self.config["max_file_size_mb"] * 1024 * 1024,
                    backupCount=self.config["backup_count"],
                    encoding="utf-8"
                )
            
            file_handler.setFormatter(self.formatters["detailed"])
            file_handler.setLevel(logging.DEBUG)  # File gets everything
            handlers["file"] = file_handler
        
        # Error-only log file
        if self.config["enable_file_logging"]:
            error_file = Path(self.config["log_directory"]) / "errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=3,
                encoding="utf-8"
            )
            error_handler.setFormatter(self.formatters["detailed"])
            error_handler.setLevel(logging.ERROR)
            handlers["error"] = error_handler
        
        # IO-level logging (request/response details)
        if self.config["enable_io_logging"]:
            io_file = Path(self.config["log_directory"]) / "io.log"
            io_handler = logging.handlers.RotatingFileHandler(
                io_file,
                maxBytes=20 * 1024 * 1024,  # 20MB for IO logs
                backupCount=2,
                encoding="utf-8"
            )
            io_handler.setFormatter(self.formatters["io"])
            io_handler.setLevel(15)  # IO level
            handlers["io"] = io_handler
        
        # JSON structured log file
        if self.config["enable_file_logging"]:
            json_file = Path(self.config["log_directory"]) / "structured.jsonl"
            json_handler = logging.handlers.RotatingFileHandler(
                json_file,
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=3,
                encoding="utf-8"
            )
            json_handler.setFormatter(self.formatters["json"])
            json_handler.setLevel(logging.INFO)
            handlers["json"] = json_handler
        
        return handlers
    
    def _setup_component_loggers(self):
        """Setup component-specific loggers met eigen log levels"""
        
        for component, level in self.config["component_specific_levels"].items():
            logger = logging.getLogger(f"agentos.{component}")
            logger.setLevel(getattr(logging, level.upper()))
            self.loggers[component] = logger
    
    def get_logger(self, component: str) -> logging.Logger:
        """Get logger voor specific component"""
        
        if component not in self.loggers:
            logger = logging.getLogger(f"agentos.{component}")
            logger.setLevel(getattr(logging, self.config["log_level"]))
            self.loggers[component] = logger
        
        return self.loggers[component]
    
    def log_io_request(self, method: str, url: str, headers: Dict = None, body: Any = None):
        """Log incoming request details (IO level)"""
        if not self.config["enable_io_logging"]:
            return
            
        io_logger = self.get_logger("io")
        io_data = {
            "type": "REQUEST",
            "method": method,
            "url": url,
            "headers": dict(headers) if headers else {},
            "body_size": len(str(body)) if body else 0
        }
        
        if body and len(str(body)) < 1000:  # Log small bodies completely
            io_data["body"] = body
            
        io_logger.log(15, f"REQUEST {method} {url}", extra={"extra_data": io_data})
    
    def log_io_response(self, status_code: int, response_data: Any = None, duration_ms: float = None):
        """Log outgoing response details (IO level)"""
        if not self.config["enable_io_logging"]:
            return
            
        io_logger = self.get_logger("io") 
        io_data = {
            "type": "RESPONSE",
            "status_code": status_code,
            "response_size": len(str(response_data)) if response_data else 0,
            "duration_ms": duration_ms
        }
        
        if response_data and len(str(response_data)) < 1000:
            io_data["response_data"] = response_data
            
        io_logger.log(15, f"RESPONSE {status_code} ({duration_ms}ms)", extra={"extra_data": io_data})
    
    def log_performance(self, operation: str, duration: float, extra_data: Dict = None):
        """Log performance metrics"""
        if not self.config["performance_logging"]:
            return
            
        perf_logger = self.get_logger("performance")
        perf_data = {
            "operation": operation,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        if extra_data:
            perf_data.update(extra_data)
            
        perf_logger.info(f"PERF: {operation} completed in {duration:.3f}s", extra={"extra_data": perf_data})
    
    def log_agent_execution(self, agent_name: str, input_data: Dict, output_data: Dict = None, 
                          duration: float = None, success: bool = True, error: str = None):
        """Specialized logging voor agent executions"""
        
        agent_logger = self.get_logger("agents")
        
        log_data = {
            "agent": agent_name,
            "success": success,
            "input_size": len(str(input_data)),
            "duration": duration
        }
        
        if output_data:
            log_data["output_size"] = len(str(output_data))
            
        if error:
            log_data["error"] = error
            agent_logger.error(f"Agent {agent_name} failed: {error}", extra={"extra_data": log_data})
        else:
            agent_logger.info(f"Agent {agent_name} completed in {duration:.2f}s", extra={"extra_data": log_data})
    
    def reload_config(self):
        """Reload logging configuration (useful for runtime changes)"""
        self.config = self._load_config()
        
        # Update log levels
        for component, level in self.config["component_specific_levels"].items():
            if component in self.loggers:
                self.loggers[component].setLevel(getattr(logging, level.upper()))

# Global logger instance
logger_instance = AgentOSLogger()

def get_logger(component: str = "general") -> logging.Logger:
    """Convenience function voor getting component logger"""
    return logger_instance.get_logger(component)

def log_io_request(method: str, url: str, headers: Dict = None, body: Any = None):
    """Convenience function voor IO request logging"""
    logger_instance.log_io_request(method, url, headers, body)

def log_io_response(status_code: int, response_data: Any = None, duration_ms: float = None):
    """Convenience function voor IO response logging"""
    logger_instance.log_io_response(status_code, response_data, duration_ms)

def log_performance(operation: str, duration: float, extra_data: Dict = None):
    """Convenience function voor performance logging"""
    logger_instance.log_performance(operation, duration, extra_data)

def log_agent_execution(agent_name: str, input_data: Dict, output_data: Dict = None,
                       duration: float = None, success: bool = True, error: str = None):
    """Convenience function voor agent execution logging"""
    logger_instance.log_agent_execution(agent_name, input_data, output_data, duration, success, error)

# Context managers for timing
class log_timing:
    """Context manager voor automatic performance logging"""
    
    def __init__(self, operation: str, component: str = "performance", extra_data: Dict = None):
        self.operation = operation
        self.component = component
        self.extra_data = extra_data or {}
        self.start_time = None
        self.logger = get_logger(component)
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            log_performance(self.operation, duration, self.extra_data)
            self.logger.info(f"Completed {self.operation} in {duration:.3f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.3f}s: {exc_val}")

# Example usage functions
if __name__ == "__main__":
    # Test the logging system
    logger = get_logger("test")
    
    logger.debug("Debug message")
    logger.info("Info message") 
    logger.warning("Warning message")
    logger.error("Error message")
    logger.log(15, "IO level message")  # Custom IO level
    
    # Test performance logging
    with log_timing("test_operation", "test"):
        time.sleep(0.1)
    
    # Test agent logging
    log_agent_execution(
        "test_agent",
        {"input": "test"},
        {"output": "result"},
        duration=0.5,
        success=True
    )
    
    print("Logging test completed - check logs/ directory")