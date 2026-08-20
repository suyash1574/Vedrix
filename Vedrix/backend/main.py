from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import init_db, get_session
from app.services.interview_engine.graph import initialize_interview_graph, close_interview_graph
from app.services.cache_service import init_cache, close_cache, cache_service
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter
from app.core.logging_config import setup_logging, get_logger
from app.core.metrics import router as metrics_router
from app.core.csrf import CSRFMiddleware
from app.middleware.audit import AuditLogMiddleware
from app.middleware.performance import PerformanceMonitoringMiddleware
from app.services.session_cleanup import session_cleanup
from app.services.orchestrator_scheduler import orchestrator_scheduler
import uuid
import time
from sqlalchemy import text

# Setup logging (JSON in production, plain in dev)
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await init_cache()
    await initialize_interview_graph()
    # Phase 1.4: Start session cleanup service
    await session_cleanup.start_cleanup_loop(interval_seconds=300)  # Every 5 minutes
    # Orchestrator: Start scheduled workflow checks (every 15 minutes)
    await orchestrator_scheduler.start(interval_seconds=900)
    logger.info("Vedrix backend started — DB, cache, and session cleanup initialized")
    yield
    # Shutdown logic
    await orchestrator_scheduler.stop()
    await session_cleanup.stop_cleanup_loop()
    await close_cache()
    await close_interview_graph()
    logger.info("Vedrix backend shutting down")

app = FastAPI(
    title="Vedrix AI Interview System",
    description="Modern AI-powered interview platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CSRF Protection — must be after SlowAPI but before CORS
app.add_middleware(CSRFMiddleware)

# Audit Logging — logs all state-changing actions
app.add_middleware(AuditLogMiddleware)

# Performance Monitoring — tracks request latency and metrics
app.add_middleware(PerformanceMonitoringMiddleware)

# CORS Middleware configuration
if settings.ENVIRONMENT == "production":
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    if "*" in origins or not origins:
        raise ValueError(
            "CORS: Wildcard '*' is not allowed and ALLOWED_ORIGINS must be configured when ENVIRONMENT is production."
        )
else:
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]
    if settings.FRONTEND_URL:
        origins.append(settings.FRONTEND_URL)
    if settings.ALLOWED_ORIGINS:
        for o in [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]:
            if o not in origins:
                origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(metrics_router)  # Prometheus metrics at /metrics

# ── Request ID Middleware for Tracing ───────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.start_time = time.time()

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log request details
    duration = time.time() - request.state.start_time
    logger.info(
        f"request_id={request_id} method={request.method} path={request.url.path} "
        f"status={response.status_code} duration={duration:.3f}s"
    )

    return response

# ── Health Check Endpoints ───────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Basic health check - service is running"""
    return {
        "status": "healthy",
        "service": "vedrix-backend",
        "version": "1.0.0",
    }

@app.get("/health/ready")
async def readiness_check():
    """Detailed health check - includes database connectivity"""
    checks = {
        "database": "unhealthy",
        "redis": "unhealthy",
        "service": "healthy",
    }

    # Check database connection
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
            checks["database"] = "healthy"
            break
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "unhealthy"

    try:
        checks["redis"] = "healthy" if await cache_service.health_check() else "unhealthy"
    except Exception:
        checks["redis"] = "unhealthy"

    dependencies_healthy = checks["database"] == "healthy" and checks["redis"] == "healthy"
    overall = "healthy" if dependencies_healthy else "degraded"

    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={
            "status": overall,
            "checks": checks,
            "service": "vedrix-backend",
            "version": "1.0.0",
        }
    )

@app.get("/")
async def root():
    return {"message": "Welcome to Vedrix API", "status": "online"}
