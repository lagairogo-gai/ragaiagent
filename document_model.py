from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class DocumentType(PyEnum):
    """Document type enumeration"""
    REQUIREMENTS = "requirements"
    SPECIFICATION = "specification"
    USER_MANUAL = "user_manual"
    TECHNICAL_DOC = "technical_doc"
    BUSINESS_RULES = "business_rules"
    MEETING_NOTES = "meeting_notes"
    OTHER = "other"


class DocumentStatus(PyEnum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Document(Base):
    """Document model for storing and processing uploaded files"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Document metadata
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(50), nullable=False)  # MIME type
    document_type = Column(String(50), default=DocumentType.OTHER.value)
    
    # Content and processing
    title = Column(String(500), nullable=True)  # Extracted or provided title
    content = Column(Text, nullable=True)  # Extracted text content
    summary = Column(Text, nullable=True)  # AI-generated summary
    
    # Processing status
    status = Column(String(20), default=DocumentStatus.UPLOADED.value)
    processing_error = Column(Text, nullable=True)
    
    # Embedding and vector store
    embeddings_generated = Column(Boolean, default=False)
    vector_store_id = Column(String(100), nullable=True)  # Reference to vector store
    chunk_count = Column(Integer, default=0)
    
    # Relationships
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Integration source
    source_type = Column(String(50), default="upload")  # upload, jira, confluence, sharepoint
    source_id = Column(String(255), nullable=True)  # External ID from source system
    source_url = Column(String(500), nullable=True)  # URL to original document
    
    # Document metadata from AI processing
    extracted_metadata = Column(JSON, default=dict)  # AI-extracted metadata
    entities = Column(JSON, default=list)  # Named entities found in document
    keywords = Column(JSON, default=list)  # Key terms and phrases
    
    # Knowledge graph integration
    kg_document_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    uploaded_by = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    annotations = relationship("DocumentAnnotation", back_populates="document")
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "document_type": self.document_type,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "processing_error": self.processing_error,
            "embeddings_generated": self.embeddings_generated,
            "vector_store_id": self.vector_store_id,
            "chunk_count": self.chunk_count,
            "project_id": self.project_id,
            "uploaded_by_id": self.uploaded_by_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "extracted_metadata": self.extracted_metadata,
            "entities": self.entities,
            "keywords": self.keywords,
            "kg_document_id": self.kg_document_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "processed_at": self.processed_at
        }


class DocumentChunk(Base):
    """Document chunks for RAG processing"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Chunk content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    
    # Chunk metadata
    start_position = Column(Integer, nullable=True)  # Start position in original text
    end_position = Column(Integer, nullable=True)  # End position in original text
    word_count = Column(Integer, nullable=False)
    
    # Vector embedding
    embedding_id = Column(String(100), nullable=True)  # Reference to vector store
    similarity_threshold = Column(Float, default=0.7)
    
    # Chunk classification
    chunk_type = Column(String(50), nullable=True)  # heading, paragraph, table, etc.
    importance_score = Column(Float, default=0.5)  # AI-determined importance
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(document_id={self.document_id}, index={self.chunk_index})>"
    
    def to_dict(self):
        """Convert chunk to dictionary"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "word_count": self.word_count,
            "embedding_id": self.embedding_id,
            "similarity_threshold": self.similarity_threshold,
            "chunk_type": self.chunk_type,
            "importance_score": self.importance_score
        }


class DocumentAnnotation(Base):
    """Manual annotations and comments on documents"""
    __tablename__ = "document_annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Annotation content
    annotation_text = Column(Text, nullable=False)
    annotation_type = Column(String(50), default="comment")  # comment, highlight, tag
    
    # Position in document
    start_position = Column(Integer, nullable=True)
    end_position = Column(Integer, nullable=True)
    selected_text = Column(Text, nullable=True)
    
    # Annotation metadata
    tags = Column(JSON, default=list)
    is_resolved = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="annotations")
    user = relationship("User")
    
    def __repr__(self):
        return f"<DocumentAnnotation(document_id={self.document_id}, type='{self.annotation_type}')>"
    
    def to_dict(self):
        """Convert annotation to dictionary"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "annotation_text": self.annotation_text,
            "annotation_type": self.annotation_type,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "selected_text": self.selected_text,
            "tags": self.tags,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }