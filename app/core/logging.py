"""Centralized logging configuration."""

import logging
import logging.config
import logging.handlers
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.core.config import settings

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
log_file = LOGS_DIR / "app.log"
error_log_file = LOGS_DIR / "error.log"


def setup_logging() -> None:
    """Configure application logging with both console and file handlers."""
    
    # Define log format
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    json_format = "%(asctime)s %(name)s %(levelname)s %(message)s"
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console Handler (for development/stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler (JSON format for production parsing)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = jsonlogger.JsonFormatter(json_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error File Handler (JSON format)
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = jsonlogger.JsonFormatter(json_format)
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized - {settings.PROJECT_NAME} v{settings.VERSION}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
