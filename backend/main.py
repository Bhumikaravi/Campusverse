import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import connect_db, close_db
from app.routers import (
    auth_router,
    materials_router,
    admin_router,
    reviews_router,
    bookmarks_router,
    categories_router,
    scanning_booth_router,
    classifier_router,
    quality_router,
    summaries_router,
    search_router,
    similarity_router,
    chat_router,
    study_buddy_router,
    guardrails_router,
    recognition_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("campusverse")

from datetime import datetime

async def seed_admin_user():
    from app.database import get_db
    from app.middleware.auth import hash_password
    db = get_db()
    admin = await db["users"].find_one({"role": "admin"})
    if not admin:
        logger.info("No administrator found. Seeding default administrator account...")
        admin_email = "admin@campusverse.edu"
        existing = await db["users"].find_one({"email": admin_email})
        if existing:
            await db["users"].update_one({"email": admin_email}, {"$set": {"role": "admin"}})
        else:
            pwd_hash = hash_password("Admin@123")
            now = datetime.utcnow()
            await db["users"].insert_one({
                "email": admin_email,
                "full_name": "CampusVerse Admin",
                "name": "CampusVerse Admin",
                "hashed_password": pwd_hash,
                "passwordHash": pwd_hash,
                "role": "admin",
                "department": "Administration",
                "semester": None,
                "created_at": now,
                "updated_at": now,
                "createdAt": now
            })
        logger.info("Admin user 'admin@campusverse.edu' seeded successfully (password: Admin@123)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect MongoDB and init indexes
    logger.info("Initializing CampusVerse FastAPI Backend...")
    try:
        await connect_db()
        await seed_admin_user()
    except Exception as e:
        logger.warning(
            "MongoDB is not currently reachable (%s). Backend running in standalone mode (document extraction, OCR, and AI summarization active).",
            e
        )
    try:
        from app.services.text_extract import get_rapid_ocr
        get_rapid_ocr()
        logger.info("RapidOCR neural network engine pre-warmed and ready.")
    except Exception:
        pass
    yield
    # Shutdown: close MongoDB client
    logger.info("Shutting down CampusVerse Backend...")
    try:
        await close_db()
    except Exception:
        pass

app = FastAPI(
    title="CampusVerse API",
    description="CampusVerse Full-Stack Study Material & AI Moderation API",
    version="2.0.0",
    lifespan=lifespan
)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware (Supports configured CLIENT_URL, local dev, and all Vercel domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type"]
)

from fastapi.exceptions import RequestValidationError, HTTPException

# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTPException on %s: %s (status %s)", request.url.path, exc.detail, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg', 'Invalid input')}")
    detail_msg = "; ".join(errors) if errors else "Invalid request data provided."
    logger.warning("Validation error on %s: %s", request.url.path, detail_msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail_msg, "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Server processing error: {str(exc)}"}
    )

# Routers
app.include_router(auth_router)
app.include_router(materials_router)
app.include_router(admin_router)
app.include_router(reviews_router)
app.include_router(bookmarks_router)
app.include_router(categories_router)
app.include_router(scanning_booth_router)
app.include_router(classifier_router)
app.include_router(quality_router)
app.include_router(summaries_router)
app.include_router(search_router)
app.include_router(similarity_router)
app.include_router(chat_router)
app.include_router(study_buddy_router)
app.include_router(guardrails_router)
app.include_router(recognition_router)

# Mount built React frontend static files if available
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent / "frontend_dist"
if not frontend_dist.exists():
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_frontend(full_path: str):
        if full_path.startswith("api/") or full_path == "health" or full_path == "docs" or full_path == "openapi.json":
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        target_file = frontend_dist / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(frontend_dist / "index.html"))

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "campusverse-fastapi",
        "storage": settings.STORAGE_PROVIDER,
        "moderation": "gemini" if settings.GEMINI_API_KEY else "rule-based-fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        reload_excludes=["*.pyc", "*node_modules*", "*.log", "uploads/*"]
    )
