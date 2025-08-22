from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import structlog
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models.user import User
from ...models.project import Project
from ...models.user_story import UserStory, UserStoryComment, UserStoryVersion
from ...models.document import Document
from ...schemas.user_story import (
    UserStoryCreate, UserStoryUpdate, UserStoryResponse,
    UserStoryListResponse, UserStoryGenerationRequest,
    UserStoryGenerationResponse, UserStoryCommentCreate,
    UserStoryCommentResponse, UserStoryQualityCheck
)
from ...agents.user_story_agent import user_story_agent
from ...services.rag_service import rag_service
from ...services.knowledge_graph_service import knowledge_graph_service

logger = structlog.get_logger()
router = APIRouter()


@router.post("/generate", response_model=UserStoryGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_user_stories(
    generation_request: UserStoryGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate user stories using AI agent"""
    
    # Verify project access
    project = db.query(Project).filter(
        Project.id == generation_request.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    try:
        logger.info("Starting user story generation",
                   project_id=generation_request.project_id,
                   user_id=current_user.id)
        
        # Generate user stories using the agent
        generation_result = await user_story_agent.generate_user_stories(
            requirements=generation_request.requirements,
            project_id=generation_request.project_id,
            user_id=current_user.id,
            persona=generation_request.persona,
            additional_context=generation_request.additional_context,
            generation_options=generation_request.generation_options or {}
        )
        
        # Save generated stories to database
        saved_stories = []
        if generation_result["success"] and generation_result["user_stories"]:
            for story_data in generation_result["user_stories"]:
                # Create user story record
                user_story = UserStory(
                    title=story_data.get("title", "Generated User Story"),
                    persona=story_data.get("persona", "User"),
                    functionality=story_data.get("functionality", ""),
                    benefit=story_data.get("benefit", ""),
                    story_text=story_data.get("story_text", ""),
                    description=story_data.get("description"),
                    acceptance_criteria=story_data.get("acceptance_criteria", []),
                    priority=story_data.get("priority", "medium"),
                    story_points=story_data.get("estimated_points"),
                    complexity=story_data.get("complexity", "medium"),
                    generated_by_ai=True,
                    generation_prompt=generation_request.requirements,
                    generation_context=generation_result.get("metadata", {}),
                    confidence_score=story_data.get("confidence_score", 0.8),
                    project_id=generation_request.project_id,
                    created_by_user_id=current_user.id,
                    tags=story_data.get("tags", []),
                    source_documents=[doc["metadata"]["document_id"] for doc in generation_result.get("context_documents", []) if "document_id" in doc.get("metadata", {})],
                    kg_story_id=None  # Will be set in background task
                )
                
                db.add(user_story)
                db.commit()
                db.refresh(user_story)
                saved_stories.append(user_story)
        
        # Schedule background tasks
        if saved_stories:
            for story in saved_stories:
                background_tasks.add_task(
                    _create_knowledge_graph_entities,
                    story.id,
                    generation_result.get("knowledge_graph_entities", [])
                )
        
        logger.info("User story generation completed",
                   project_id=generation_request.project_id,
                   stories_generated=len(saved_stories))
        
        return UserStoryGenerationResponse(
            success=generation_result["success"],
            stories_count=len(saved_stories),
            generated_stories=[story.to_dict() for story in saved_stories],
            generation_metadata=generation_result.get("metadata", {}),
            quality_scores=generation_result.get("quality_scores", {}),
            context_documents=generation_result.get("context_documents", []),
            messages=generation_result.get("messages", []),
            errors=generation_result.get("errors", []),
            warnings=generation_result.get("warnings", [])
        )
        
    except Exception as e:
        logger.error("User story generation failed",
                    project_id=generation_request.project_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Story generation failed: {str(e)}"
        )


@router.get("/", response_model=UserStoryListResponse)
async def list_user_stories(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    skip: int = Query(0, ge=0, description="Number of stories to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of stories to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user stories with filtering and pagination"""
    
    # Build query
    query = db.query(UserStory)
    
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
        query = query.filter(UserStory.project_id == project_id)
    else:
        # Show only stories from user's projects
        user_project_ids = db.query(Project.id).filter(Project.owner_id == current_user.id).subquery()
        query = query.filter(UserStory.project_id.in_(user_project_ids))
    
    # Apply filters
    if status:
        query = query.filter(UserStory.status == status)
    if priority:
        query = query.filter(UserStory.priority == priority)
    if assigned_to:
        query = query.filter(UserStory.assigned_to_user_id == assigned_to)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (UserStory.title.ilike(search_filter)) |
            (UserStory.description.ilike(search_filter)) |
            (UserStory.story_text.ilike(search_filter))
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    stories = query.order_by(UserStory.created_at.desc()).offset(skip).limit(limit).all()
    
    return UserStoryListResponse(
        stories=[story.to_dict() for story in stories],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{story_id}", response_model=UserStoryResponse)
async def get_user_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    return story.to_dict()


@router.put("/{story_id}", response_model=UserStoryResponse)
async def update_user_story(
    story_id: int,
    story_update: UserStoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    # Create version history before updating
    version = UserStoryVersion(
        user_story_id=story.id,
        version_number=len(story.versions) + 1,
        change_description=story_update.change_description or "Updated via API",
        changed_by_user_id=current_user.id,
        story_data=story.to_dict()
    )
    db.add(version)
    
    # Update story fields
    update_data = story_update.dict(exclude_unset=True, exclude={"change_description"})
    for field, value in update_data.items():
        setattr(story, field, value)
    
    story.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(story)
    
    logger.info("User story updated",
               story_id=story.id,
               user_id=current_user.id,
               fields_updated=list(update_data.keys()))
    
    return story.to_dict()


@router.delete("/{story_id}")
async def delete_user_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    db.delete(story)
    db.commit()
    
    logger.info("User story deleted", story_id=story.id, user_id=current_user.id)
    
    return {"message": "User story deleted successfully"}


@router.post("/{story_id}/comments", response_model=UserStoryCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    story_id: int,
    comment_data: UserStoryCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    comment = UserStoryComment(
        user_story_id=story_id,
        user_id=current_user.id,
        comment_text=comment_data.comment_text,
        comment_type=comment_data.comment_type,
        parent_comment_id=comment_data.parent_comment_id
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return comment.to_dict()


@router.get("/{story_id}/comments", response_model=List[UserStoryCommentResponse])
async def get_comments(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comments for a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    comments = db.query(UserStoryComment).filter(
        UserStoryComment.user_story_id == story_id
    ).order_by(UserStoryComment.created_at.asc()).all()
    
    return [comment.to_dict() for comment in comments]


@router.post("/{story_id}/enhance")
async def enhance_user_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enhance user story with additional context from RAG"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    try:
        enhancement_result = await rag_service.enhance_user_story_with_context(story, db)
        
        logger.info("User story enhanced",
                   story_id=story.id,
                   context_found=enhancement_result["context_found"])
        
        return {
            "story_id": story_id,
            "enhancement_suggestions": enhancement_result,
            "message": "Enhancement completed successfully"
        }
        
    except Exception as e:
        logger.error("User story enhancement failed", story_id=story.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhancement failed: {str(e)}"
        )


@router.post("/{story_id}/quality-check", response_model=UserStoryQualityCheck)
async def perform_quality_check(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Perform quality check on a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    try:
        from ...agents.quality_checker import quality_checker
        
        quality_result = await quality_checker.check_user_story_quality(story.to_dict())
        
        # Update story with quality scores
        if quality_result.get("scores"):
            story.quality_score = quality_result["scores"].get("overall_score")
            story.clarity_score = quality_result["scores"].get("clarity_score")
            story.completeness_score = quality_result["scores"].get("completeness_score")
            story.testability_score = quality_result["scores"].get("testability_score")
            db.commit()
        
        logger.info("Quality check completed",
                   story_id=story.id,
                   overall_score=quality_result.get("scores", {}).get("overall_score"))
        
        return UserStoryQualityCheck(
            story_id=story_id,
            overall_score=quality_result.get("scores", {}).get("overall_score", 0),
            invest_scores=quality_result.get("invest_scores", {}),
            feedback=quality_result.get("feedback", []),
            suggestions=quality_result.get("suggestions", []),
            risk_assessment=quality_result.get("risk_assessment", "medium")
        )
        
    except Exception as e:
        logger.error("Quality check failed", story_id=story.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality check failed: {str(e)}"
        )


@router.get("/{story_id}/versions")
async def get_story_versions(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get version history for a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    versions = db.query(UserStoryVersion).filter(
        UserStoryVersion.user_story_id == story_id
    ).order_by(UserStoryVersion.version_number.desc()).all()
    
    return [version.to_dict() for version in versions]


@router.get("/{story_id}/related-entities")
async def get_related_entities(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get knowledge graph entities related to a user story"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    try:
        # Get entity recommendations for this story
        story_text = f"{story.title} {story.story_text} {story.description or ''}"
        entities = await knowledge_graph_service.get_entity_recommendations(
            user_story_text=story_text,
            project_id=story.project_id,
            limit=10
        )
        
        return {
            "story_id": story_id,
            "related_entities": entities,
            "total_found": len(entities)
        }
        
    except Exception as e:
        logger.error("Failed to get related entities", story_id=story.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related entities: {str(e)}"
        )


@router.post("/{story_id}/export-jira")
async def export_to_jira(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export user story to Jira"""
    
    # Check access through project ownership
    story = db.query(UserStory).join(Project).filter(
        UserStory.id == story_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found or access denied"
        )
    
    try:
        from ...services.jira_service import jira_service
        
        # Export to Jira
        jira_result = await jira_service.create_issue_from_user_story(
            user_story=story,
            project_key=story.project.jira_project_key
        )
        
        if jira_result["success"]:
            # Update story with Jira issue key
            story.jira_issue_key = jira_result["issue_key"]
            story.external_url = jira_result["issue_url"]
            db.commit()
            
            logger.info("User story exported to Jira",
                       story_id=story.id,
                       jira_key=jira_result["issue_key"])
            
            return {
                "success": True,
                "jira_issue_key": jira_result["issue_key"],
                "jira_url": jira_result["issue_url"],
                "message": "Story exported to Jira successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Jira export failed: {jira_result.get('error', 'Unknown error')}"
            )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Jira integration not available"
        )
    except Exception as e:
        logger.error("Jira export failed", story_id=story.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Jira export failed: {str(e)}"
        )


@router.get("/analytics/project/{project_id}")
async def get_project_analytics(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get analytics for user stories in a project"""
    
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
    
    try:
        # Get basic statistics
        total_stories = db.query(UserStory).filter(UserStory.project_id == project_id).count()
        
        # Status distribution
        status_query = db.query(
            UserStory.status,
            db.func.count(UserStory.id).label('count')
        ).filter(UserStory.project_id == project_id).group_by(UserStory.status).all()
        
        status_distribution = {status: count for status, count in status_query}
        
        # Priority distribution
        priority_query = db.query(
            UserStory.priority,
            db.func.count(UserStory.id).label('count')
        ).filter(UserStory.project_id == project_id).group_by(UserStory.priority).all()
        
        priority_distribution = {priority: count for priority, count in priority_query}
        
        # Quality scores
        quality_query = db.query(
            db.func.avg(UserStory.quality_score).label('avg_quality'),
            db.func.avg(UserStory.clarity_score).label('avg_clarity'),
            db.func.avg(UserStory.completeness_score).label('avg_completeness'),
            db.func.avg(UserStory.testability_score).label('avg_testability')
        ).filter(
            UserStory.project_id == project_id,
            UserStory.quality_score.isnot(None)
        ).first()
        
        # AI vs Manual stories
        ai_stories = db.query(UserStory).filter(
            UserStory.project_id == project_id,
            UserStory.generated_by_ai == True
        ).count()
        
        manual_stories = total_stories - ai_stories
        
        # Story points distribution
        points_query = db.query(
            UserStory.story_points,
            db.func.count(UserStory.id).label('count')
        ).filter(
            UserStory.project_id == project_id,
            UserStory.story_points.isnot(None)
        ).group_by(UserStory.story_points).all()
        
        points_distribution = {points: count for points, count in points_query}
        
        return {
            "project_id": project_id,
            "summary": {
                "total_stories": total_stories,
                "ai_generated": ai_stories,
                "manually_created": manual_stories,
                "avg_quality_score": float(quality_query.avg_quality) if quality_query.avg_quality else None,
                "avg_clarity_score": float(quality_query.avg_clarity) if quality_query.avg_clarity else None,
                "avg_completeness_score": float(quality_query.avg_completeness) if quality_query.avg_completeness else None,
                "avg_testability_score": float(quality_query.avg_testability) if quality_query.avg_testability else None
            },
            "distributions": {
                "status": status_distribution,
                "priority": priority_distribution,
                "story_points": points_distribution
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Analytics generation failed", project_id=project_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {str(e)}"
        )


# Background task functions
async def _create_knowledge_graph_entities(story_id: int, entities: List[Dict[str, Any]]):
    """Background task to create knowledge graph entities for a user story"""
    try:
        db = next(get_db())
        story = db.query(UserStory).filter(UserStory.id == story_id).first()
        
        if story and entities:
            # Create entities in knowledge graph
            entity_ids = []
            for entity in entities:
                try:
                    entity_id = await knowledge_graph_service.create_entity(
                        name=entity["name"],
                        entity_type=entity["type"],
                        properties=entity.get("properties", {}),
                        project_id=story.project_id,
                        description=entity.get("description")
                    )
                    entity_ids.append(entity_id)
                except Exception as e:
                    logger.warning("Failed to create KG entity", entity_name=entity["name"], error=str(e))
            
            # Update story with KG reference
            if entity_ids:
                story.kg_story_id = entity_ids[0]  # Use first entity as primary reference
                db.commit()
                
                logger.info("Knowledge graph entities created for story",
                           story_id=story_id,
                           entities_created=len(entity_ids))
        
        db.close()
        
    except Exception as e:
        logger.error("Background KG entity creation failed", story_id=story_id, error=str(e))