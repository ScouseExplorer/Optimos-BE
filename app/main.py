from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, users
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Optimos Backend API",
    version=settings.VERSION,
    description="Optimos Backend API"
)

@app.get("/")
async def root():
    return {"message": "Welcome to Optimos API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    return {"message": "Welcome to Optimos API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
