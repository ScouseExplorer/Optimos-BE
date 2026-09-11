from time import time
from typing import Dict
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, users, chats, admin, subscriptions, profile
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import User, Subscription, Chat, UserProfile, NotificationPreferences, SecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Optimos Backend API",
    version=settings.VERSION,
    description="Optimos Backend API"
)


# Rate limiting
request_tracker: Dict[str, list] = defaultdict(list)  # IP -> [timestamp1, timestamp2, ...]
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 10  # per IP


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time()

        # Clean old requests outside the window
        request_tracker[client_ip] = [
            ts for ts in request_tracker[client_ip]
            if current_time - ts < RATE_LIMIT_WINDOW
        ]

        # Check if limit exceeded
        remaining = MAX_REQUESTS_PER_WINDOW - len(request_tracker[client_ip])
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={
                    "Retry-After": str(RATE_LIMIT_WINDOW),
                    "X-RateLimit-Limit": str(MAX_REQUESTS_PER_WINDOW),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(RATE_LIMIT_WINDOW),
                },
            )

        # Record this request
        request_tracker[client_ip].append(current_time)

        response = await call_next(request)
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


@app.get("/")
async def root():
    return {"message": "Welcome to Optimos API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(chats.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)
