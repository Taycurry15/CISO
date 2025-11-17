"""
Security Middleware for CMMC Platform
======================================
Implements OWASP API Security Top 10 protections and industry best practices.

Features:
- Rate limiting (API1:2023 - Broken Object Level Authorization)
- CORS configuration (API7:2023 - Security Misconfiguration)
- Input sanitization and XSS protection (API8:2023 - Injection)
- Security headers (CSP, HSTS, etc.)
- Request logging and monitoring
- IP-based blocking
"""

import re
import time
import logging
from typing import Callable, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import html
import os

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """
    Token bucket rate limiter with per-endpoint and per-IP tracking.

    Implements sliding window rate limiting to prevent:
    - Brute force attacks
    - DDoS attempts
    - API abuse
    """

    def __init__(self):
        # Store: {ip_address: {endpoint: [(timestamp, tokens)]}}
        self.requests: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self.blocked_ips: Dict[str, datetime] = {}

        # Rate limit configurations (requests per minute)
        self.limits = {
            "/api/v1/auth/login": 5,           # Prevent brute force
            "/api/v1/auth/register": 3,         # Prevent spam accounts
            "/api/v1/auth/refresh": 10,         # Moderate refresh rate
            "/api/v1/evidence/upload": 30,      # Prevent upload abuse
            "/api/v1/ingest/document": 20,      # Prevent ingest abuse
            "default": 100,                      # Default for other endpoints
        }

        # Block duration for repeated violations (in minutes)
        self.block_duration = 15

    def _clean_old_requests(self, ip: str, endpoint: str, window: int = 60):
        """Remove requests outside the time window."""
        cutoff = time.time() - window
        if ip in self.requests and endpoint in self.requests[ip]:
            self.requests[ip][endpoint] = [
                (ts, tokens) for ts, tokens in self.requests[ip][endpoint]
                if ts > cutoff
            ]

    def _get_limit(self, endpoint: str) -> int:
        """Get rate limit for endpoint."""
        # Check exact match first
        if endpoint in self.limits:
            return self.limits[endpoint]

        # Check prefix match
        for pattern, limit in self.limits.items():
            if endpoint.startswith(pattern):
                return limit

        return self.limits["default"]

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked."""
        if ip in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[ip]:
                return True
            else:
                # Block expired
                del self.blocked_ips[ip]
        return False

    def check_rate_limit(self, ip: str, endpoint: str) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed: bool, retry_after: int)
        """
        # Check if IP is blocked
        if self.is_blocked(ip):
            remaining = (self.blocked_ips[ip] - datetime.utcnow()).seconds
            return False, remaining

        # Clean old requests
        self._clean_old_requests(ip, endpoint)

        # Get limit for this endpoint
        limit = self._get_limit(endpoint)

        # Count requests in the last minute
        current_count = len(self.requests[ip][endpoint])

        if current_count >= limit:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for IP {ip} on endpoint {endpoint}: "
                f"{current_count}/{limit} requests"
            )

            # Block IP if consistently violating
            if current_count >= limit * 2:
                self.blocked_ips[ip] = datetime.utcnow() + timedelta(minutes=self.block_duration)
                logger.error(f"IP {ip} blocked for {self.block_duration} minutes due to excessive requests")

            return False, 60  # Retry after 1 minute

        # Allow request
        self.requests[ip][endpoint].append((time.time(), 1))
        return True, 0


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host

        # Check X-Forwarded-For header (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Check rate limit
        allowed, retry_after = rate_limiter.check_rate_limit(client_ip, request.url.path)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        limit = rate_limiter._get_limit(request.url.path)
        remaining = limit - len(rate_limiter.requests[client_ip][request.url.path])

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        return response


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

class InputSanitizer:
    """
    Sanitize user inputs to prevent XSS, SQLi, and other injection attacks.
    """

    # Patterns for detecting malicious input
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<embed',
        r'<object',
    ]

    SQL_PATTERNS = [
        r"(\s|^)(union|select|insert|update|delete|drop|create|alter|exec|execute)(\s|;|$)",
        r"--",
        r"/\*.*\*/",
        r";\s*(drop|delete|update|insert)",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Escape HTML to prevent XSS."""
        if not text:
            return text
        return html.escape(text)

    @staticmethod
    def detect_xss(text: str) -> bool:
        """Detect potential XSS attempts."""
        if not text:
            return False

        text_lower = text.lower()
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """Detect potential SQL injection attempts."""
        if not text:
            return False

        text_lower = text.lower()
        for pattern in InputSanitizer.SQL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def detect_path_traversal(text: str) -> bool:
        """Detect path traversal attempts."""
        if not text:
            return False

        for pattern in InputSanitizer.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        # Remove path components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext

        return filename


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements OWASP secure headers recommendations.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS (if using HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

        # Remove server information (MutableHeaders has no .pop)
        server_header = response.headers.get("Server")
        if server_header is not None:
            del response.headers["Server"]

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize all input data.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip validation for certain endpoints
        skip_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Check query parameters
        for param, value in request.query_params.items():
            if InputSanitizer.detect_xss(value):
                logger.warning(f"XSS attempt detected in query param {param}: {value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input: potential XSS detected"}
                )

            if InputSanitizer.detect_sql_injection(value):
                logger.warning(f"SQL injection attempt detected in query param {param}: {value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input: potential SQL injection detected"}
                )

            if InputSanitizer.detect_path_traversal(value):
                logger.warning(f"Path traversal attempt detected in query param {param}: {value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input: potential path traversal detected"}
                )

        # Check path parameters
        if InputSanitizer.detect_path_traversal(request.url.path):
            logger.warning(f"Path traversal attempt in URL: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid path"}
            )

        return await call_next(request)


# =============================================================================
# LOGGING AND MONITORING
# =============================================================================

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all API requests for security auditing.
    """

    # Sensitive fields to redact in logs
    SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "authorization"}

    @staticmethod
    def redact_sensitive_data(data: dict) -> dict:
        """Redact sensitive fields from log data."""
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            if key.lower() in AuditLoggingMiddleware.SENSITIVE_FIELDS:
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = AuditLoggingMiddleware.redact_sensitive_data(value)
            else:
                redacted[key] = value

        return redacted

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get client information
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        user_agent = request.headers.get("User-Agent", "")

        # Process request
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time

        # Log request
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "forwarded_for": forwarded_for,
            "user_agent": user_agent,
            "status_code": response.status_code,
            "response_time": f"{process_time:.3f}s",
        }

        # Log level based on status code
        if response.status_code >= 500:
            logger.error(f"API Request: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"API Request: {log_data}")
        else:
            logger.info(f"API Request: {log_data}")

        # Add custom header with request ID
        response.headers["X-Request-ID"] = f"{int(start_time * 1000000)}"
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

def get_cors_config():
    """
    Get CORS configuration from environment.

    Security best practices:
    - Only allow specific origins in production
    - Limit allowed methods
    - Restrict allowed headers
    - Set appropriate max age
    """

    # Get allowed origins from environment
    allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")

    if allowed_origins_str:
        # Parse comma-separated list
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
    else:
        # Development default (CHANGE IN PRODUCTION)
        allowed_origins = ["http://localhost:3000", "http://localhost:8080"]
        logger.warning(
            "CORS_ALLOWED_ORIGINS not set. Using development defaults. "
            "Set this in production!"
        )

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Organization-ID",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,  # 10 minutes
    }


# =============================================================================
# FILE UPLOAD SECURITY
# =============================================================================

class FileUploadValidator:
    """
    Validate file uploads for security.
    """

    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
        "text/plain",
        "text/csv",
        "application/json",
        "image/png",
        "image/jpeg",
        "image/jpg",
    }

    # Magic bytes for file type detection
    MAGIC_BYTES = {
        "application/pdf": [b"%PDF"],
        "image/png": [b"\x89PNG"],
        "image/jpeg": [b"\xff\xd8\xff"],
        "application/zip": [b"PK\x03\x04"],  # DOCX/XLSX are zip files
    }

    # Maximum file size (100 MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    @staticmethod
    def validate_mime_type(content_type: str) -> bool:
        """Validate MIME type."""
        return content_type in FileUploadValidator.ALLOWED_MIME_TYPES

    @staticmethod
    def validate_file_size(size: int) -> bool:
        """Validate file size."""
        return 0 < size <= FileUploadValidator.MAX_FILE_SIZE

    @staticmethod
    def validate_magic_bytes(file_content: bytes, expected_type: str) -> bool:
        """
        Validate file content using magic bytes.

        This prevents MIME type spoofing.
        """
        if expected_type not in FileUploadValidator.MAGIC_BYTES:
            # No magic bytes defined for this type
            return True

        magic_bytes_list = FileUploadValidator.MAGIC_BYTES[expected_type]

        for magic_bytes in magic_bytes_list:
            if file_content.startswith(magic_bytes):
                return True

        return False

    @staticmethod
    def sanitize_and_validate_filename(filename: str) -> str:
        """
        Sanitize and validate filename.

        Returns sanitized filename or raises HTTPException.
        """
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )

        # Sanitize filename
        sanitized = InputSanitizer.sanitize_filename(filename)

        if not sanitized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )

        return sanitized
