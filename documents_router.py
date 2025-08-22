from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
import os
import uuid
import shutil
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_active_user
from ...core.config import settings
from ...models.user import User
from ...models.project import Project
from ...models.document import Document, DocumentChunk, DocumentAnnotation
from ...schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentCreate,
    DocumentUpdate, DocumentAnnotationCreate, DocumentAnnotationResponse
)
from ...services.rag_service import rag_service
from ...utils.text_processing import extract_text_from_file, get_file_type

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    project_id: int = Form(...),
    document_type: str = Form("other"),
    title: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document"""
    
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = get_file_type(file_path)
        
        # Extract text content
        try:
            extracted_text = extract_text_from_file(file_path, file_extension)
        except Exception as e:
            logger.warning("Text extraction failed", filename=file.filename, error=str(e))
            extracted_text = ""
        
        # Create document record
        document = Document(
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            document_type=document_type,
            title=title or file.filename,
            content=extracted_text,
            status="uploaded" if extracted_text else "processing",
            project_id=project_id,
            uploaded_by_id=current_user.id,
            source_type="upload"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Schedule background processing
        background_tasks.add_task(
            _process_document_background,
            document.id
        )
        
        logger.info("Document uploaded successfully",
                   document_id=document.id,
                   filename=file.filename,
                   project_id=project_id,
                   user_id=current_user.id)
        
        return document.to_dict()
        
    except Exception as e:
        # Clean up file if database operation failed
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        
        logger.error("Document upload failed", filename=file.filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of documents to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List documents with filtering and pagination"""
    
    # Build query
    query = db.query(Document)
    
    # Filter by project access
    if project_id:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        query = query.filter(Document.project_id == project_id)
    else:
        # Show only documents from user's projects
        user_project_ids = db.query(Project.id).filter(Project.owner_id == current_user.id).subquery()
        query = query.filter(Document.project_id.in_(user_project_ids))
    
    # Apply filters
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if status:
        query = query.filter(Document.status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Document.title.ilike(search_filter)) |
            (Document.content.ilike(search_filter))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        documents=[doc.to_dict() for doc in documents],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific document"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    return document.to_dict()


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update document metadata"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # Update document fields
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    
    logger.info("Document updated",
               document_id=document.id,
               user_id=current_user.id,
               fields_updated=list(update_data.keys()))
    
    return document.to_dict()


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # Delete file from disk
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        logger.warning("Failed to delete document file", file_path=document.file_path, error=str(e))
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    logger.info("Document deleted", document_id=document.id, user_id=current_user.id)
    
    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document for RAG indexing"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # Reset processing status
    document.status = "processing"
    document.embeddings_generated = False
    document.processing_error = None
    db.commit()
    
    # Schedule reprocessing
    background_tasks.add_task(_process_document_background, document.id)
    
    logger.info("Document reprocessing scheduled", document_id=document.id)
    
    return {"message": "Document reprocessing scheduled"}


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get chunks for a document"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    # Get chunks
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).offset(skip).limit(limit).all()
    
    total_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).count()
    
    return {
        "document_id": document_id,
        "chunks": [chunk.to_dict() for chunk in chunks],
        "total": total_chunks,
        "skip": skip,
        "limit": limit
    }


@router.post("/{document_id}/annotations", response_model=DocumentAnnotationResponse, status_code=status.HTTP_201_CREATED)
async def add_annotation(
    document_id: int,
    annotation_data: DocumentAnnotationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add an annotation to a document"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    annotation = DocumentAnnotation(
        document_id=document_id,
        user_id=current_user.id,
        annotation_text=annotation_data.annotation_text,
        annotation_type=annotation_data.annotation_type,
        start_position=annotation_data.start_position,
        end_position=annotation_data.end_position,
        selected_text=annotation_data.selected_text,
        tags=annotation_data.tags or []
    )
    
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    
    logger.info("Document annotation added",
               document_id=document_id,
               annotation_id=annotation.id,
               user_id=current_user.id)
    
    return annotation.to_dict()


@router.get("/{document_id}/annotations", response_model=List[DocumentAnnotationResponse])
async def get_annotations(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get annotations for a document"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    annotations = db.query(DocumentAnnotation).filter(
        DocumentAnnotation.document_id == document_id
    ).order_by(DocumentAnnotation.created_at.desc()).all()
    
    return [annotation.to_dict() for annotation in annotations]


@router.get("/{document_id}/search")
async def search_document_content(
    document_id: int,
    query: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search within document content"""
    
    # Check access through project ownership
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied"
        )
    
    if not document.content:
        return {
            "document_id": document_id,
            "query": query,
            "matches": [],
            "total_matches": 0
        }
    
    # Simple text search (could be enhanced with more sophisticated search)
    content = document.content.lower()
    query_lower = query.lower()
    
    matches = []
    start = 0
    while True:
        pos = content.find(query_lower, start)
        if pos == -1:
            break
        
        # Extract context around the match
        context_start = max(0, pos - 50)
        context_end = min(len(content), pos + len(query) + 50)
        context = document.content[context_start:context_end]
        
        matches.append({
            "position": pos,
            "context": context,
            "highlight_start": pos - context_start,
            "highlight_end": pos - context_start + len(query)
        })
        
        start = pos + 1
    
    return {
        "document_id": document_id,
        "query": query,
        "matches": matches,
        "total_matches": len(matches)
    }


# Background task functions
async def _process_document_background(document_id: int):
    """Background task to process document for RAG"""
    try:
        db = next(get_db())
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            logger.error("Document not found for processing", document_id=document_id)
            return
        
        logger.info("Starting document processing", document_id=document_id)
        
        # Update status
        document.status = "processing"
        db.commit()
        
        # Process and index document
        success = await rag_service.process_and_index_document(document, db)
        
        if success:
            document.status = "processed"
            document.processed_at = datetime.utcnow()
            logger.info("Document processed successfully", document_id=document_id)
        else:
            document.status = "failed"
            document.processing_error = "Failed to process document for RAG indexing"
            logger.error("Document processing failed", document_id=document_id)
        
        db.commit()
        db.close()
        
    except Exception as e:
        logger.error("Background document processing failed", document_id=document_id, error=str(e))
        
        # Update status to failed
        try:
            db = next(get_db())
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                document.processing_error = str(e)
                db.commit()
            db.close()
        except Exception as update_error:
            logger.error("Failed to update document status", error=str(update_error))