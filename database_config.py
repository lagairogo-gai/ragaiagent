from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import redis
from neo4j import GraphDatabase
from .config import settings

# PostgreSQL Database
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    poolclass=StaticPool if "sqlite" in settings.DATABASE_URL else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Redis connection
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client


# Neo4j connection for Knowledge Graph
class Neo4jConnection:
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("Connected to Neo4j successfully")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def execute_query(self, query: str, parameters: dict = None):
        """Execute a Cypher query"""
        if not self.driver:
            raise ConnectionError("No active Neo4j connection")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]
    
    def execute_write_query(self, query: str, parameters: dict = None):
        """Execute a write Cypher query"""
        if not self.driver:
            raise ConnectionError("No active Neo4j connection")
        
        with self.driver.session() as session:
            result = session.write_transaction(self._execute_query, query, parameters or {})
            return result
    
    @staticmethod
    def _execute_query(tx, query: str, parameters: dict):
        """Helper method for write transactions"""
        result = tx.run(query, parameters)
        return [record for record in result]


# Global Neo4j connection instance
neo4j_connection = Neo4jConnection()


def get_neo4j() -> Neo4jConnection:
    """Get Neo4j connection"""
    return neo4j_connection


# Database initialization
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def init_knowledge_graph():
    """Initialize knowledge graph schema"""
    try:
        # Create constraints and indexes for better performance
        constraints_and_indexes = [
            # Unique constraints
            "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT feature_id_unique IF NOT EXISTS FOR (f:Feature) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT user_story_id_unique IF NOT EXISTS FOR (us:UserStory) REQUIRE us.id IS UNIQUE",
            "CREATE CONSTRAINT stakeholder_id_unique IF NOT EXISTS FOR (s:Stakeholder) REQUIRE s.id IS UNIQUE",
            
            # Indexes for better query performance
            "CREATE INDEX project_name_index IF NOT EXISTS FOR (p:Project) ON (p.name)",
            "CREATE INDEX requirement_title_index IF NOT EXISTS FOR (r:Requirement) ON (r.title)",
            "CREATE INDEX user_story_title_index IF NOT EXISTS FOR (us:UserStory) ON (us.title)",
            "CREATE INDEX stakeholder_role_index IF NOT EXISTS FOR (s:Stakeholder) ON (s.role)",
        ]
        
        neo4j_conn = get_neo4j()
        for query in constraints_and_indexes:
            try:
                neo4j_conn.execute_query(query)
            except Exception as e:
                print(f"Warning: Could not execute query '{query}': {e}")
        
        print("Knowledge graph schema initialized")
        
    except Exception as e:
        print(f"Failed to initialize knowledge graph: {e}")


# Cleanup function
def cleanup_connections():
    """Clean up all database connections"""
    try:
        redis_client.close()
        neo4j_connection.close()
        engine.dispose()
        print("All database connections closed")
    except Exception as e:
        print(f"Error during cleanup: {e}")


# Health check functions
def check_postgres_health() -> bool:
    """Check PostgreSQL connection health"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def check_redis_health() -> bool:
    """Check Redis connection health"""
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


def check_neo4j_health() -> bool:
    """Check Neo4j connection health"""
    try:
        neo4j_connection.execute_query("RETURN 1")
        return True
    except Exception:
        return False