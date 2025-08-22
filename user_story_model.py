from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class UserStoryStatus(PyEnum):
    """User story status enumeration"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IN_DEVELOPMENT = "in_development"
    TESTING = "testing"
    DONE = "done"
    REJECTED = "rejected"


class UserStoryPriority(PyEnum):
    """User story priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserStory(Base):
    """User story model for storing generated and managed user stories"""
    __tablename__ = "user_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    
    # Core user story components
    persona = Column(String(200), nullable=False)  # As a [persona]
    functionality = Column(Text, nullable=False)   # I want [functionality]
    benefit = Column(Text, nullable=False)         # So that [benefit]
    
    # Full user story text
    story_text = Column(Text, nullable=False)
    
    # Story details
    description = Column(Text, nullable=True)
    acceptance_criteria = Column(JSON, default=list)  # List of acceptance criteria
    definition_of_done = Column(JSON, default=list)   # List of DoD items
    
    # Story metadata
    status = Column(String(20), default=UserStoryStatus.DRAFT.value)
    priority = Column(String(20), default=UserStoryPriority.MEDIUM.value)
    story_points = Column(Integer, nullable=True)
    business_value = Column(Integer, nullable=True)  # 1-10 scale
    
    # AI generation metadata
    generated_by_ai = Column(Boolean, default=True)
    generation_prompt = Column(Text, nullable=True)  # Original prompt used
    generation_context = Column(JSON, default=dict)  # Context used for generation
    confidence_score = Column(Float, nullable=True)  # AI confidence in generation
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)     # Overall quality score
    clarity_score = Column(Float, nullable=True)     # Clarity of requirements
    completeness_score = Column(Float, nullable=True) # Completeness score
    testability_score = Column(Float, nullable=True)  # How testable the story is
    
    # Relationships
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # External system integration
    jira_issue_key = Column(String(50), nullable=True, index=True)
    external_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)
    
    # Knowledge graph integration
    kg_story_id = Column(String(100), nullable=True, index=True)
    
    # Source information
    source_documents = Column(JSON, default=list)  # Document IDs used for generation
    source_requirements = Column(JSON, default=list)  # Requirement IDs
    
    # Tags and categorization
    tags = Column(JSON, default=list)
    epic = Column(String(200), nullable=True)
    theme = Column(String(200), nullable=True)
    feature = Column(String(200), nullable=True)
    
    # Estimates and planning
    estimated_hours = Column(Float, nullable=True)
    complexity = Column(String(20), nullable=True)  # simple, medium, complex
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    
    # Dependencies
    depends_on = Column(JSON, default=list)  # List of story IDs this depends on
    blocks = Column(JSON, default=list)     # List of story IDs this blocks
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="user_stories")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="user_stories")
    assigned_to_user = relationship("User", foreign_keys=[assigned_to_user_id])
    comments = relationship("UserStoryComment", back_populates="user_story")
    versions = relationship("UserStoryVersion", back_populates="user_story")
    
    def __repr__(self):
        return f"<UserStory(title='{self.title}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert user story to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "persona": self.persona,
            "functionality": self.functionality,
            "benefit": self.benefit,
            "story_text": self.story_text,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "definition_of_done": self.definition_of_done,
            "status": self.status,
            "priority": self.priority,
            "story_points": self.story_points,
            "business_value": self.business_value,
            "generated_by_ai": self.generated_by_ai,
            "generation_prompt": self.generation_prompt,
            "generation_context": self.generation_context,
            "confidence_score": self.confidence_score,
            "quality_score": self.quality_score,
            "clarity_score": self.clarity_score,
            "completeness_score": self.completeness_score,
            "testability_score": self.testability_score,
            "project_id": self.project_id,
            "created_by_user_id": self.created_by_user_id,
            "assigned_to_user_id": self.assigned_to_user_id,
            "jira_issue_key": self.jira_issue_key,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "kg_story_id": self.kg_story_id,
            "source_documents": self.source_documents,
            "source_requirements": self.source_requirements,
            "tags": self.tags,
            "epic": self.epic,
            "theme": self.theme,
            "feature": self.feature,
            "estimated_hours": self.estimated_hours,
            "complexity": self.complexity,
            "risk_level": self.risk_level,
            "depends_on": self.depends_on,
            "blocks": self.blocks,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "completed_at": self.completed_at
        }
    
    def get_formatted_story(self) -> str:
        """Get formatted user story text"""
        return f"As a {self.persona}, I want {self.functionality} so that {self.benefit}."


class UserStoryComment(Base):
    """Comments and feedback on user stories"""
    __tablename__ = "user_story_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Comment content
    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(50), default="general")  # general, feedback, question, suggestion
    
    # Comment metadata
    is_resolved = Column(Boolean, default=False)
    parent_comment_id = Column(Integer, ForeignKey("user_story_comments.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_story = relationship("UserStory", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("UserStoryComment", remote_side=[id])
    replies = relationship("UserStoryComment", back_populates="parent_comment")
    
    def __repr__(self):
        return f"<UserStoryComment(story_id={self.user_story_id}, type='{self.comment_type}')>"
    
    def to_dict(self):
        """Convert comment to dictionary"""
        return {
            "id": self.id,
            "user_story_id": self.user_story_id,
            "user_id": self.user_id,
            "comment_text": self.comment_text,
            "comment_type": self.comment_type,
            "is_resolved": self.is_resolved,
            "parent_comment_id": self.parent_comment_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class UserStoryVersion(Base):
    """Version history for user stories"""
    __tablename__ = "user_story_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=False)
    
    # Version information
    version_number = Column(Integer, nullable=False)
    change_description = Column(Text, nullable=True)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Snapshot of story at this version
    story_data = Column(JSON, nullable=False)  # Complete story data snapshot
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user_story = relationship("UserStory", back_populates="versions")
    changed_by_user = relationship("User")
    
    def __repr__(self):
        return f"<UserStoryVersion(story_id={self.user_story_id}, version={self.version_number})>"
    
    def to_dict(self):
        """Convert version to dictionary"""
        return {
            "id": self.id,
            "user_story_id": self.user_story_id,
            "version_number": self.version_number,
            "change_description": self.change_description,
            "changed_by_user_id": self.changed_by_user_id,
            "story_data": self.story_data,
            "created_at": self.created_at
        }