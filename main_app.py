from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from contextlib import asynccontextmanager
import structlog
import time
import uvicorn

from .core.config import settings
from .core.database import create_tables, init_knowledge_graph, cleanup_connections
from .core.database import check_postgres_health, check_redis_health, check_neo4j_health
from .api.v1 import auth, documents, user_stories, integrations, knowledge_graph
from .api.v1.auth import router as auth_router
from .api.v1.documents import router as documents_router
from .api.v1.user_stories import router as user_stories_router
from .api.v1.integrations import router as integrations_router
from .api.v1.knowledge_graph import router as knowledge_graph_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting RAG User Stories Generator API")
    
    try:
        # Initialize database tables
        create_tables()
        logger.info("Database tables created/verified")
        
        # Initialize knowledge graph schema
        init_knowledge_graph()
        logger.info("Knowledge graph schema initialized")
        
        # Check all service connections
        postgres_healthy = check_postgres_health()
        redis_healthy = check_redis_health()
        neo4j_healthy = check_neo4j_health()
        
        logger.info(
            "Service health check completed",
            postgres=postgres_healthy,
            redis=redis_healthy,
            neo4j=neo4j_healthy
        )
        
        if not all([postgres_healthy, redis_healthy, neo4j_healthy]):
            logger.warning("Some services are not healthy - check configuration")
        
    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG User Stories Generator API")
    cleanup_connections()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
    RAG-Based AI Agent for User Story Generation
    
    This API provides comprehensive functionality for:
    - Document upload and processing
    - AI-powered user story generation using RAG
    - Knowledge graph management
    - External system integrations (Jira, Confluence, SharePoint)
    - Project and team collaboration
    
    Built with FastAPI, LangChain, and Neo4j for enterprise-grade performance.
    """,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"] if settings.DEBUG else ["*"]
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s"
    )
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Custom exception handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url),
        method=request.method
    )
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "error_id": f"{int(time.time())}"  # Simple error ID for tracking
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.VERSION,
        "environment": "development" if settings.DEBUG else "production"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including all services"""
    postgres_healthy = check_postgres_health()
    redis_healthy = check_redis_health()
    neo4j_healthy = check_neo4j_health()
    
    overall_healthy = all([postgres_healthy, redis_healthy, neo4j_healthy])
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": time.time(),
        "version": settings.VERSION,
        "services": {
            "postgresql": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "neo4j": "healthy" if neo4j_healthy else "unhealthy"
        },
        "configuration": {
            "debug_mode": settings.DEBUG,
            "vector_db_type": settings.VECTOR_DB_TYPE,
            "default_llm_provider": settings.DEFAULT_LLM_PROVIDER,
            "default_model": settings.DEFAULT_MODEL
        }
    }


# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG User Stories Generator API",
        "version": settings.VERSION,
        "docs_url": "/docs" if settings.DEBUG else "Documentation not available in production",
        "health_check": "/health"
    }


# Include API routers
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"]
)

app.include_router(
    user_stories_router,
    prefix="/api/v1/user-stories",
    tags=["User Stories"]
)

app.include_router(
    integrations_router,
    prefix="/api/v1/integrations",
    tags=["Integrations"]
)

app.include_router(
    knowledge_graph_router,
    prefix="/api/v1/knowledge-graph",
    tags=["Knowledge Graph"]
)


# API versioning info
@app.get("/api/v1")
async def api_v1_info():
    """API v1 information"""
    return {
        "version": "1.0",
        "description": "RAG User Stories Generator API v1",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "documents": "/api/v1/documents",
            "user_stories": "/api/v1/user-stories", 
            "integrations": "/api/v1/integrations",
            "knowledge_graph": "/api/v1/knowledge-graph"
        },
        "features": [
            "JWT Authentication",
            "Document Upload & Processing",
            "AI-Powered User Story Generation",
            "RAG (Retrieval-Augmented Generation)",
            "Knowledge Graph Management",
            "External Integrations (Jira, Confluence, SharePoint)",
            "Project Management",
            "Real-time Collaboration"
        ]
    }


# Development server runner
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )