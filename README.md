# RAG-Based AI Agent for User Story Generation

A comprehensive enterprise-grade application that uses Retrieval-Augmented Generation (RAG) and AI agents to automatically generate high-quality user stories from requirements documents and specifications.

## 🚀 Features

- **AI-Powered User Story Generation**: Uses advanced LLMs with RAG to generate contextual user stories
- **Multi-LLM Support**: Compatible with OpenAI GPT-4, Azure OpenAI, Google Gemini, Anthropic Claude, and local models via Ollama
- **Knowledge Graph Integration**: Builds and queries knowledge graphs using Neo4j for enhanced context understanding
- **Document Processing**: Supports PDF, DOCX, TXT, MD, XLSX, and CSV file uploads with intelligent text extraction
- **External Integrations**: Direct integration with Jira, Confluence, and SharePoint for seamless workflow
- **Quality Assessment**: Automated quality checking using INVEST criteria and other best practices
- **Real-time Collaboration**: Multi-user support with role-based access control
- **Enterprise Security**: JWT authentication, API keys, and comprehensive audit logging
- **Scalable Architecture**: Microservices design with Docker containerization and monitoring

## 🏗️ Architecture

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy + Alembic (Database ORM & migrations)
- PostgreSQL (Primary database)
- Redis (Caching & session storage)
- Neo4j (Knowledge graph database)
- ChromaDB/Pinecone (Vector database)
- LangChain + LangGraph (LLM framework & agent orchestration)
- Celery (Background task processing)

**Frontend:**
- React 18 with TypeScript
- Tailwind CSS for styling
- React Query for state management
- React Flow for visual workflows
- Framer Motion for animations

**Infrastructure:**
- Docker & Docker Compose
- Nginx (Reverse proxy)
- Prometheus + Grafana (Monitoring)
- Elasticsearch + Kibana (Optional advanced search)

### Core Components

1. **AI Agent Workflow**: LangGraph-based agent that orchestrates the entire user story generation process
2. **RAG Service**: Retrieval-augmented generation using vector similarity search
3. **Knowledge Graph Service**: Entity extraction and relationship mapping
4. **Document Processor**: Intelligent text extraction and chunking
5. **LLM Service**: Multi-provider LLM abstraction layer
6. **Integration Services**: External system connectors (Jira, Confluence, SharePoint)

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- At least one LLM API key (OpenAI, Azure OpenAI, etc.)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rag-user-stories
```

### 2. Environment Setup

```bash
# Copy the environment template
cp .env.template .env

# Edit the .env file with your configuration
nano .env
```

**Required Environment Variables:**
- `SECRET_KEY`: A secure secret key for JWT tokens
- `POSTGRES_PASSWORD`: Password for PostgreSQL database
- `REDIS_PASSWORD`: Password for Redis cache
- `NEO4J_PASSWORD`: Password for Neo4j database
- `OPENAI_API_KEY`: Your OpenAI API key (or other LLM provider keys)

### 3. Start the Application

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

### 4. Initialize the Database

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Create initial admin user (optional)
docker-compose exec backend python -m app.scripts.create_admin_user
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Grafana Dashboard**: http://localhost:3001
- **pgAdmin**: http://localhost:5050 (if admin profile enabled)

## 📖 Usage Guide

### Creating Your First Project

1. **Register/Login**: Create an account or login at the frontend
2. **Create Project**: Set up a new project with your requirements
3. **Upload Documents**: Add requirement documents, specifications, or existing user stories
4. **Generate Stories**: Use the AI agent to generate user stories from your requirements
5. **Review & Refine**: Review generated stories, add comments, and make improvements
6. **Export**: Export to Jira, CSV, or other formats

### API Usage

The application provides a comprehensive REST API. Here's a quick example:

```python
import requests

# Authentication
auth_response = requests.post("http://localhost:8000/api/v1/auth/login", json={
    "username": "your_username",
    "password": "your_password"
})
token = auth_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Generate user stories
generation_request = {
    "requirements": "Create a user management system with authentication and role-based access",
    "project_id": 1,
    "persona": "System Administrator",
    "additional_context": "This is for an enterprise application"
}

response = requests.post(
    "http://localhost:8000/api/v1/user-stories/generate",
    json=generation_request,
    headers=headers
)

generated_stories = response.json()
```

### Document Upload and Processing

```python
# Upload a document
files = {"file": open("requirements.pdf", "rb")}
data = {"project_id": 1, "document_type": "requirements"}

response = requests.post(
    "http://localhost:8000/api/v1/documents/upload",
    files=files,
    data=data,
    headers=headers
)
```

## 🔧 Configuration

### LLM Providers

Configure your preferred LLM provider in the `.env` file:

```bash
# For OpenAI
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4
OPENAI_API_KEY=your_key_here

# For Azure OpenAI
DEFAULT_LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# For local models (Ollama)
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```

### Vector Database

Choose between ChromaDB (local) or Pinecone (cloud):

```bash
# ChromaDB (default, local)
VECTOR_DB_TYPE=chromadb
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Pinecone (cloud-based)
VECTOR_DB_TYPE=pinecone
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=rag-user-stories
```

### External Integrations

Configure Jira, Confluence, and SharePoint integration:

```bash
# Jira
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_USERNAME=your_email@company.com
JIRA_API_TOKEN=your_api_token

# Confluence
CONFLUENCE_BASE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USERNAME=your_email@company.com
CONFLUENCE_API_TOKEN=your_api_token

# SharePoint
SHAREPOINT_SITE_URL=https://your-company.sharepoint.com/sites/your-site
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
```

## 🏃‍♂️ Development

### Local Development Setup

```bash
# Backend development
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd frontend
npm install
npm start
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Add new table"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1
```

## 📊 Monitoring

The application includes comprehensive monitoring:

- **Grafana Dashboards**: Application metrics, database performance, LLM usage
- **Prometheus Metrics**: Custom metrics for user story generation, document processing
- **Health Checks**: All services include health check endpoints
- **Logging**: Structured logging with correlation IDs

Access monitoring at:
- Grafana: http://localhost:3001 (admin/admin123)
- Prometheus: http://localhost:9090

## 🔧 Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   # Check logs
   docker-compose logs backend
   docker-compose logs postgres
   
   # Restart specific service
   docker-compose restart backend
   ```

2. **Database connection issues**:
   ```bash
   # Check PostgreSQL health
   docker-compose exec postgres pg_isready -U rag_user -d rag_user_stories
   
   # Reset database
   docker-compose down -v
   docker-compose up -d postgres
   ```

3. **LLM API errors**:
   - Verify API keys in `.env` file
   - Check API quotas and rate limits
   - Review logs for specific error messages

4. **Memory issues**:
   - Increase Docker memory allocation
   - Adjust Neo4j memory settings in docker-compose.yml
   - Monitor resource usage with `docker stats`

### Performance Optimization

1. **Vector Database**: 
   - Use Pinecone for production scalability
   - Optimize chunk size and overlap settings
   - Monitor embedding generation costs

2. **Knowledge Graph**:
   - Regularly clean up unused entities
   - Optimize Cypher queries
   - Monitor Neo4j memory usage

3. **Background Tasks**:
   - Scale Celery workers based on load
   - Monitor task queue lengths
   - Optimize document processing pipeline

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write comprehensive tests for new features
- Update documentation for API changes
- Use conventional commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://docs.langchain.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [React Documentation](https://react.dev/)
- [Docker Documentation](https://docs.docker.com/)

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the [documentation](./docs/)
- Review the [FAQ](./docs/FAQ.md)

---

**Built with ❤️ for the developer community**