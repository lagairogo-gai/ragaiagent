from typing import List, Dict, Any, Optional, Tuple
import structlog
from datetime import datetime
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import Chroma, Pinecone
from langchain.schema import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..core.database import get_db
from ..models.document import Document as DocumentModel, DocumentChunk
from ..models.user_story import UserStory
from ..models.knowledge_graph import KnowledgeGraphEntity
from .llm_service import llm_service

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self):
        self.embedding_providers = {}
        self._initialize_embedding_providers()
    
    def _initialize_embedding_providers(self):
        """Initialize available embedding providers"""
        try:
            # OpenAI embeddings
            if settings.OPENAI_API_KEY:
                self.embedding_providers["openai"] = OpenAIEmbeddings(
                    openai_api_key=settings.OPENAI_API_KEY,
                    model=settings.DEFAULT_EMBEDDING_MODEL
                )
                logger.info("OpenAI embeddings initialized")
            
            # Local sentence transformers
            try:
                self.embedding_providers["sentence_transformers"] = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2"
                )
                logger.info("Sentence transformers embeddings initialized")
            except Exception as e:
                logger.warning("Failed to initialize sentence transformers", error=str(e))
            
        except Exception as e:
            logger.error("Failed to initialize embedding providers", error=str(e))
    
    def get_embeddings(self, provider: str = "openai"):
        """Get embedding provider"""
        if provider not in self.embedding_providers:
            raise ValueError(f"Embedding provider '{provider}' not available")
        return self.embedding_providers[provider]


class VectorStore:
    """Vector store abstraction"""
    
    def __init__(self, store_type: str = "chromadb"):
        self.store_type = store_type
        self.embedding_service = EmbeddingService()
        self.stores = {}
        self._initialize_stores()
    
    def _initialize_stores(self):
        """Initialize vector stores"""
        try:
            if self.store_type == "chromadb":
                self._initialize_chroma()
            elif self.store_type == "pinecone":
                self._initialize_pinecone()
        except Exception as e:
            logger.error("Failed to initialize vector stores", error=str(e))
    
    def _initialize_chroma(self):
        """Initialize ChromaDB"""
        try:
            embeddings = self.embedding_service.get_embeddings("openai")
            self.stores["default"] = Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
                embedding_function=embeddings,
                collection_name="documents"
            )
            logger.info("ChromaDB initialized")
        except Exception as e:
            logger.error("Failed to initialize ChromaDB", error=str(e))
    
    def _initialize_pinecone(self):
        """Initialize Pinecone"""
        try:
            import pinecone
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            embeddings = self.embedding_service.get_embeddings("openai")
            self.stores["default"] = Pinecone.from_existing_index(
                index_name=settings.PINECONE_INDEX_NAME,
                embedding=embeddings
            )
            logger.info("Pinecone initialized")
        except Exception as e:
            logger.error("Failed to initialize Pinecone", error=str(e))
    
    def get_store(self, project_id: Optional[int] = None):
        """Get vector store for project"""
        # For now, return default store
        # In production, you might want project-specific stores
        return self.stores.get("default")
    
    async def add_documents(self, documents: List[Document], project_id: Optional[int] = None):
        """Add documents to vector store"""
        store = self.get_store(project_id)
        if not store:
            raise ValueError("Vector store not available")
        
        try:
            # Add documents and get IDs
            ids = store.add_documents(documents)
            logger.info("Documents added to vector store", count=len(documents), project_id=project_id)
            return ids
        except Exception as e:
            logger.error("Failed to add documents to vector store", error=str(e))
            raise
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        project_id: Optional[int] = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """Perform similarity search"""
        store = self.get_store(project_id)
        if not store:
            raise ValueError("Vector store not available")
        
        try:
            results = store.similarity_search(
                query=query,
                k=k,
                filter=filter_dict
            )
            logger.info("Similarity search completed", query_length=len(query), results_count=len(results))
            return results
        except Exception as e:
            logger.error("Similarity search failed", error=str(e))
            raise
    
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        project_id: Optional[int] = None,
        filter_dict: Optional[Dict] = None
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search with scores"""
        store = self.get_store(project_id)
        if not store:
            raise ValueError("Vector store not available")
        
        try:
            results = store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            logger.info("Similarity search with scores completed", results_count=len(results))
            return results
        except Exception as e:
            logger.error("Similarity search with scores failed", error=str(e))
            raise


class DocumentProcessor:
    """Service for processing documents for RAG"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def process_document(self, document: DocumentModel, db_session) -> List[DocumentChunk]:
        """Process document into chunks"""
        try:
            if not document.content:
                logger.warning("Document has no content to process", document_id=document.id)
                return []
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(document.content)
            
            # Create document chunk records
            document_chunks = []
            for i, chunk_content in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=i,
                    word_count=len(chunk_content.split()),
                    chunk_type="paragraph"  # Could be enhanced with more sophisticated detection
                )
                document_chunks.append(chunk)
                db_session.add(chunk)
            
            # Update document
            document.chunk_count = len(document_chunks)
            document.status = "processed"
            document.processed_at = datetime.utcnow()
            
            db_session.commit()
            
            logger.info("Document processed into chunks", 
                       document_id=document.id, 
                       chunk_count=len(document_chunks))
            
            return document_chunks
            
        except Exception as e:
            logger.error("Document processing failed", document_id=document.id, error=str(e))
            document.status = "failed"
            document.processing_error = str(e)
            db_session.commit()
            raise
    
    def create_langchain_documents(self, chunks: List[DocumentChunk]) -> List[Document]:
        """Convert database chunks to LangChain documents"""
        langchain_docs = []
        
        for chunk in chunks:
            doc = Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "word_count": chunk.word_count,
                    "chunk_type": chunk.chunk_type,
                    "source": "database"
                }
            )
            langchain_docs.append(doc)
        
        return langchain_docs


class RAGService:
    """Main RAG service for retrieval-augmented generation"""
    
    def __init__(self):
        self.vector_store = VectorStore(settings.VECTOR_DB_TYPE)
        self.document_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
    
    async def process_and_index_document(self, document: DocumentModel, db_session) -> bool:
        """Process document and add to vector store"""
        try:
            # Process document into chunks
            chunks = await self.document_processor.process_document(document, db_session)
            
            if not chunks:
                return False
            
            # Convert to LangChain documents
            langchain_docs = self.document_processor.create_langchain_documents(chunks)
            
            # Add to vector store
            await self.vector_store.add_documents(langchain_docs, document.project_id)
            
            # Update document status
            document.embeddings_generated = True
            document.vector_store_id = str(uuid.uuid4())  # Generate unique vector store ID
            db_session.commit()
            
            logger.info("Document indexed successfully", document_id=document.id)
            return True
            
        except Exception as e:
            logger.error("Failed to process and index document", document_id=document.id, error=str(e))
            return False
    
    async def retrieve_relevant_context(
        self,
        query: str,
        project_id: int,
        k: int = None,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query"""
        k = k or settings.TOP_K_RETRIEVAL
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD
        
        try:
            # Perform similarity search with scores
            results = await self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                project_id=project_id,
                filter_dict={"project_id": project_id} if project_id else None
            )
            
            # Filter by similarity threshold and format results
            relevant_context = []
            for doc, score in results:
                if score >= similarity_threshold:
                    relevant_context.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": score
                    })
            
            logger.info("Retrieved relevant context", 
                       query_length=len(query), 
                       total_results=len(results),
                       relevant_results=len(relevant_context))
            
            return relevant_context
            
        except Exception as e:
            logger.error("Failed to retrieve relevant context", error=str(e))
            raise
    
    async def generate_user_stories_with_rag(
        self,
        requirements: str,
        project_id: int,
        persona: Optional[str] = None,
        additional_context: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate user stories using RAG"""
        try:
            # Retrieve relevant context from documents
            context_docs = await self.retrieve_relevant_context(
                query=requirements,
                project_id=project_id
            )
            
            # Build context string from retrieved documents
            context_parts = []
            if context_docs:
                context_parts.append("=== RELEVANT CONTEXT FROM DOCUMENTS ===")
                for i, ctx in enumerate(context_docs[:5]):  # Limit to top 5 for token efficiency
                    context_parts.append(f"Context {i+1} (similarity: {ctx['similarity_score']:.3f}):")
                    context_parts.append(ctx["content"][:500] + "..." if len(ctx["content"]) > 500 else ctx["content"])
                    context_parts.append("")
            
            if additional_context:
                context_parts.append("=== ADDITIONAL CONTEXT ===")
                context_parts.append(additional_context)
            
            combined_context = "\n".join(context_parts) if context_parts else None
            
            # Generate user stories using LLM service
            result = await llm_service.generate_user_story(
                requirements=requirements,
                context=combined_context,
                persona=persona,
                provider_name=llm_provider,
                model_name=llm_model
            )
            
            # Add RAG-specific metadata
            result["rag_metadata"] = {
                "context_documents_used": len(context_docs),
                "context_sources": [ctx["metadata"] for ctx in context_docs],
                "retrieval_query": requirements,
                "project_id": project_id
            }
            
            logger.info("User stories generated with RAG",
                       project_id=project_id,
                       context_docs_count=len(context_docs),
                       success=result.get("success", False))
            
            return result
            
        except Exception as e:
            logger.error("RAG user story generation failed", project_id=project_id, error=str(e))
            raise
    
    async def enhance_user_story_with_context(
        self,
        user_story: UserStory,
        db_session
    ) -> Dict[str, Any]:
        """Enhance existing user story with additional context"""
        try:
            # Use the user story content to find relevant context
            query = f"{user_story.title} {user_story.story_text} {user_story.description or ''}"
            
            context_docs = await self.retrieve_relevant_context(
                query=query,
                project_id=user_story.project_id,
                k=3  # Fewer results for enhancement
            )
            
            if not context_docs:
                return {"enhancement": None, "context_found": False}
            
            # Generate enhancement suggestions
            context_text = "\n".join([ctx["content"] for ctx in context_docs])
            
            enhancement_prompt = f"""
Based on the following context from project documents, suggest improvements to this user story:

USER STORY:
Title: {user_story.title}
Story: {user_story.story_text}
Description: {user_story.description or 'None'}
Current Acceptance Criteria: {user_story.acceptance_criteria}

RELEVANT CONTEXT:
{context_text}

Provide suggestions for:
1. Additional acceptance criteria
2. Edge cases to consider
3. Dependencies or constraints
4. Clarifications or improvements

Format as JSON with specific, actionable suggestions."""

            enhancement_result = await llm_service.generate_text(
                prompt=enhancement_prompt,
                temperature=0.5,
                max_tokens=1500
            )
            
            return {
                "enhancement": enhancement_result,
                "context_found": True,
                "context_sources": [ctx["metadata"] for ctx in context_docs]
            }
            
        except Exception as e:
            logger.error("User story enhancement failed", user_story_id=user_story.id, error=str(e))
            raise
    
    async def search_project_knowledge(
        self,
        query: str,
        project_id: int,
        search_type: str = "similarity",  # similarity, keyword, hybrid
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search project knowledge base"""
        try:
            if search_type == "similarity":
                results = await self.vector_store.similarity_search_with_score(
                    query=query,
                    k=limit,
                    project_id=project_id
                )
                
                return [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score,
                        "search_type": "similarity"
                    }
                    for doc, score in results
                ]
            
            # TODO: Implement keyword and hybrid search
            else:
                raise NotImplementedError(f"Search type '{search_type}' not implemented yet")
                
        except Exception as e:
            logger.error("Knowledge search failed", query=query, project_id=project_id, error=str(e))
            raise
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Check RAG service health"""
        health_status = {
            "vector_store": "unknown",
            "embeddings": "unknown",
            "document_processor": "healthy"
        }
        
        try:
            # Test vector store
            test_store = self.vector_store.get_store()
            if test_store:
                health_status["vector_store"] = "healthy"
            else:
                health_status["vector_store"] = "unhealthy"
        except Exception:
            health_status["vector_store"] = "unhealthy"
        
        try:
            # Test embeddings
            embeddings = self.embedding_service.get_embeddings()
            test_embedding = embeddings.embed_query("test")
            if test_embedding:
                health_status["embeddings"] = "healthy"
        except Exception:
            health_status["embeddings"] = "unhealthy"
        
        return health_status


# Global RAG service instance
rag_service = RAGService()