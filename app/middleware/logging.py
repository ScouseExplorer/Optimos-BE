"""Middleware for logging HTTP requests and responses."""

import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request and response details."""
        
        # Generate request ID for tracing
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        
        # Capture request details
        start_time = time.time()
        method = request.method
        path = request.url.path
        query_string = request.url.query
        client_host = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_string": query_string,
                "client_host": client_host,
                "event": "request_started"
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_host": client_host,
                    "event": "request_completed"
                }
            )
            
            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log errors
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "client_host": client_host,
                    "error": str(e),
                    "event": "request_error"
                },
                exc_info=True
            )
            raise


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log error responses with more detail."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Capture and log error responses."""
        
        response = await call_next(request)
        
        # Log 4xx and 5xx responses
        if response.status_code >= 400:
            logger.warning(
                f"Error response: {response.status_code}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "event": "error_response"
                }
            )
        
        return response
