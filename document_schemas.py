from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentBase(BaseModel):
    """Base document schema"""
    title: Optional[str] = None
    document_type: str = "other"
    
    @validator('document_type')
    def validate_document_type(cls, v):
        allowed_types = [
            "requirements", "specification", "user_manual", 
            "technical_doc", "business_rules", "meeting_notes", "other"
        ]
        if v not in allowed_types:
            raise ValueError(f'Document type must be one of: {", ".join(allowed_types)}')
        return v


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    project_id: int
    source_type: str = "upload"
    source_id: Optional[str] = None
    source_url: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    title: Optional[str] = None
    document_type: Optional[str] = None
    summary: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    entities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    summary: Optional[str] = None
    status: str
    processing_error: Optional[str] = None
    embeddings_generated: bool
    chunk_count: int
    project_id: int
    uploaded_by_id: int
    source_type: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    extracted_metadata: Dict[str, Any] = {}
    entities: List[str] = []
    keywords: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for document list"""
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response"""
    id: int
    document_id: int
    content: str
    chunk_index: int
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    word_count: int
    chunk_type: Optional[str] = None
    importance_score: float = 0.5
    
    class Config:
        from_attributes = True


class DocumentAnnotationBase(BaseModel):
    """Base annotation schema"""
    annotation_text: str
    annotation_type: str = "comment"
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    selected_text: Optional[str] = None
    tags: Optional[List[str]] = []
    
    @validator('annotation_text')
    def validate_annotation_text(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Annotation text cannot be empty')
        return v.strip()


class DocumentAnnotationCreate(DocumentAnnotationBase):
    """Schema for creating an annotation"""
    pass


class DocumentAnnotationResponse(DocumentAnnotationBase):
    """Schema for annotation response"""
    id: int
    document_id: int
    user_id: int
    is_resolved: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentSearchRequest(BaseModel):
    """Schema for document search request"""
    query: str
    project_id: Optional[int] = None
    document_types: Optional[List[str]] = None
    search_type: str = "similarity"  # similarity, keyword, hybrid
    limit: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Search query must be at least 2 characters')
        return v.strip()
    
    @validator('search_type')
    def validate_search_type(cls, v):
        if v not in ["similarity", "keyword", "hybrid"]:
            raise ValueError('Search type must be similarity, keyword, or hybrid')
        return v


class DocumentSearchResponse(BaseModel):
    """Schema for document search response"""
    query: str
    results: List[Dict[str, Any]]
    total_matches: int
    search_time_ms: float


class DocumentProcessingStatus(BaseModel):
    """Schema for document processing status"""
    document_id: int
    status: str
    progress_percentage: float
    current_step: str
    error_message: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class DocumentExtractionResult(BaseModel):
    """Schema for document extraction results"""
    document_id: int
    extracted_text: str
    metadata: Dict[str, Any]
    entities: List[Dict[str, Any]]
    keywords: List[str]
    summary: Optional[str] = None
    confidence_score: float


class DocumentComparisonRequest(BaseModel):
    """Schema for comparing documents"""
    document_ids: List[int]
    comparison_type: str = "content"  # content, metadata, structure
    
    @validator('document_ids')
    def validate_document_ids(cls, v):
        if len(v) < 2:
            raise ValueError('At least 2 documents required for comparison')
        return v


class DocumentComparisonResponse(BaseModel):
    """Schema for document comparison response"""
    document_ids: List[int]
    similarity_scores: Dict[str, float]
    common_entities: List[str]
    unique_entities: Dict[int, List[str]]
    content_overlap: float
    differences: List[Dict[str, Any]]


class DocumentBatchOperation(BaseModel):
    """Schema for batch operations on documents"""
    document_ids: List[int]
    operation: str  # reprocess, delete, update_metadata, export
    parameters: Optional[Dict[str, Any]] = None
    
    @validator('document_ids')
    def validate_document_ids(cls, v):
        if not v:
            raise ValueError('At least one document ID required')
        return v
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_ops = ["reprocess", "delete", "update_metadata", "export"]
        if v not in allowed_ops:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_ops)}')
        return v


class DocumentVersionInfo(BaseModel):
    """Schema for document version information"""
    document_id: int
    version: str
    hash: str
    size: int
    modified_at: datetime
    changes: List[str]


class DocumentAnalytics(BaseModel):
    """Schema for document analytics"""
    project_id: int
    total_documents: int
    documents_by_type: Dict[str, int]
    processing_status_distribution: Dict[str, int]
    total_size_bytes: int
    average_processing_time: float
    most_referenced_documents: List[Dict[str, Any]]
    upload_trends: List[Dict[str, Any]]