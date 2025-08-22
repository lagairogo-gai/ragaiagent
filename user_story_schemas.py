from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserStoryBase(BaseModel):
    """Base user story schema"""
    title: str
    persona: str
    functionality: str
    benefit: str
    description: Optional[str] = None
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters')
        return v.strip()
    
    @validator('persona', 'functionality', 'benefit')
    def validate_required_fields(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Field must not be empty')
        return v.strip()


class UserStoryCreate(UserStoryBase):
    """Schema for creating a user story"""
    project_id: int
    acceptance_criteria: Optional[List[str]] = []
    definition_of_done: Optional[List[str]] = []
    priority: Optional[str] = "medium"
    story_points: Optional[int] = None
    business_value: Optional[int] = None
    tags: Optional[List[str]] = []
    epic: Optional[str] = None
    theme: Optional[str] = None
    feature: Optional[str] = None
    complexity: Optional[str] = "medium"
    risk_level: Optional[str] = "low"
    estimated_hours: Optional[float] = None
    assigned_to_user_id: Optional[int] = None


class UserStoryUpdate(BaseModel):
    """Schema for updating a user story"""
    title: Optional[str] = None
    persona: Optional[str] = None
    functionality: Optional[str] = None
    benefit: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    definition_of_done: Optional[List[str]] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    business_value: Optional[int] = None
    tags: Optional[List[str]] = None
    epic: Optional[str] = None
    theme: Optional[str] = None
    feature: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    estimated_hours: Optional[float] = None
    assigned_to_user_id: Optional[int] = None
    change_description: Optional[str] = None


class UserStoryResponse(UserStoryBase):
    """Schema for user story response"""
    id: int
    story_text: str
    status: str
    priority: str
    story_points: Optional[int] = None
    business_value: Optional[int] = None
    generated_by_ai: bool
    confidence_score: Optional[float] = None
    quality_score: Optional[float] = None
    clarity_score: Optional[float] = None
    completeness_score: Optional[float] = None
    testability_score: Optional[float] = None
    project_id: int
    created_by_user_id: int
    assigned_to_user_id: Optional[int] = None
    jira_issue_key: Optional[str] = None
    external_url: Optional[str] = None
    acceptance_criteria: List[str] = []
    definition_of_done: List[str] = []
    tags: List[str] = []
    epic: Optional[str] = None
    theme: Optional[str] = None
    feature: Optional[str] = None
    complexity: Optional[str] = None
    risk_level: Optional[str] = None
    estimated_hours: Optional[float] = None
    source_documents: List[int] = []
    depends_on: List[int] = []
    blocks: List[int] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserStoryListResponse(BaseModel):
    """Response for user story list"""
    stories: List[UserStoryResponse]
    total: int
    skip: int
    limit: int


class UserStoryGenerationRequest(BaseModel):
    """Schema for user story generation request"""
    requirements: str
    project_id: int
    persona: Optional[str] = None
    additional_context: Optional[str] = None
    generation_options: Optional[Dict[str, Any]] = None
    
    @validator('requirements')
    def validate_requirements(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Requirements must be at least 10 characters')
        return v.strip()


class UserStoryGenerationResponse(BaseModel):
    """Schema for user story generation response"""
    success: bool
    stories_count: int
    generated_stories: List[Dict[str, Any]]
    generation_metadata: Dict[str, Any]
    quality_scores: Dict[str, Any]
    context_documents: List[Dict[str, Any]]
    messages: List[str]
    errors: List[str]
    warnings: List[str]


class UserStoryCommentBase(BaseModel):
    """Base comment schema"""
    comment_text: str
    comment_type: Optional[str] = "general"
    
    @validator('comment_text')
    def validate_comment_text(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Comment text cannot be empty')
        return v.strip()


class UserStoryCommentCreate(UserStoryCommentBase):
    """Schema for creating a comment"""
    parent_comment_id: Optional[int] = None


class UserStoryCommentResponse(UserStoryCommentBase):
    """Schema for comment response"""
    id: int
    user_story_id: int
    user_id: int
    is_resolved: bool
    parent_comment_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserStoryQualityCheck(BaseModel):
    """Schema for quality check results"""
    story_id: int
    overall_score: float
    invest_scores: Dict[str, float]
    feedback: List[str]
    suggestions: List[str]
    risk_assessment: str


class UserStoryVersion(BaseModel):
    """Schema for user story version"""
    id: int
    user_story_id: int
    version_number: int
    change_description: Optional[str] = None
    changed_by_user_id: int
    story_data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserStoryDependency(BaseModel):
    """Schema for user story dependencies"""
    source_story_id: int
    target_story_id: int
    dependency_type: str  # blocks, depends_on, relates_to
    description: Optional[str] = None


class UserStoryExportRequest(BaseModel):
    """Schema for exporting user stories"""
    story_ids: List[int]
    export_format: str  # jira, csv, json
    include_comments: bool = False
    include_versions: bool = False


class UserStoryBulkUpdate(BaseModel):
    """Schema for bulk updating user stories"""
    story_ids: List[int]
    updates: UserStoryUpdate
    
    @validator('story_ids')
    def validate_story_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one story ID must be provided')
        return v


class UserStoryAnalytics(BaseModel):
    """Schema for user story analytics"""
    project_id: int
    total_stories: int
    status_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    complexity_distribution: Dict[str, int]
    ai_vs_manual: Dict[str, int]
    average_story_points: Optional[float] = None
    average_quality_score: Optional[float] = None
    completion_rate: float
    velocity_trend: List[Dict[str, Any]]


class UserStorySearch(BaseModel):
    """Schema for user story search"""
    query: str
    project_id: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = "relevance"
    limit: int = 20
    
    @validator('query')
    def validate_query(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Search query must be at least 2 characters')
        return v.strip()


class UserStorySearchResponse(BaseModel):
    """Schema for user story search response"""
    query: str
    results: List[Dict[str, Any]]
    total_matches: int
    search_time_ms: float
    suggestions: List[str] = []


class UserStoryTemplate(BaseModel):
    """Schema for user story templates"""
    name: str
    description: Optional[str] = None
    persona_template: str
    functionality_template: str
    benefit_template: str
    acceptance_criteria_template: List[str] = []
    tags: List[str] = []
    category: Optional[str] = None
    is_public: bool = False


class UserStoryTemplateResponse(UserStoryTemplate):
    """Schema for user story template response"""
    id: int
    created_by: int
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True