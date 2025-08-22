from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "RAG User Stories Generator"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Vector Database
    VECTOR_DB_TYPE: str = Field(default="chromadb", env="VECTOR_DB_TYPE")  # chromadb or pinecone
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    PINECONE_API_KEY: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: Optional[str] = Field(default=None, env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: Optional[str] = Field(default=None, env="PINECONE_INDEX_NAME")
    
    # Knowledge Graph (Neo4j)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(..., env="NEO4J_PASSWORD")
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_VERSION: str = Field(default="2023-12-01-preview", env="AZURE_OPENAI_VERSION")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    
    # Default LLM settings
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    DEFAULT_MODEL: str = Field(default="gpt-4", env="DEFAULT_MODEL")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-ada-002", env="DEFAULT_EMBEDDING_MODEL")
    
    # External Integrations
    JIRA_BASE_URL: Optional[str] = Field(default=None, env="JIRA_BASE_URL")
    JIRA_USERNAME: Optional[str] = Field(default=None, env="JIRA_USERNAME")
    JIRA_API_TOKEN: Optional[str] = Field(default=None, env="JIRA_API_TOKEN")
    
    CONFLUENCE_BASE_URL: Optional[str] = Field(default=None, env="CONFLUENCE_BASE_URL")
    CONFLUENCE_USERNAME: Optional[str] = Field(default=None, env="CONFLUENCE_USERNAME")
    CONFLUENCE_API_TOKEN: Optional[str] = Field(default=None, env="CONFLUENCE_API_TOKEN")
    
    SHAREPOINT_SITE_URL: Optional[str] = Field(default=None, env="SHAREPOINT_SITE_URL")
    SHAREPOINT_CLIENT_ID: Optional[str] = Field(default=None, env="SHAREPOINT_CLIENT_ID")
    SHAREPOINT_CLIENT_SECRET: Optional[str] = Field(default=None, env="SHAREPOINT_CLIENT_SECRET")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # File Upload
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md", ".xlsx", ".csv"]
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # RAG Configuration
    CHUNK_SIZE: int = Field(default=1000, env="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=200, env="CHUNK_OVERLAP")
    TOP_K_RETRIEVAL: int = Field(default=5, env="TOP_K_RETRIEVAL")
    SIMILARITY_THRESHOLD: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # User Story Generation
    MAX_USER_STORIES_PER_REQUEST: int = Field(default=10, env="MAX_USER_STORIES_PER_REQUEST")
    USER_STORY_TEMPLATE: str = Field(
        default="As a {persona}, I want {functionality} so that {benefit}.",
        env="USER_STORY_TEMPLATE"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure upload directory exists
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)


# Global settings instance
settings = Settings()