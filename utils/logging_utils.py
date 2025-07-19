"""
Logging utilities for Orchestra with structured logging and rotation.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any
import json


def setup_logging(log_level: str = "INFO", log_dir: str = None) -> logging.Logger:
    """
    Set up structured logging with rotation for Orchestra.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory to store log files (defaults to ./logs)
    
    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger("orchestra")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation for persistent logging
    log_file = os.path.join(log_dir, "orchestra.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Structured JSON logs for analysis
    json_log_file = os.path.join(log_dir, "orchestra.jsonl")
    json_handler = logging.handlers.RotatingFileHandler(
        json_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    return logger


class JSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        return json.dumps(log_entry)


class OrchesteraLogger:
    """
    High-level logging interface for Orchestra with structured data support.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_cycle_start(self, work_mode: str, usage_status: str):
        """Log the start of an Orchestra cycle"""
        self.logger.info(
            f"Orchestra cycle started - Mode: {work_mode}, Usage: {usage_status}",
            extra={'extra_data': {
                'event': 'cycle_start',
                'work_mode': work_mode,
                'usage_status': usage_status
            }}
        )
    
    def log_cycle_end(self, work_mode: str, duration: float, status: str, results: Dict[str, Any] = None):
        """Log the end of an Orchestra cycle"""
        extra_data = {
            'event': 'cycle_end',
            'work_mode': work_mode,
            'duration_seconds': duration,
            'status': status
        }
        
        if results:
            extra_data['results_summary'] = {
                'repos_processed': len(results.get('results', {})),
                'total_tasks': sum(
                    len(repo_result.get('tasks', []))
                    for repo_result in results.get('results', {}).values()
                    if isinstance(repo_result, dict)
                )
            }
        
        self.logger.info(
            f"Orchestra cycle completed - Mode: {work_mode}, Duration: {duration:.1f}s, Status: {status}",
            extra={'extra_data': extra_data}
        )
    
    def log_usage_status(self, usage_summary: Dict[str, Any]):
        """Log current usage status"""
        self.logger.info(
            f"Usage status - Tokens: {usage_summary.get('total_tokens', 0)}, "
            f"Requests: {usage_summary.get('requests', 0)}",
            extra={'extra_data': {
                'event': 'usage_status',
                'usage_summary': usage_summary
            }}
        )
    
    def log_repo_processing(self, repo_name: str, mode: str, status: str, error: str = None):
        """Log repository processing events"""
        extra_data = {
            'event': 'repo_processing',
            'repo_name': repo_name,
            'mode': mode,
            'status': status
        }
        
        if error:
            extra_data['error'] = error
            self.logger.error(
                f"Error processing {repo_name} in {mode} mode: {error}",
                extra={'extra_data': extra_data}
            )
        else:
            self.logger.info(
                f"Processing {repo_name} in {mode} mode - Status: {status}",
                extra={'extra_data': extra_data}
            )
    
    def log_github_operation(self, operation: str, repo: str, success: bool, details: str = None):
        """Log GitHub operations"""
        extra_data = {
            'event': 'github_operation',
            'operation': operation,
            'repo': repo,
            'success': success
        }
        
        if details:
            extra_data['details'] = details
        
        level = self.logger.info if success else self.logger.warning
        level(
            f"GitHub {operation} for {repo} - {'Success' if success else 'Failed'}",
            extra={'extra_data': extra_data}
        )
    
    def log_claude_code_call(self, repo: str, task_type: str, success: bool, token_usage: Dict = None):
        """Log Claude Code API calls"""
        extra_data = {
            'event': 'claude_code_call',
            'repo': repo,
            'task_type': task_type,
            'success': success
        }
        
        if token_usage:
            extra_data['token_usage'] = token_usage
        
        level = self.logger.info if success else self.logger.error
        level(
            f"Claude Code call for {repo} ({task_type}) - {'Success' if success else 'Failed'}",
            extra={'extra_data': extra_data}
        )
    
    def log_error(self, error_type: str, message: str, context: Dict[str, Any] = None):
        """Log errors with context"""
        extra_data = {
            'event': 'error',
            'error_type': error_type,
            'context': context or {}
        }
        
        self.logger.error(
            f"{error_type}: {message}",
            extra={'extra_data': extra_data}
        )
    
    def log_debug(self, message: str, context: Dict[str, Any] = None):
        """Log debug information"""
        if context:
            self.logger.debug(message, extra={'extra_data': context})
        else:
            self.logger.debug(message)


# Global logger instance
_orchestra_logger = None


def get_logger() -> OrchesteraLogger:
    """Get the global Orchestra logger instance"""
    global _orchestra_logger
    if _orchestra_logger is None:
        base_logger = setup_logging()
        _orchestra_logger = OrchesteraLogger(base_logger)
    return _orchestra_logger


def configure_logging(log_level: str = "INFO", log_dir: str = None) -> OrchesteraLogger:
    """Configure and return the global Orchestra logger"""
    global _orchestra_logger
    base_logger = setup_logging(log_level, log_dir)
    _orchestra_logger = OrchesteraLogger(base_logger)
    return _orchestra_logger


# Error handling decorator
def log_errors(error_type: str = "unknown"):
    """Decorator to automatically log errors from functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log_error(
                    error_type=error_type,
                    message=str(e),
                    context={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                )
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test logging setup
    logger = configure_logging("DEBUG")
    
    logger.log_cycle_start("workday", "normal")
    logger.log_repo_processing("test-repo", "workday", "completed")
    logger.log_github_operation("pr_list", "test-repo", True, "Found 3 PRs")
    logger.log_usage_status({
        "total_tokens": 15000,
        "requests": 25,
        "timestamp": datetime.now().isoformat()
    })
    logger.log_cycle_end("workday", 45.2, "completed", {"results": {"test-repo": {"tasks": []}}})
    
    print("Logging test completed. Check logs/ directory for output.")