"""
Structured logging system with correlation IDs.

This module provides a comprehensive logging system with structured output,
correlation ID tracking, and integration with monitoring systems.
"""

import json
import logging
import logging.handlers
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pathlib import Path
import contextvars

from core.interfaces import ILogger
from core.exceptions import ConfigurationError


# Context variable for correlation ID
correlation_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id', default=None
)


class CorrelationIDFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record."""
        correlation_id = correlation_id_context.get()
        record.correlation_id = correlation_id or "N/A"
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger_name: bool = True,
        include_correlation_id: bool = True,
        extra_fields: Optional[Dict[str, str]] = None
    ):
        """Initialize JSON formatter.
        
        Args:
            include_timestamp: Include timestamp in output
            include_level: Include log level in output
            include_logger_name: Include logger name in output
            include_correlation_id: Include correlation ID in output
            extra_fields: Additional fields to include
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger_name = include_logger_name
        self.include_correlation_id = include_correlation_id
        self.extra_fields = extra_fields or {}
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "message": record.getMessage()
        }
        
        # Add standard fields
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        if self.include_level:
            log_entry["level"] = record.levelname
        
        if self.include_logger_name:
            log_entry["logger"] = record.name
        
        if self.include_correlation_id and hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from formatter config
        log_entry.update(self.extra_fields)
        
        # Add any extra fields from the log record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'message', 'exc_info', 'exc_text',
                'stack_info', 'correlation_id'
            } and not key.startswith('_'):
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""
    
    def __init__(
        self,
        include_correlation_id: bool = True,
        extra_fields: Optional[Dict[str, str]] = None
    ):
        """Initialize text formatter."""
        format_parts = [
            "%(asctime)s",
            "%(levelname)-8s",
            "%(name)s"
        ]
        
        if include_correlation_id:
            format_parts.append("%(correlation_id)s")
        
        format_parts.append("%(message)s")
        
        format_string = " - ".join(format_parts)
        
        super().__init__(
            fmt=format_string,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.extra_fields = extra_fields or {}


class StructuredLogger(ILogger):
    """Structured logger implementation with correlation ID support."""
    
    def __init__(
        self,
        name: str,
        level: str = "INFO",
        format_type: str = "json",
        log_file: Optional[str] = None,
        max_size: str = "10MB",
        backup_count: int = 5,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger_name: bool = True,
        include_correlation_id: bool = True,
        extra_fields: Optional[Dict[str, str]] = None
    ):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Format type (json, text)
            log_file: Optional log file path
            max_size: Maximum log file size
            backup_count: Number of backup files to keep
            include_timestamp: Include timestamp in logs
            include_level: Include log level in logs
            include_logger_name: Include logger name in logs
            include_correlation_id: Include correlation ID in logs
            extra_fields: Additional fields to include in all logs
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add correlation ID filter
        correlation_filter = CorrelationIDFilter()
        
        # Create formatter
        if format_type.lower() == "json":
            formatter = JSONFormatter(
                include_timestamp=include_timestamp,
                include_level=include_level,
                include_logger_name=include_logger_name,
                include_correlation_id=include_correlation_id,
                extra_fields=extra_fields
            )
        else:
            formatter = TextFormatter(
                include_correlation_id=include_correlation_id,
                extra_fields=extra_fields
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(correlation_filter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            self._add_file_handler(
                log_file, formatter, correlation_filter, max_size, backup_count
            )
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _add_file_handler(
        self,
        log_file: str,
        formatter: logging.Formatter,
        correlation_filter: CorrelationIDFilter,
        max_size: str,
        backup_count: int
    ) -> None:
        """Add rotating file handler."""
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max_size
        size_bytes = self._parse_size(max_size)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=size_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(correlation_filter)
        self.logger.addHandler(file_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # Assume bytes
            return int(size_str)
    
    def log(
        self,
        level: str,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a message with optional correlation ID and metadata."""
        # Set correlation ID in context if provided
        if correlation_id:
            correlation_id_context.set(correlation_id)
        
        # Get log level
        log_level = getattr(logging, level.upper())
        
        # Log with extra fields
        self.logger.log(log_level, message, extra=kwargs)
    
    def info(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log an info message."""
        self.log("INFO", message, correlation_id, **kwargs)
    
    def warning(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a warning message."""
        self.log("WARNING", message, correlation_id, **kwargs)
    
    def error(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log an error message."""
        self.log("ERROR", message, correlation_id, **kwargs)
    
    def debug(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a debug message."""
        self.log("DEBUG", message, correlation_id, **kwargs)
    
    def critical(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a critical message."""
        self.log("CRITICAL", message, correlation_id, **kwargs)
    
    def exception(
        self,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log an exception with traceback."""
        if correlation_id:
            correlation_id_context.set(correlation_id)
        
        self.logger.exception(message, extra=kwargs)


class LoggerFactory:
    """Factory for creating loggers with consistent configuration."""
    
    @staticmethod
    def create_logger(
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> StructuredLogger:
        """Create a logger with the given configuration."""
        if config is None:
            config = {}
        
        return StructuredLogger(
            name=name,
            level=config.get("level", "INFO"),
            format_type=config.get("format", "json"),
            log_file=config.get("file"),
            max_size=config.get("max_size", "10MB"),
            backup_count=config.get("backup_count", 5),
            include_timestamp=config.get("include_timestamp", True),
            include_level=config.get("include_level", True),
            include_logger_name=config.get("include_logger_name", True),
            include_correlation_id=config.get("include_correlation_id", True),
            extra_fields=config.get("extra_fields")
        )


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from the current context."""
    return correlation_id_context.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def with_correlation_id(correlation_id: Optional[str] = None):
    """Decorator to set correlation ID for a function."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            cid = correlation_id or generate_correlation_id()
            correlation_id_context.set(cid)
            try:
                return await func(*args, **kwargs)
            finally:
                correlation_id_context.set(None)
        
        def sync_wrapper(*args, **kwargs):
            cid = correlation_id or generate_correlation_id()
            correlation_id_context.set(cid)
            try:
                return func(*args, **kwargs)
            finally:
                correlation_id_context.set(None)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
