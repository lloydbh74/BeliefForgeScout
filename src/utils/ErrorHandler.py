"""
Comprehensive error handling and logging utilities
Centralizes error management across the application
"""
import logging
import traceback
import sys
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime
from functools import wraps
from enum import Enum
import json
from pathlib import Path

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better organization"""
    DATABASE = "database"
    API = "api"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    EXTERNAL_SERVICE = "external_service"
    CACHE = "cache"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"

class DashboardError(Exception):
    """Base exception class for dashboard application"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: str = None,
        details: Dict[str, Any] = None,
        cause: Exception = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or "An error occurred in the application"
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "user_message": self.user_message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
            "timestamp": self.timestamp.isoformat(),
            "traceback": traceback.format_exc() if self.cause else None
        }

class DatabaseError(DashboardError):
    """Database-related errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None, cause: Exception = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            user_message="Database operation failed. Please try again later.",
            details=details,
            cause=cause
        )

class ValidationError(DashboardError):
    """Input validation errors"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            user_message=f"Invalid input: {message}",
            details={"field": field, "value": value}
        )

class AuthenticationError(DashboardError):
    """Authentication/authorization errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            user_message="Please log in to continue."
        )

class CacheError(DashboardError):
    """Cache-related errors"""
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            message=message,
            category=ErrorCategory.CACHE,
            severity=ErrorSeverity.LOW,
            user_message="Temporary cache issue. The operation will continue normally.",
            details={"operation": operation}
        )

class ExternalServiceError(DashboardError):
    """External service integration errors"""
    def __init__(self, service: str, message: str, cause: Exception = None):
        super().__init__(
            message=f"{service} error: {message}",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            user_message=f"External service {service} is temporarily unavailable.",
            details={"service": service},
            cause=cause
        )

class ErrorHandler:
    """Centralized error handling and logging"""

    def __init__(self, log_file: str = None, log_level: str = "INFO"):
        self.setup_logging(log_file, log_level)
        self.error_stats = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "recent_errors": []
        }

    def setup_logging(self, log_file: str = None, log_level: str = "INFO"):
        """Setup comprehensive logging configuration"""
        # Create logs directory if it doesn't exist
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                *([logging.FileHandler(log_file)] if log_file else [])
            ]
        )

        # Create specific loggers
        self.app_logger = logging.getLogger("dashboard_app")
        self.error_logger = logging.getLogger("dashboard_errors")
        self.performance_logger = logging.getLogger("dashboard_performance")
        self.security_logger = logging.getLogger("dashboard_security")

        # Set up error logger to log to separate file if specified
        if log_file:
            error_log_file = str(Path(log_file).parent / "errors.log")
            error_handler = logging.FileHandler(error_log_file)
            error_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.error_logger.addHandler(error_handler)
            self.error_logger.setLevel(logging.ERROR)

    def handle_error(
        self,
        error: Union[Exception, DashboardError],
        context: Dict[str, Any] = None,
        user_id: str = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Handle and log an error with context
        Returns formatted error response
        """
        # Convert to DashboardError if it's a regular exception
        if not isinstance(error, DashboardError):
            dashboard_error = DashboardError(
                message=str(error),
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                cause=error
            )
        else:
            dashboard_error = error

        # Add context
        if context:
            dashboard_error.details.update(context)

        # Log the error
        self.log_error(dashboard_error, user_id, request_id)

        # Update statistics
        self._update_error_stats(dashboard_error)

        # Return error response
        return self.format_error_response(dashboard_error)

    def log_error(
        self,
        error: DashboardError,
        user_id: str = None,
        request_id: str = None
    ):
        """Log error with appropriate level based on severity"""
        log_data = {
            "error": error.to_dict(),
            "user_id": user_id,
            "request_id": request_id
        }

        # Log to error logger
        if error.severity == ErrorSeverity.CRITICAL:
            self.error_logger.critical(f"CRITICAL ERROR: {json.dumps(log_data, default=str)}")
        elif error.severity == ErrorSeverity.HIGH:
            self.error_logger.error(f"HIGH SEVERITY ERROR: {json.dumps(log_data, default=str)}")
        elif error.severity == ErrorSeverity.MEDIUM:
            self.error_logger.warning(f"MEDIUM SEVERITY ERROR: {json.dumps(log_data, default=str)}")
        else:
            self.error_logger.info(f"LOW SEVERITY ERROR: {json.dumps(log_data, default=str)}")

        # Log to category-specific logger if applicable
        if error.category == ErrorCategory.SECURITY:
            self.security_logger.warning(f"Security error: {json.dumps(log_data, default=str)}")

    def format_error_response(self, error: DashboardError) -> Dict[str, Any]:
        """Format error for API response"""
        response = {
            "success": False,
            "error": {
                "message": error.user_message,
                "category": error.category.value,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat()
            }
        }

        # Include technical details in development mode
        if self.is_development_mode():
            response["error"]["technical_message"] = error.message
            response["error"]["details"] = error.details

        return response

    def _update_error_stats(self, error: DashboardError):
        """Update error statistics"""
        self.error_stats["total_errors"] += 1

        # Update category stats
        category = error.category.value
        self.error_stats["by_category"][category] = self.error_stats["by_category"].get(category, 0) + 1

        # Update severity stats
        severity = error.severity.value
        self.error_stats["by_severity"][severity] = self.error_stats["by_severity"].get(severity, 0) + 1

        # Add to recent errors (keep last 100)
        self.error_stats["recent_errors"].append({
            "timestamp": error.timestamp.isoformat(),
            "category": category,
            "severity": severity,
            "message": error.message
        })

        if len(self.error_stats["recent_errors"]) > 100:
            self.error_stats["recent_errors"] = self.error_stats["recent_errors"][-100:]

    def is_development_mode(self) -> bool:
        """Check if running in development mode"""
        import os
        return os.getenv("ENVIRONMENT", "development").lower() == "development"

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            **self.error_stats,
            "last_updated": datetime.utcnow().isoformat()
        }

    def reset_error_stats(self):
        """Reset error statistics"""
        self.error_stats = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "recent_errors": []
        }

def handle_exceptions(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: str = None,
    reraise: bool = True
):
    """
    Decorator for handling exceptions in functions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DashboardError:
                # Re-raise DashboardErrors as-is
                if reraise:
                    raise
                return None
            except Exception as e:
                # Convert to DashboardError
                dashboard_error = DashboardError(
                    message=f"Error in {func.__name__}: {str(e)}",
                    category=category,
                    severity=severity,
                    user_message=user_message or "An error occurred while processing your request",
                    cause=e
                )

                if reraise:
                    raise dashboard_error
                else:
                    # Log and return None
                    error_handler.log_error(dashboard_error)
                    return None

        return wrapper
    return decorator

def log_performance(func: Callable) -> Callable:
    """
    Decorator for logging function performance
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.utcnow()
        try:
            result = func(*args, **kwargs)
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            error_handler.performance_logger.info(
                f"Performance: {func.__name__} completed in {duration:.3f}s"
            )

            return result
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            error_handler.performance_logger.error(
                f"Performance: {func.__name__} failed after {duration:.3f}s - {str(e)}"
            )
            raise

    return wrapper

# Global error handler instance
error_handler = ErrorHandler()

# Convenience functions
def log_error(error: Union[Exception, DashboardError], **kwargs):
    """Log an error using the global error handler"""
    return error_handler.handle_error(error, **kwargs)

def handle_validation_error(message: str, field: str = None, value: Any = None):
    """Create and handle a validation error"""
    error = ValidationError(message, field, value)
    return error_handler.handle_error(error)

def handle_database_error(message: str, cause: Exception = None, **kwargs):
    """Create and handle a database error"""
    error = DatabaseError(message, kwargs, cause)
    return error_handler.handle_error(error)

def handle_auth_error(message: str = "Authentication failed"):
    """Create and handle an authentication error"""
    error = AuthenticationError(message)
    return error_handler.handle_error(error)