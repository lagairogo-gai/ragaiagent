"""
RAG-Based AI Agent for User Story Generation - Project Architecture
================================================================

Directory Structure:
-------------------

rag-user-stories/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI main application
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Configuration settings
│   │   │   ├── database.py            # Database connection
│   │   │   └── security.py            # Authentication & JWT
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User model
│   │   │   ├── document.py            # Document model
│   │   │   ├── user_story.py          # User story model
│   │   │   ├── knowledge_graph.py     # Knowledge graph entities
│   │   │   └── project.py             # Project/workspace model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # Pydantic schemas
│   │   │   ├── document.py
│   │   │   ├── user_story.py
│   │   │   └── knowledge_graph.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py            # Authentication endpoints
│   │   │   │   ├── documents.py       # Document management
│   │   │   │   ├── user_stories.py    # User story generation
│   │   │   │   ├── integrations.py    # Jira, Confluence, SharePoint
│   │   │   │   └── knowledge_graph.py # Knowledge graph operations
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py         # LLM integration service
│   │   │   ├── rag_service.py         # RAG pipeline service
│   │   │   ├── knowledge_graph_service.py # KG operations
│   │   │   ├── jira_service.py        # Jira integration
│   │   │   ├── confluence_service.py  # Confluence integration
│   │   │   └── sharepoint_service.py  # SharePoint integration
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── user_story_agent.py    # Main agent using LangGraph
│   │   │   ├── document_processor.py  # Document processing agent
│   │   │   └── quality_checker.py     # User story quality checker
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── vector_store.py        # Vector database operations
│   │   │   ├── text_processing.py     # Text preprocessing
│   │   │   └── export_utils.py        # Export utilities
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_api.py
│   │       ├── test_services.py
│   │       └── test_agents.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── forms/
│   │   │   ├── visualization/
│   │   │   └── integrations/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── utils/
│   │   ├── styles/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── docs/
├── scripts/
└── README.md

Technology Stack:
----------------

Backend:
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- Alembic (Database migrations)
- PostgreSQL (Primary database)
- Redis (Caching & session storage)
- ChromaDB/Pinecone (Vector database)
- Neo4j (Knowledge graph database)
- LangChain (LLM framework)
- LangGraph (Agent framework)
- Celery (Background tasks)

Frontend:
- React 18 with TypeScript
- Tailwind CSS (Styling)
- React Query (State management)
- React Flow (Visual workflow)
- Framer Motion (Animations)
- Axios (HTTP client)

LLM Integrations:
- OpenAI GPT-4/3.5
- Azure OpenAI
- Google Gemini
- Anthropic Claude
- Local models via Ollama

External Integrations:
- Jira API
- Confluence API
- SharePoint API
- File upload handling

Knowledge Graph Schema:
----------------------

Entities:
- Project
- Requirement
- Feature
- UserStory
- Stakeholder
- BusinessRule
- Dependency
- Risk

Relationships:
- BELONGS_TO
- DEPENDS_ON
- IMPLEMENTS
- INVOLVES
- CONFLICTS_WITH
- DERIVES_FROM

Agent Workflow:
--------------

1. Document Ingestion
   - Parse uploaded documents
   - Extract requirements from Jira/Confluence
   - Build knowledge graph
   - Create vector embeddings

2. User Story Generation
   - Analyze user prompts
   - Retrieve relevant context via RAG
   - Query knowledge graph
   - Generate user stories using LLM
   - Validate and refine output

3. Export & Integration
   - Format user stories
   - Export to Jira
   - Update knowledge graph
   - Store generated artifacts

This architecture provides a scalable, modular system for enterprise-grade 
user story generation with comprehensive integrations and AI capabilities.
"""