from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class EntityType(PyEnum):
    """Knowledge graph entity types"""
    PROJECT = "project"
    REQUIREMENT = "requirement"
    FEATURE = "feature"
    USER_STORY = "user_story"
    STAKEHOLDER = "stakeholder"
    BUSINESS_RULE = "business_rule"
    DEPENDENCY = "dependency"
    RISK = "risk"
    PERSONA = "persona"
    SYSTEM = "system"
    PROCESS = "process"


class RelationshipType(PyEnum):
    """Knowledge graph relationship types"""
    BELONGS_TO = "belongs_to"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    INVOLVES = "involves"
    CONFLICTS_WITH = "conflicts_with"
    DERIVES_FROM = "derives_from"
    RELATES_TO = "relates_to"
    BLOCKS = "blocks"
    ENABLES = "enables"
    VALIDATES = "validates"


class KnowledgeGraphEntity(Base):
    """Knowledge graph entities stored in relational database for caching/indexing"""
    __tablename__ = "kg_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Entity identification
    kg_id = Column(String(100), unique=True, nullable=False, index=True)  # Neo4j node ID
    entity_type = Column(String(50), nullable=False, index=True)
    name = Column(String(500), nullable=False, index=True)
    
    # Entity properties
    properties = Column(JSON, default=dict)  # All entity properties
    description = Column(Text, nullable=True)
    
    # Source information
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    source_user_story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=True)
    
    # Entity metadata
    confidence_score = Column(Float, default=1.0)  # Confidence in entity extraction
    importance_score = Column(Float, default=0.5)  # Relative importance
    
    # Sync status with Neo4j
    is_synced = Column(Boolean, default=False)
    last_synced = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project")
    source_document = relationship("Document")
    source_user_story = relationship("UserStory")
    outgoing_relationships = relationship("KnowledgeGraphRelationship", 
                                        foreign_keys="KnowledgeGraphRelationship.source_entity_id",
                                        back_populates="source_entity")
    incoming_relationships = relationship("KnowledgeGraphRelationship", 
                                        foreign_keys="KnowledgeGraphRelationship.target_entity_id",
                                        back_populates="target_entity")
    
    def __repr__(self):
        return f"<KGEntity(type='{self.entity_type}', name='{self.name}')>"
    
    def to_dict(self):
        """Convert entity to dictionary"""
        return {
            "id": self.id,
            "kg_id": self.kg_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "properties": self.properties,
            "description": self.description,
            "project_id": self.project_id,
            "source_document_id": self.source_document_id,
            "source_user_story_id": self.source_user_story_id,
            "confidence_score": self.confidence_score,
            "importance_score": self.importance_score,
            "is_synced": self.is_synced,
            "last_synced": self.last_synced,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class KnowledgeGraphRelationship(Base):
    """Knowledge graph relationships stored in relational database"""
    __tablename__ = "kg_relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationship identification
    kg_id = Column(String(100), unique=True, nullable=False, index=True)  # Neo4j relationship ID
    relationship_type = Column(String(50), nullable=False, index=True)
    
    # Connected entities
    source_entity_id = Column(Integer, ForeignKey("kg_entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("kg_entities.id"), nullable=False)
    
    # Relationship properties
    properties = Column(JSON, default=dict)
    description = Column(Text, nullable=True)
    
    # Relationship metadata
    confidence_score = Column(Float, default=1.0)
    strength = Column(Float, default=0.5)  # Relationship strength (0-1)
    
    # Source information
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    derived_from_document = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    # Sync status
    is_synced = Column(Boolean, default=False)
    last_synced = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    source_entity = relationship("KnowledgeGraphEntity", 
                               foreign_keys=[source_entity_id],
                               back_populates="outgoing_relationships")
    target_entity = relationship("KnowledgeGraphEntity", 
                               foreign_keys=[target_entity_id],
                               back_populates="incoming_relationships")
    project = relationship("Project")
    document = relationship("Document")
    
    def __repr__(self):
        return f"<KGRelationship(type='{self.relationship_type}', source={self.source_entity_id}, target={self.target_entity_id})>"
    
    def to_dict(self):
        """Convert relationship to dictionary"""
        return {
            "id": self.id,
            "kg_id": self.kg_id,
            "relationship_type": self.relationship_type,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "properties": self.properties,
            "description": self.description,
            "confidence_score": self.confidence_score,
            "strength": self.strength,
            "project_id": self.project_id,
            "derived_from_document": self.derived_from_document,
            "is_synced": self.is_synced,
            "last_synced": self.last_synced,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class KnowledgeGraphQuery(Base):
    """Stored queries and their results for caching"""
    __tablename__ = "kg_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Query information
    query_text = Column(Text, nullable=False)  # Cypher query or natural language
    query_type = Column(String(50), nullable=False)  # cypher, natural_language, template
    query_hash = Column(String(64), unique=True, nullable=False, index=True)  # Hash for caching
    
    # Query context
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Query results (cached)
    results = Column(JSON, nullable=True)
    result_count = Column(Integer, default=0)
    
    # Query metadata
    execution_time_ms = Column(Float, nullable=True)
    is_cached = Column(Boolean, default=False)
    cache_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project")
    user = relationship("User")
    
    def __repr__(self):
        return f"<KGQuery(type='{self.query_type}', project_id={self.project_id})>"
    
    def to_dict(self):
        """Convert query to dictionary"""
        return {
            "id": self.id,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "query_hash": self.query_hash,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "results": self.results,
            "result_count": self.result_count,
            "execution_time_ms": self.execution_time_ms,
            "is_cached": self.is_cached,
            "cache_expires_at": self.cache_expires_at,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class KnowledgeGraphSchema(Base):
    """Schema definitions for knowledge graph structure"""
    __tablename__ = "kg_schemas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Schema information
    name = Column(String(100), nullable=False, unique=True, index=True)
    version = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    
    # Schema definition
    entity_types = Column(JSON, nullable=False)  # Allowed entity types and properties
    relationship_types = Column(JSON, nullable=False)  # Allowed relationship types
    constraints = Column(JSON, default=dict)  # Schema constraints
    
    # Schema status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<KGSchema(name='{self.name}', version='{self.version}')>"
    
    def to_dict(self):
        """Convert schema to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entity_types": self.entity_types,
            "relationship_types": self.relationship_types,
            "constraints": self.constraints,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }