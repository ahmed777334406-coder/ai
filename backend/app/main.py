from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict, deque
from time import monotonic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
from app.database import Base, engine, ensure_database_extensions
from app.api.router import api_router
from app import models  # noqa: F401 - register SQLAlchemy models

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment.lower() == "production":
        if settings.jwt_secret_key == "CHANGE_ME_FOR_LOCAL_DEVELOPMENT_ONLY" or settings.jwt_secret_key.startswith("replace-with-") or len(settings.jwt_secret_key) < 32:
            raise RuntimeError("Set a strong JWT_SECRET_KEY before production startup")
        if not settings.database_url.startswith("postgresql"):
            raise RuntimeError("Production requires persistent PostgreSQL")
        if "*" in settings.cors_origin_list or any(not o.startswith("https://") for o in settings.cors_origin_list):
            raise RuntimeError("Production CORS requires explicit HTTPS origins")
        if settings.admin_password == "ChangeThisAdminPassword!":
            raise RuntimeError("Set a unique ADMIN_PASSWORD before production startup")
    if settings.environment.lower() != "production":
        ensure_database_extensions()
        Base.metadata.create_all(bind=engine)
    (Path(settings.upload_dir) / "public").mkdir(parents=True, exist_ok=True)
    (Path(settings.upload_dir) / "private").mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="Beihang SmartFind API", version="1.0.0", description="AI-powered bilingual campus lost-and-found platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_rate_buckets = defaultdict(deque)

@app.middleware("http")
async def basic_rate_limit(request, call_next):
    path = request.url.path
    if request.method in {"POST", "PATCH", "PUT", "DELETE"} and path.startswith("/api/v1") and not request.headers.get("authorization"):
        if request.headers.get("x-smartfind-request") != "1":
            return JSONResponse(status_code=403, content={"detail": "Missing CSRF request header"})
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            return JSONResponse(status_code=403, content={"detail": "Untrusted request origin"})
    if path.startswith("/api/v1/auth/login"):
        limit, window = 12, 60
    elif path.startswith("/api/v1/ai") and request.method == "POST":
        limit, window = 20, 60
    elif path.startswith("/api/v1/auth/session"):
        limit, window = 30, 60
    elif path.startswith("/api/v1/auth/register"):
        limit, window = 8, 3600
    elif path.startswith("/api/v1/listings/") and request.method == "POST":
        limit, window = 30, 60
    else:
        limit, window = 300, 60
    host = request.client.host if request.client else "unknown"
    # Normalize numeric IDs and group non-auth routes to bound attacker-controlled keys.
    group = "login" if path.startswith("/api/v1/auth/login") else "register" if path.startswith("/api/v1/auth/register") else "uploads" if path.startswith("/api/v1/listings/") and request.method == "POST" else "general"
    if path.startswith("/api/v1/ai") and request.method == "POST": group = "ai"
    elif path.startswith("/api/v1/auth/session"): group = "session"
    key = f"{host}:{group}"
    now = monotonic()
    if len(_rate_buckets) > 10000:
        for old_key in list(_rate_buckets):
            if not _rate_buckets[old_key] or now - _rate_buckets[old_key][-1] > 3600:
                del _rate_buckets[old_key]
        if len(_rate_buckets) > 10000 and key not in _rate_buckets:
            return JSONResponse(status_code=429, content={"detail":"Rate limit capacity reached"})
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > window: bucket.popleft()
    if len(bucket) >= limit:
        return JSONResponse(status_code=429, content={"detail":"Rate limit exceeded. Please try again later."})
    bucket.append(now)
    return await call_next(request)

@app.get("/health/live", tags=["health"])
def health_live():
    return {"status": "alive", "service": "beihang-smartfind-api"}

@app.get("/health/ready", tags=["health"])
def health_ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": engine.dialect.name}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database_error": type(exc).__name__})

app.include_router(api_router, prefix="/api/v1")
app.mount("/media/public", StaticFiles(directory=str(Path(settings.upload_dir) / "public"), check_dir=False), name="public-media")
