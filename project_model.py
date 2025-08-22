from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class ProjectStatus(PyEnum):
    """Project status enumeration"""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(PyEnum):
    """Project priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Project(Base):
    """Project model for organizing user stories and requirements"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Project metadata
    key = Column(String(20), unique=True, nullable=False, index=True)  # Project key like "PROJ-1"
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING)
    priority = Column(Enum(ProjectPriority), default=ProjectPriority.MEDIUM)
    
    # Ownership and collaboration
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Project configuration
    settings = Column(JSON, default=dict)  # Project-specific settings
    
    # Integration settings
    jira_project_key = Column(String(50), nullable=True)
    confluence_space_key = Column(String(50), nullable=True)
    sharepoint_site_path = Column(String(255), nullable=True)
    
    # AI and RAG configuration
    llm_provider = Column(String(50), nullable=True)  # Override default LLM
    llm_model = Column(String(100), nullable=True)
    rag_settings = Column(JSON, default=dict)  # RAG-specific settings
    
    # Knowledge graph ID for Neo4j
    kg_project_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project")
    user_stories = relationship("UserStory", back_populates="project")
    collaborators = relationship("ProjectCollaborator", back_populates="project")
    
    def __repr__(self):
        return f"<Project(key='{self.key}', name='{self.name}')>"
    
    def to_dict(self):
        """Convert project to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "key": self.key,
            "status": self.status.value if self.status else None,
            "priority": self.priority.value if self.priority else None,
            "owner_id": self.owner_id,
            "settings": self.settings,
            "jira_project_key": self.jira_project_key,
            "confluence_space_key": self.confluence_space_key,
            "sharepoint_site_path": self.sharepoint_site_path,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "rag_settings": self.rag_settings,
            "kg_project_id": self.kg_project_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ProjectCollaborator(Base):
    """Project collaborators with role-based permissions"""
    __tablename__ = "project_collaborators"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Role and permissions
    role = Column(String(50), default="viewer")  # owner, editor, viewer
    permissions = Column(JSON, default=list)  # Specific permissions list
    
    # Status
    is_active = Column(Boolean, default=True)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id])
    invited_by_user = relationship("User", foreign_keys=[invited_by])
    
    def __repr__(self):
        return f"<ProjectCollaborator(project_id={self.project_id}, user_id={self.user_id}, role='{self.role}')>"
    
    def to_dict(self):
        """Convert collaborator to dictionary"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "invited_by": self.invited_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ProjectTemplate(Base):
    """Project templates for quick project setup"""
    __tablename__ = "project_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Template configuration
    template_data = Column(JSON, nullable=False)  # Complete template structure
    category = Column(String(100), nullable=True)  # web_app, mobile_app, etc.
    
    # Template metadata
    is_public = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    
    def __repr__(self):
        return f"<ProjectTemplate(name='{self.name}', category='{self.category}')>"
    
    def to_dict(self):
        """Convert template to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_data": self.template_data,
            "category": self.category,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }