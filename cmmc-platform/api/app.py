"""
CMMC Compliance Platform - Main Application
FastAPI application with all routers and middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

# Import configuration
from config import settings

# Import database
from database import Database, get_db_pool, get_database

# Import API routers
from user_api import router as user_router
from assessment_api import router as assessment_router
from document_api import router as document_router
from analysis_api import router as analysis_router
from provider_api import router as provider_router
from report_api import router as report_router
from dashboard_api import router as dashboard_router
from bulk_api import router as bulk_router
from integration_api import router as integration_router
from document_management_api import router as document_mgmt_router
from ai_cost_api import router as ai_cost_router
from ai_budget_api import router as ai_budget_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
database = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting CMMC Compliance Platform API...")
    try:
        await database.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down CMMC Compliance Platform API...")
    await database.disconnect()
    logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Production-ready API for CMMC Level 2 compliance assessments",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Database Dependency Injection
# ============================================================================
# Wire the global database instance to all API modules that need it
# This fixes the "Database pool dependency not configured" errors

# Import the broken get_db_pool functions from each module
import assessment_api
import dashboard_api
import provider_api
import report_api
import user_api
import ai_cost_api
import ai_budget_api
from middleware import auth_middleware

# Override their placeholder dependencies with the real database pool
app.dependency_overrides[assessment_api.get_db_pool] = get_db_pool
app.dependency_overrides[dashboard_api.get_db_pool] = get_db_pool
app.dependency_overrides[provider_api.get_db_pool] = get_db_pool
app.dependency_overrides[report_api.get_db_pool] = get_db_pool
app.dependency_overrides[user_api.get_db_pool] = get_db_pool
app.dependency_overrides[ai_cost_api.get_db_pool] = get_db_pool
app.dependency_overrides[ai_budget_api.get_db_pool] = get_db_pool
app.dependency_overrides[auth_middleware.get_db_pool] = get_db_pool

logger.info("Database dependencies wired successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        pool = database.get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/api/docs"
    }


# Include all routers
app.include_router(user_router, prefix="/api/v1", tags=["users"])
app.include_router(assessment_router, prefix="/api/v1", tags=["assessments"])
app.include_router(document_router, prefix="/api/v1", tags=["documents"])
app.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])
app.include_router(provider_router, prefix="/api/v1", tags=["providers"])
app.include_router(report_router, prefix="/api/v1", tags=["reports"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
app.include_router(bulk_router, prefix="/api/v1", tags=["bulk"])
app.include_router(integration_router, prefix="/api/v1", tags=["integrations"])
app.include_router(document_mgmt_router, prefix="/api/v1", tags=["document-management", "rag"])
app.include_router(ai_cost_router, prefix="/api/v1/ai", tags=["ai-costs"])
app.include_router(ai_budget_router, prefix="/api/v1/ai", tags=["ai-budgets"])


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
