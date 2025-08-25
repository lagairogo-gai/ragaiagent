#!/bin/bash

# File Organizer Script for RAG User Stories Generator
# This script moves scattered Python files to their proper backend locations

set -e  # Exit on any error

echo "🗂️  RAG User Stories Generator - File Organizer"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Create necessary directories
echo "Creating backend directory structure..."

mkdir -p backend/app/core
mkdir -p backend/app/models
mkdir -p backend/app/schemas
mkdir -p backend/app/api/v1
mkdir -p backend/app/services
mkdir -p backend/app/agents
mkdir -p backend/app/utils
mkdir -p backend/app/tests

# Create __init__.py files
touch backend/app/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/v1/__init__.py
touch backend/app/services/__init__.py
touch backend/app/agents/__init__.py
touch backend/app/utils/__init__.py
touch backend/app/tests/__init__.py

print_success "Directory structure created"

echo ""
echo "Moving files to their proper locations..."

# Move core configuration files
if [ -f "core_config.py" ]; then
    mv core_config.py backend/app/core/config.py
    print_success "Moved: core_config.py → backend/app/core/config.py"
else
    print_error "core_config.py not found"
fi

if [ -f "database_config.py" ]; then
    mv database_config.py backend/app/core/database.py
    print_success "Moved: database_config.py → backend/app/core/database.py"
else
    print_error "database_config.py not found"
fi

if [ -f "security_module.py" ]; then
    mv security_module.py backend/app/core/security.py
    print_success "Moved: security_module.py → backend/app/core/security.py"
else
    print_error "security_module.py not found"
fi

# Move model files
if [ -f "user_model.py" ]; then
    mv user_model.py backend/app/models/user.py
    print_success "Moved: user_model.py → backend/app/models/user.py"
else
    print_error "user_model.py not found"
fi

if [ -f "project_model.py" ]; then
    mv project_model.py backend/app/models/project.py
    print_success "Moved: project_model.py → backend/app/models/project.py"
else
    print_error "project_model.py not found"
fi

if [ -f "document_model.py" ]; then
    mv document_model.py backend/app/models/document.py
    print_success "Moved: document_model.py → backend/app/models/document.py"
else
    print_error "document_model.py not found"
fi

if [ -f "user_story_model.py" ]; then
    mv user_story_model.py backend/app/models/user_story.py
    print_success "Moved: user_story_model.py → backend/app/models/user_story.py"
else
    print_error "user_story_model.py not found"
fi

if [ -f "knowledge_graph_model.py" ]; then
    mv knowledge_graph_model.py backend/app/models/knowledge_graph.py
    print_success "Moved: knowledge_graph_model.py → backend/app/models/knowledge_graph.py"
else
    print_error "knowledge_graph_model.py not found"
fi

# Move schema files
if [ -f "user_schemas.py" ]; then
    mv user_schemas.py backend/app/schemas/user.py
    print_success "Moved: user_schemas.py → backend/app/schemas/user.py"
else
    print_error "user_schemas.py not found"
fi

if [ -f "user_story_schemas.py" ]; then
    mv user_story_schemas.py backend/app/schemas/user_story.py
    print_success "Moved: user_story_schemas.py → backend/app/schemas/user_story.py"
else
    print_error "user_story_schemas.py not found"
fi

if [ -f "document_schemas.py" ]; then
    mv document_schemas.py backend/app/schemas/document.py
    print_success "Moved: document_schemas.py → backend/app/schemas/document.py"
else
    print_error "document_schemas.py not found"
fi

# Move API router files
if [ -f "auth_router.py" ]; then
    mv auth_router.py backend/app/api/v1/auth.py
    print_success "Moved: auth_router.py → backend/app/api/v1/auth.py"
else
    print_error "auth_router.py not found"
fi

if [ -f "user_stories_router.py" ]; then
    mv user_stories_router.py backend/app/api/v1/user_stories.py
    print_success "Moved: user_stories_router.py → backend/app/api/v1/user_stories.py"
else
    print_error "user_stories_router.py not found"
fi

if [ -f "documents_router.py" ]; then
    mv documents_router.py backend/app/api/v1/documents.py
    print_success "Moved: documents_router.py → backend/app/api/v1/documents.py"
else
    print_error "documents_router.py not found"
fi

# Move service files
if [ -f "llm_service.py" ]; then
    mv llm_service.py backend/app/services/llm_service.py
    print_success "Moved: llm_service.py → backend/app/services/llm_service.py"
else
    print_error "llm_service.py not found"
fi

if [ -f "rag_service.py" ]; then
    mv rag_service.py backend/app/services/rag_service.py
    print_success "Moved: rag_service.py → backend/app/services/rag_service.py"
else
    print_error "rag_service.py not found"
fi

if [ -f "knowledge_graph_service.py" ]; then
    mv knowledge_graph_service.py backend/app/services/knowledge_graph_service.py
    print_success "Moved: knowledge_graph_service.py → backend/app/services/knowledge_graph_service.py"
else
    print_error "knowledge_graph_service.py not found"
fi

# Move agent files
if [ -f "user_story_agent.py" ]; then
    mv user_story_agent.py backend/app/agents/user_story_agent.py
    print_success "Moved: user_story_agent.py → backend/app/agents/user_story_agent.py"
else
    print_error "user_story_agent.py not found"
fi

# Move utility files
if [ -f "text_processing_utils.py" ]; then
    mv text_processing_utils.py backend/app/utils/text_processing.py
    print_success "Moved: text_processing_utils.py → backend/app/utils/text_processing.py"
else
    print_error "text_processing_utils.py not found"
fi

# Clean up setup scripts by moving them to scripts directory
echo ""
echo "Cleaning up setup scripts..."

if [ -f "setup_script.py" ]; then
    mv setup_script.py scripts/setup_script.py
    print_success "Moved: setup_script.py → scripts/setup_script.py"
fi

if [ -f "setup_script_bash.sh" ]; then
    mv setup_script_bash.sh scripts/setup_script_bash.sh
    print_success "Moved: setup_script_bash.sh → scripts/setup_script_bash.sh"
fi

if [ -f "setup_script_bash_fixed.sh" ]; then
    mv setup_script_bash_fixed.sh scripts/setup_script_bash_fixed.sh
    print_success "Moved: setup_script_bash_fixed.sh → scripts/setup_script_bash_fixed.sh"
fi

if [ -f "project-requirement.txt" ]; then
    mv project-requirement.txt scripts/project-requirement.txt
    print_success "Moved: project-requirement.txt → scripts/project-requirement.txt"
fi

# Create main.py if it doesn't exist in backend/app/
if [ ! -f "backend/app/main.py" ]; then
    cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from .core.config import settings
from .core.database import create_tables, init_knowledge_graph, cleanup_connections

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
        create_tables()
        init_knowledge_graph()
        logger.info("Application initialized successfully")
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
    description="RAG-Based AI Agent for User Story Generation",
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG User Stories Generator API",
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION
    }
EOF
    print_success "Created: backend/app/main.py"
fi

# Create requirements.txt if it doesn't exist
if [ ! -f "backend/requirements.txt" ]; then
    cat > backend/requirements.txt << 'EOF'
# Core web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database & ORM
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
redis==5.0.1

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# LLM & AI frameworks
langchain==0.1.0
langchain-openai==0.0.2
langchain-community==0.0.10
langgraph==0.0.20
openai==1.6.1

# Vector databases
chromadb==0.4.18
pinecone-client==2.2.4

# Knowledge graph
neo4j==5.15.0
py2neo==2021.2.4

# Text processing & embeddings
sentence-transformers==2.2.2
pypdf2==3.0.1
python-docx==1.1.0
openpyxl==3.1.2

# Background tasks
celery[redis]==5.3.4

# Integrations
atlassian-python-api==3.41.0
office365-rest-python-client==2.5.3
requests==2.31.0

# Utilities
pydantic==2.5.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
typing-extensions==4.8.0

# Development & testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
black==23.11.0
flake8==6.1.0

# Monitoring & logging
structlog==23.2.0
EOF
    print_success "Created: backend/requirements.txt"
fi

# Create Dockerfile for backend if it doesn't exist
if [ ! -f "backend/Dockerfile" ]; then
    cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads chroma_db

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    print_success "Created: backend/Dockerfile"
fi

# Create .env.template if it doesn't exist
if [ ! -f ".env.template" ]; then
    cat > .env.template << 'EOF'
# RAG User Stories Generator - Environment Configuration
# Copy this file to .env and fill in your actual values

# Application Settings
DEBUG=false
SECRET_KEY=your_super_secret_key_change_this_in_production
APP_NAME="RAG User Stories Generator"
VERSION=1.0.0

# Database Passwords
POSTGRES_PASSWORD=your_postgres_password_here
REDIS_PASSWORD=your_redis_password_here
NEO4J_PASSWORD=your_neo4j_password_here

# LLM Provider API Keys
OPENAI_API_KEY=your_openai_api_key_here
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Default LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4
DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002

# Vector Database Type
VECTOR_DB_TYPE=chromadb
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Knowledge Graph Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j

# Server Settings
HOST=0.0.0.0
PORT=8000

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080
ALGORITHM=HS256
EOF
    print_success "Created: .env.template"
fi

echo ""
echo "Verification - Checking file organization..."

# Verify the backend structure
if [ -f "backend/app/main.py" ]; then
    print_success "✓ Backend main app found"
else
    print_error "✗ Backend main app missing"
fi

if [ -d "backend/app/core" ] && [ -f "backend/app/core/__init__.py" ]; then
    print_success "✓ Backend core package ready"
else
    print_error "✗ Backend core package incomplete"
fi

if [ -d "backend/app/models" ] && [ -f "backend/app/models/__init__.py" ]; then
    print_success "✓ Backend models package ready"
else
    print_error "✗ Backend models package incomplete"
fi

if [ -d "backend/app/services" ] && [ -f "backend/app/services/__init__.py" ]; then
    print_success "✓ Backend services package ready"
else
    print_error "✗ Backend services package incomplete"
fi

echo ""
echo "📁 Final project structure:"
echo "├── backend/"
echo "│   ├── app/"
echo "│   │   ├── core/        # Configuration & database"
echo "│   │   ├── models/      # Database models"
echo "│   │   ├── schemas/     # Pydantic schemas"
echo "│   │   ├── api/v1/      # API endpoints"
echo "│   │   ├── services/    # Business logic"
echo "│   │   ├── agents/      # AI agents"
echo "│   │   └── utils/       # Utilities"
echo "│   ├── requirements.txt"
echo "│   └── Dockerfile"
echo "├── frontend/"
echo "├── scripts/"
echo "├── docker-compose.yml"
echo "└── .env.template"

echo ""
echo -e "${GREEN}🎉 File organization completed!${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Configure your environment:"
echo "   ${YELLOW}cp .env.template .env${NC}"
echo "   ${YELLOW}nano .env${NC}  # Add your API keys"
echo ""
echo "2. Test the backend structure:"
echo "   ${YELLOW}cd backend${NC}"
echo "   ${YELLOW}python -c \"from app.main import app; print('✓ Import successful')\"${NC}"
echo ""
echo "3. Start the application:"
echo "   ${YELLOW}docker-compose up -d${NC}"
echo ""
echo "4. Access the API:"
echo "   ${BLUE}http://localhost:8000${NC}"
echo "   ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${GREEN}Ready to go! 🚀${NC}"