"""Logging utility for the application."""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "CallSummarizer", log_dir: Path = None) -> logging.Logger:
    """Set up and configure the application logger.
    
    Creates a logger with both console and file handlers:
    - Console: Shows INFO level and above with simple format
    - File: Saves DEBUG level and above with detailed format including function names
    
    Args:
        name: Logger name
        log_dir: Directory to save log files. Defaults to ~/CallSummaries/logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture all levels, handlers filter
    
    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Detailed formatter for file logs (includes function name and line number)
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Simple formatter for console output (cleaner, less verbose)
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler - shows INFO and above to user
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler - saves all DEBUG and above for troubleshooting
    if log_dir is None:
        log_dir = Path.home() / "CallSummaries" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create daily log file (one file per day)
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Save everything for debugging
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger

