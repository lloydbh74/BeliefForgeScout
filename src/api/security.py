import os
import secrets
import bcrypt
import bleach
from typing import Optional
from pydantic import validator
import re

def generate_secure_secret(length: int = 64) -> str:
    """Generate a cryptographically secure secret"""
    return secrets.token_urlsafe(length)

def validate_jwt_secret() -> str:
    """Validate and return JWT secret"""
    jwt_secret = os.getenv("JWT_SECRET")

    if not jwt_secret:
        raise ValueError(
            "JWT_SECRET environment variable is required. "
            f"Generate one with: {generate_secure_secret()}"
        )

    if len(jwt_secret) < 32:
        raise ValueError(
            "JWT_SECRET must be at least 32 characters long for security"
        )

    return jwt_secret

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

class SecurityValidator:
    """Security validation utilities"""

    @staticmethod
    def sanitize_html(content: str, allowed_tags: list = None) -> str:
        """Sanitize HTML content to prevent XSS"""
        if allowed_tags is None:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u']

        return bleach.clean(
            content,
            tags=allowed_tags,
            attributes={},
            strip=True
        )

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text content"""
        if not text:
            return ""

        # Remove potentially dangerous characters
        # Allow only printable ASCII and basic Unicode
        sanitized = re.sub(r'[^\w\s\-.,!?@#%\*\+\/=():;\'"&]', '', text)

        # Limit length to prevent buffer overflow
        return sanitized[:10000]

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) and len(email) <= 254

    @staticmethod
    def validate_json_content(content: str) -> bool:
        """Validate that JSON content doesn't contain malicious patterns"""
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                    # JavaScript URLs
            r'on\w+\s*=',                     # Event handlers
            r'<iframe[^>]*>',                 # Iframes
            r'<object[^>]*>',                 # Objects
            r'<embed[^>]*>',                   # Embeds
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return False

        return True

class SecureInput:
    """Secure input validation using Pydantic"""

    @staticmethod
    def validate_reply_text(text: str) -> str:
        """Validate and sanitize reply text"""
        if not text:
            raise ValueError("Reply text cannot be empty")

        if len(text) > 280:
            raise ValueError("Reply text cannot exceed 280 characters")

        # Check for potential injection patterns
        dangerous_patterns = [
            '<script', 'javascript:', 'onload=', 'onerror=',
            'onclick=', 'alert(', 'confirm(', 'prompt('
        ]

        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if pattern in text_lower:
                raise ValueError(f"Reply text contains potentially unsafe content: {pattern}")

        return SecurityValidator.sanitize_text(text)

    @staticmethod
    def validate_tweet_text(text: str) -> str:
        """Validate and sanitize tweet text"""
        if not text:
            raise ValueError("Tweet text cannot be empty")

        if len(text) > 5000:  # Reasonable limit for storage
            raise ValueError("Tweet text is too long")

        return SecurityValidator.sanitize_text(text)

class RateLimiter:
    """In-memory rate limiting (for development)"""

    def __init__(self):
        self.attempts = {}
        self.lockouts = {}

    def is_rate_limited(self, key: str, max_attempts: int = 5, window_minutes: int = 15) -> tuple[bool, Optional[int]]:
        """Check if a key is rate limited"""
        import time
        from datetime import datetime, timedelta

        now = time.time()

        # Check if currently locked out
        if key in self.lockouts:
            lockout_end = self.lockouts[key]
            if now < lockout_end:
                remaining = int(lockout_end - now)
                return True, remaining
            else:
                # Lockout expired, clean up
                del self.lockouts[key]
                if key in self.attempts:
                    del self.attempts[key]

        # Record attempt
        if key not in self.attempts:
            self.attempts[key] = []

        # Clean old attempts outside the window
        window_start = now - (window_minutes * 60)
        self.attempts[key] = [attempt_time for attempt_time in self.attempts[key]
                             if attempt_time > window_start]

        # Add current attempt
        self.attempts[key].append(now)

        # Check if limit exceeded
        if len(self.attempts[key]) > max_attempts:
            # Apply lockout
            lockout_end = now + (window_minutes * 60)
            self.lockouts[key] = lockout_end
            return True, window_minutes * 60

        return False, None

# Global rate limiter instance
login_rate_limiter = RateLimiter()
api_rate_limiter = RateLimiter()

class SecurityHeaders:
    """Security headers for HTTP responses"""

    @staticmethod
    def get_security_headers() -> dict:
        """Get security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://fonts.gstatic.com; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }

class AuditLogger:
    """Security audit logging"""

    def __init__(self):
        import logging
        import os

        # Ensure logs directory exists
        log_dir = '/app/data/logs'
        os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger('security_audit')
        handler = logging.FileHandler(os.path.join(log_dir, 'security_audit.log'))
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_auth_event(self, event_type: str, email: str, ip_address: str,
                       success: bool, details: Optional[str] = None):
        """Log authentication events"""
        self.logger.info(
            f"AUTH_EVENT: {event_type} | Email: {email} | IP: {ip_address} | "
            f"Success: {success} | Details: {details or 'None'}"
        )

    def log_api_access(self, endpoint: str, method: str, user_email: str,
                      ip_address: str, status_code: int):
        """Log API access events"""
        self.logger.info(
            f"API_ACCESS: {method} {endpoint} | User: {user_email} | "
            f"IP: {ip_address} | Status: {status_code}"
        )

    def log_security_violation(self, violation_type: str, details: str,
                             user_email: Optional[str] = None,
                             ip_address: Optional[str] = None):
        """Log security violations"""
        self.logger.warning(
            f"SECURITY_VIOLATION: {violation_type} | Details: {details} | "
            f"User: {user_email or 'Unknown'} | IP: {ip_address or 'Unknown'}"
        )

# Global audit logger instance
try:
    audit_logger = AuditLogger()
except Exception:
    audit_logger = None  # Fallback if logging fails