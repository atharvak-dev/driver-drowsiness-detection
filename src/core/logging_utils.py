"""
Production Logging System
Structured logging with rotation, filtering, and telemetry.
"""
import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields
        if hasattr(record, "custom_fields"):
            log_data.update(record.custom_fields)
        
        return json.dumps(log_data)


def setup_logging(
    name: str = "drowsiness_detection",
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_json: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup production logging system.
    
    Args:
        name: Logger name
        log_file: Path to log file (None for no file logging)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Enable console output
        enable_json: Use JSON formatting
        max_bytes: Max size per log file
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Setup formatters
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")
    
    return logger


class DetectionLogger:
    """Logger for detection events with structured data."""
    
    def __init__(self, log_file: str = "data/detections.jsonl"):
        """
        Initialize detection logger.
        
        Args:
            log_file: Path to JSONL file for detection logs
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log a detection event.
        
        Args:
            event_data: Event data dictionary
        """
        try:
            with open(self.log_file, 'a') as f:
                json.dump(event_data, f)
                f.write('\n')
        except Exception as e:
            logging.error(f"Failed to log detection event: {e}")
    
    def read_events(self, limit: Optional[int] = None) -> list:
        """
        Read detection events from log.
        
        Args:
            limit: Maximum number of events to read (None for all)
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            if not self.log_file.exists():
                return events
            
            with open(self.log_file, 'r') as f:
                for i, line in enumerate(f):
                    if limit and i >= limit:
                        break
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logging.error(f"Failed to read detection events: {e}")
        
        return events
    
    def clear(self) -> None:
        """Clear detection log file."""
        if self.log_file.exists():
            self.log_file.unlink()


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger
