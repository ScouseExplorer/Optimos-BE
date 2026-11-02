import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.routes import (
    admin,
    auth,
    billing,
    chats,
    credits,
    experiences,
    global_datasets,
    opinions,
    posts,
    profile,
    subscriptions,
    usage,
    users,
)
from app.core.config import settings
from app.core.runtime_validation import assert_runtime_settings_safe, redis_required
from app.db.base import Base
from app.db.session import engine
from app.models import User, Subscription, Chat, UserProfile, NotificationPreferences, SecuritySettings
from app.services.rate_limit_service import RateLimitService
from app.services import token_service
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Optional compatibility mode for local/dev environments.
if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(_: FastAPI):
    assert_runtime_settings_safe(settings)
    yield


app = FastAPI(
    title="Optimos Backend API",
    version=settings.VERSION,
    description="Optimos Backend API",
    lifespan=lifespan,
)


logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("optimos.api")


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_for_path(path: str) -> int:
    if path.startswith("/api/auth"):
        return settings.RATE_LIMIT_AUTH_REQUESTS
    if path.startswith("/api/chats"):
        return settings.RATE_LIMIT_AI_REQUESTS
    if path.startswith("/api/admin"):
        return settings.RATE_LIMIT_ADMIN_REQUESTS
    return settings.RATE_LIMIT_DEFAULT_REQUESTS


def _rate_limit_group(path: str) -> str:
    if path.startswith("/api/auth"):
        return "auth"
    if path.startswith("/api/chats"):
        return "ai"
    if path.startswith("/api/admin"):
        return "admin"
    return "default"


def _request_id_from_request(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid4())


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: object | None = None,
) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
            "request_id": _request_id_from_request(request),
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        # Backward compatibility for existing clients that read only `detail`.
        "detail": message,
    }
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started_at = time()
        client_ip = _get_client_ip(request)

        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time() - started_at) * 1000)
            logger.exception(
                json.dumps(
                    {
                        "event": "request_error",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": client_ip,
                        "latency_ms": latency_ms,
                    }
                )
            )
            raise

        latency_ms = int((time() - started_at) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                    "latency_ms": latency_ms,
                }
            )
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = _get_client_ip(request)
        path = request.url.path
        allowed = _rate_limit_for_path(path)
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        group = _rate_limit_group(path)
        decision = RateLimitService.evaluate(
            client_key=client_ip,
            group=group,
            allowed=allowed,
            window_seconds=window,
        )

        if decision.limited:
            response = _error_response(
                request=request,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Please try again later.",
            )
            response.headers["Retry-After"] = str(decision.retry_after)
            response.headers["X-RateLimit-Limit"] = str(decision.allowed)
            response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
            response.headers["X-RateLimit-Window"] = str(decision.window)
            response.headers["X-Request-ID"] = _request_id_from_request(request)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.allowed)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Window"] = str(decision.window)
        return response


# Add middleware (order matters: outermost first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = exc.detail if not isinstance(exc.detail, str) else None
    return _error_response(
        request=request,
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=message,
        details=details,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Validation failed",
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        json.dumps(
            {
                "event": "unhandled_exception",
                "request_id": _request_id_from_request(request),
                "path": request.url.path,
                "method": request.method,
            }
        )
    )
    return _error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
    )


@app.get("/")
async def root():
    return {"message": "Welcome to Optimos API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive", "version": settings.VERSION}


@app.get("/health/ready")
async def readiness_check(request: Request):
    checks = {"database": False, "redis": False}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        if token_service.USE_REDIS:
            token_service.redis_client.ping()
            checks["redis"] = True
        else:
            checks["redis"] = not redis_required(settings)
    except Exception:
        checks["redis"] = False

    overall_ready = all(checks.values())
    status_code = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {
        "status": "ready" if overall_ready else "not_ready",
        "checks": checks,
        "version": settings.VERSION,
        "request_id": _request_id_from_request(request),
    }
    return JSONResponse(status_code=status_code, content=payload)


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(chats.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)
app.include_router(credits.router)
app.include_router(billing.router)
app.include_router(usage.router)
app.include_router(experiences.router)
app.include_router(opinions.router)
app.include_router(posts.router)
app.include_router(global_datasets.router)
