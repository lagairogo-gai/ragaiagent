from typing import List, Dict, Any, Optional, Tuple
import json
import uuid
import structlog
from datetime import datetime

from ..core.database import get_neo4j, get_db
from ..core.config import settings
from ..models.knowledge_graph import KnowledgeGraphEntity, KnowledgeGraphRelationship, EntityType, RelationshipType
from ..services.llm_service import llm_service

logger = structlog.get_logger()


class KnowledgeGraphService:
    """Service for managing knowledge graph operations"""
    
    def __init__(self):
        self.neo4j_conn = get_neo4j()
        self.entity_extraction_cache = {}
    
    async def extract_entities_from_text(
        self,
        text: str,
        project_id: int,
        context: Optional[str] = None,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Extract entities from text using LLM"""
        try:
            # Define entity types to extract
            available_types = [e.value for e in EntityType]
            target_types = entity_types or available_types
            
            extraction_prompt = f"""
Extract key entities from the following text that are relevant for software development and user story generation.

Focus on these entity types:
{', '.join(target_types)}

For each entity found, provide:
1. Name: The entity name/identifier
2. Type: One of the specified entity types
3. Description: Brief description of the entity
4. Properties: Key-value pairs of relevant properties
5. Confidence: How confident you are in this extraction (0.0-1.0)

Text to analyze:
{text}

Additional context:
{context or 'None provided'}

Return the results as a JSON array of entities:
[
  {{
    "name": "Entity Name",
    "type": "entity_type",
    "description": "Brief description",
    "properties": {{"key": "value"}},
    "confidence": 0.95
  }}
]
"""
            
            result = await llm_service.generate_text(
                prompt=extraction_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            # Parse the JSON response
            try:
                entities = json.loads(result["text"])
                if not isinstance(entities, list):
                    entities = []
                
                # Validate and enrich entities
                validated_entities = []
                for entity in entities:
                    if self._validate_entity(entity):
                        entity["project_id"] = project_id
                        entity["extracted_at"] = datetime.utcnow().isoformat()
                        entity["source_text"] = text[:200] + "..." if len(text) > 200 else text
                        validated_entities.append(entity)
                
                logger.info("Entities extracted from text",
                           project_id=project_id,
                           total_entities=len(validated_entities))
                
                return validated_entities
                
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse entity extraction JSON", error=str(e))
                return []
                
        except Exception as e:
            logger.error("Entity extraction failed", error=str(e))
            return []
    
    def _validate_entity(self, entity: Dict[str, Any]) -> bool:
        """Validate extracted entity structure"""
        required_fields = ["name", "type", "description"]
        
        for field in required_fields:
            if field not in entity or not entity[field]:
                return False
        
        # Check if type is valid
        if entity["type"] not in [e.value for e in EntityType]:
            return False
        
        # Ensure confidence is within range
        confidence = entity.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            entity["confidence"] = 0.5
        
        return True
    
    async def create_entity(
        self,
        name: str,
        entity_type: str,
        properties: Dict[str, Any],
        project_id: int,
        description: Optional[str] = None
    ) -> str:
        """Create a new entity in the knowledge graph"""
        try:
            entity_id = str(uuid.uuid4())
            
            # Create entity in Neo4j
            cypher_query = """
            CREATE (e:{entity_type} {{
                id: $entity_id,
                name: $name,
                description: $description,
                project_id: $project_id,
                created_at: datetime(),
                properties: $properties
            }})
            RETURN e.id as id
            """.format(entity_type=entity_type.capitalize())
            
            result = self.neo4j_conn.execute_query(
                cypher_query,
                {
                    "entity_id": entity_id,
                    "name": name,
                    "description": description,
                    "project_id": project_id,
                    "properties": properties
                }
            )
            
            if result:
                logger.info("Entity created in knowledge graph",
                           entity_id=entity_id,
                           entity_type=entity_type,
                           project_id=project_id)
                return entity_id
            else:
                raise Exception("Failed to create entity in Neo4j")
                
        except Exception as e:
            logger.error("Entity creation failed", error=str(e))
            raise
    
    async def create_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a relationship between entities"""
        try:
            relationship_id = str(uuid.uuid4())
            
            cypher_query = """
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            CREATE (source)-[r:{rel_type} {{
                id: $relationship_id,
                created_at: datetime(),
                properties: $properties
            }}]->(target)
            RETURN r.id as id
            """.format(rel_type=relationship_type.upper())
            
            result = self.neo4j_conn.execute_query(
                cypher_query,
                {
                    "source_id": source_entity_id,
                    "target_id": target_entity_id,
                    "relationship_distribution": [
                    {"type": record["relationship_type"], "count": record["count"]}
                    for record in relationship_counts
                ],
                "key_entities": [
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "connections": record["connections"]
                    }
                    for record in hubs
                ]
            }
            
            logger.info("Project structure analysis completed",
                       project_id=project_id,
                       total_entities=total_entities,
                       total_relationships=total_relationships)
            
            return analysis_result
            
        except Exception as e:
            logger.error("Project structure analysis failed", error=str(e))
            return {
                "project_id": project_id,
                "summary": {"error": str(e)},
                "entity_distribution": [],
                "relationship_distribution": [],
                "key_entities": []
            }
    
    async def extract_relationships_from_text(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities from text"""
        try:
            if len(entities) < 2:
                return []
            
            entity_list = [f"- {e['name']} ({e['type']})" for e in entities]
            
            relationship_prompt = f"""
Analyze the following text and identify relationships between the provided entities.

Entities to consider:
{chr(10).join(entity_list)}

Available relationship types:
- BELONGS_TO: Entity belongs to or is part of another
- DEPENDS_ON: Entity depends on another to function
- IMPLEMENTS: Entity implements or realizes another
- INVOLVES: Entity involves or includes another
- CONFLICTS_WITH: Entity conflicts with another
- DERIVES_FROM: Entity is derived from another
- RELATES_TO: General relationship
- BLOCKS: Entity blocks or prevents another
- ENABLES: Entity enables or allows another
- VALIDATES: Entity validates or verifies another

Text to analyze:
{text}

Return relationships as JSON array:
[
  {{
    "source_entity": "Entity Name",
    "target_entity": "Entity Name", 
    "relationship_type": "RELATIONSHIP_TYPE",
    "description": "Brief description of the relationship",
    "confidence": 0.85,
    "evidence": "Text excerpt supporting this relationship"
  }}
]

Only include relationships that are clearly supported by the text.
"""
            
            result = await llm_service.generate_text(
                prompt=relationship_prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            try:
                relationships = json.loads(result["text"])
                if not isinstance(relationships, list):
                    relationships = []
                
                # Validate relationships
                validated_relationships = []
                entity_names = {e["name"]: e for e in entities}
                
                for rel in relationships:
                    if self._validate_relationship(rel, entity_names):
                        rel["project_id"] = project_id
                        rel["extracted_at"] = datetime.utcnow().isoformat()
                        validated_relationships.append(rel)
                
                logger.info("Relationships extracted from text",
                           project_id=project_id,
                           total_relationships=len(validated_relationships))
                
                return validated_relationships
                
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse relationship extraction JSON", error=str(e))
                return []
                
        except Exception as e:
            logger.error("Relationship extraction failed", error=str(e))
            return []
    
    def _validate_relationship(self, relationship: Dict[str, Any], entity_names: Dict[str, Dict]) -> bool:
        """Validate extracted relationship"""
        required_fields = ["source_entity", "target_entity", "relationship_type"]
        
        for field in required_fields:
            if field not in relationship or not relationship[field]:
                return False
        
        # Check if entities exist
        if (relationship["source_entity"] not in entity_names or 
            relationship["target_entity"] not in entity_names):
            return False
        
        # Check if relationship type is valid
        if relationship["relationship_type"] not in [r.value.upper() for r in RelationshipType]:
            return False
        
        # Ensure confidence is within range
        confidence = relationship.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            relationship["confidence"] = 0.5
        
        return True
    
    async def build_project_knowledge_graph(
        self,
        project_id: int,
        documents: List[Dict[str, Any]],
        user_stories: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive knowledge graph for a project"""
        try:
            logger.info("Building knowledge graph for project", project_id=project_id)
            
            all_entities = []
            all_relationships = []
            
            # Extract entities from documents
            for doc in documents:
                if doc.get("content"):
                    entities = await self.extract_entities_from_text(
                        text=doc["content"],
                        project_id=project_id,
                        context=f"Document: {doc.get('title', 'Untitled')}"
                    )
                    
                    # Add document metadata to entities
                    for entity in entities:
                        entity["source_document_id"] = doc.get("id")
                        entity["source_type"] = "document"
                    
                    all_entities.extend(entities)
            
            # Extract entities from user stories if provided
            if user_stories:
                for story in user_stories:
                    story_text = f"{story.get('title', '')} {story.get('story_text', '')} {story.get('description', '')}"
                    entities = await self.extract_entities_from_text(
                        text=story_text,
                        project_id=project_id,
                        context=f"User Story: {story.get('title', 'Untitled')}"
                    )
                    
                    # Add user story metadata to entities
                    for entity in entities:
                        entity["source_user_story_id"] = story.get("id")
                        entity["source_type"] = "user_story"
                    
                    all_entities.extend(entities)
            
            # Remove duplicate entities (same name and type)
            unique_entities = {}
            for entity in all_entities:
                key = f"{entity['name']}_{entity['type']}"
                if key not in unique_entities:
                    unique_entities[key] = entity
                else:
                    # Merge properties and increase confidence
                    existing = unique_entities[key]
                    existing["confidence"] = min(1.0, existing["confidence"] + entity["confidence"] * 0.1)
                    if "properties" in entity:
                        existing.setdefault("properties", {}).update(entity.get("properties", {}))
            
            final_entities = list(unique_entities.values())
            
            # Extract relationships between entities
            if len(final_entities) > 1:
                # Group entities by source document/story and extract relationships
                source_groups = {}
                for entity in final_entities:
                    source_key = (entity.get("source_document_id") or 
                                entity.get("source_user_story_id") or "unknown")
                    source_groups.setdefault(source_key, []).append(entity)
                
                for source_id, group_entities in source_groups.items():
                    if len(group_entities) > 1:
                        # Get the source text for relationship extraction
                        source_text = ""
                        if source_id != "unknown":
                            # Find the source document or user story
                            for doc in documents:
                                if doc.get("id") == source_id:
                                    source_text = doc.get("content", "")
                                    break
                            else:
                                if user_stories:
                                    for story in user_stories:
                                        if story.get("id") == source_id:
                                            source_text = f"{story.get('title', '')} {story.get('story_text', '')} {story.get('description', '')}"
                                            break
                        
                        if source_text:
                            relationships = await self.extract_relationships_from_text(
                                text=source_text,
                                entities=group_entities,
                                project_id=project_id
                            )
                            all_relationships.extend(relationships)
            
            # Create entities in Neo4j
            created_entities = {}
            for entity in final_entities:
                try:
                    entity_id = await self.create_entity(
                        name=entity["name"],
                        entity_type=entity["type"],
                        properties=entity.get("properties", {}),
                        project_id=project_id,
                        description=entity.get("description")
                    )
                    created_entities[entity["name"]] = entity_id
                    entity["kg_id"] = entity_id
                except Exception as e:
                    logger.warning("Failed to create entity", entity_name=entity["name"], error=str(e))
            
            # Create relationships in Neo4j
            created_relationships = []
            for relationship in all_relationships:
                source_name = relationship["source_entity"]
                target_name = relationship["target_entity"]
                
                if source_name in created_entities and target_name in created_entities:
                    try:
                        rel_id = await self.create_relationship(
                            source_entity_id=created_entities[source_name],
                            target_entity_id=created_entities[target_name],
                            relationship_type=relationship["relationship_type"],
                            properties={
                                "description": relationship.get("description"),
                                "confidence": relationship.get("confidence"),
                                "evidence": relationship.get("evidence")
                            }
                        )
                        relationship["kg_id"] = rel_id
                        created_relationships.append(relationship)
                    except Exception as e:
                        logger.warning("Failed to create relationship", 
                                     source=source_name, 
                                     target=target_name, 
                                     error=str(e))
            
            result = {
                "project_id": project_id,
                "entities_created": len(created_entities),
                "relationships_created": len(created_relationships),
                "entities": final_entities,
                "relationships": created_relationships,
                "build_timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
            logger.info("Knowledge graph built successfully",
                       project_id=project_id,
                       entities_count=len(created_entities),
                       relationships_count=len(created_relationships))
            
            return result
            
        except Exception as e:
            logger.error("Knowledge graph building failed", project_id=project_id, error=str(e))
            return {
                "project_id": project_id,
                "entities_created": 0,
                "relationships_created": 0,
                "entities": [],
                "relationships": [],
                "build_timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    async def query_knowledge_graph(
        self,
        cypher_query: str,
        parameters: Optional[Dict[str, Any]] = None,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query on the knowledge graph"""
        try:
            # Add project filter if specified
            if project_id and "project_id" not in cypher_query.lower():
                # This is a simple approach - in production you'd want more sophisticated query modification
                logger.warning("Project ID filter not found in query - results may include other projects")
            
            result = self.neo4j_conn.execute_query(cypher_query, parameters or {})
            
            # Convert Neo4j records to dictionaries
            query_results = []
            for record in result:
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    if hasattr(value, '__dict__'):
                        # Convert Neo4j node/relationship to dict
                        record_dict[key] = dict(value)
                    else:
                        record_dict[key] = value
                query_results.append(record_dict)
            
            logger.info("Knowledge graph query executed",
                       query_length=len(cypher_query),
                       results_count=len(query_results))
            
            return query_results
            
        except Exception as e:
            logger.error("Knowledge graph query failed", error=str(e))
            raise
    
    async def get_entity_recommendations(
        self,
        user_story_text: str,
        project_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get entity recommendations for a user story"""
        try:
            # Find entities similar to user story content
            similar_entities = await self.search_entities(
                query=user_story_text,
                project_id=project_id,
                limit=limit * 2  # Get more to filter
            )
            
            if not similar_entities:
                return []
            
            # Use LLM to rank relevance
            ranking_prompt = f"""
Given this user story text: "{user_story_text}"

Rank the following entities by relevance (most relevant first):
{json.dumps(similar_entities, indent=2)}

Consider:
1. Direct mention or reference in the user story
2. Functional relevance to the story's goal
3. Potential impact on implementation

Return only the top {limit} most relevant entities as JSON array with relevance scores:
[
  {{
    "entity": {{...entity data...}},
    "relevance_score": 0.95,
    "relevance_reason": "Brief explanation"
  }}
]
"""
            
            result = await llm_service.generate_text(
                prompt=ranking_prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            try:
                recommendations = json.loads(result["text"])
                if isinstance(recommendations, list):
                    return recommendations[:limit]
            except json.JSONDecodeError:
                logger.warning("Failed to parse entity recommendations JSON")
            
            # Fallback: return first N entities
            return similar_entities[:limit]
            
        except Exception as e:
            logger.error("Entity recommendations failed", error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check knowledge graph service health"""
        try:
            # Test Neo4j connection
            test_result = self.neo4j_conn.execute_query("RETURN 'OK' as status")
            
            if test_result and test_result[0]["status"] == "OK":
                return {
                    "neo4j": "healthy",
                    "entity_extraction": "healthy",
                    "status": "healthy"
                }
            else:
                return {
                    "neo4j": "unhealthy",
                    "entity_extraction": "unknown",
                    "status": "degraded"
                }
                
        except Exception as e:
            return {
                "neo4j": "unhealthy",
                "entity_extraction": "unknown",
                "status": "unhealthy",
                "error": str(e)
            }


# Global knowledge graph service instance
knowledge_graph_service = KnowledgeGraphService()id": relationship_id,
                    "properties": properties or {}
                }
            )
            
            if result:
                logger.info("Relationship created in knowledge graph",
                           relationship_id=relationship_id,
                           relationship_type=relationship_type)
                return relationship_id
            else:
                raise Exception("Failed to create relationship in Neo4j")
                
        except Exception as e:
            logger.error("Relationship creation failed", error=str(e))
            raise
    
    async def find_related_entities(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find entities related to a given entity"""
        try:
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join([rt.upper() for rt in relationship_types])
                rel_filter = f":{rel_types}"
            
            cypher_query = f"""
            MATCH (start {{id: $entity_id}})
            MATCH (start)-[r{rel_filter}*1..{max_depth}]-(related)
            RETURN DISTINCT related, r
            LIMIT 50
            """
            
            result = self.neo4j_conn.execute_query(
                cypher_query,
                {"entity_id": entity_id}
            )
            
            related_entities = []
            for record in result:
                entity_data = dict(record["related"])
                related_entities.append(entity_data)
            
            logger.info("Found related entities",
                       entity_id=entity_id,
                       related_count=len(related_entities))
            
            return related_entities
            
        except Exception as e:
            logger.error("Finding related entities failed", error=str(e))
            return []
    
    async def search_entities(
        self,
        query: str,
        project_id: int,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for entities by name or description"""
        try:
            type_filter = ""
            if entity_types:
                type_labels = "|".join([et.capitalize() for et in entity_types])
                type_filter = f":{type_labels}"
            
            cypher_query = f"""
            MATCH (e{type_filter})
            WHERE e.project_id = $project_id
            AND (e.name CONTAINS $query OR e.description CONTAINS $query)
            RETURN e
            ORDER BY e.name
            LIMIT {limit}
            """
            
            result = self.neo4j_conn.execute_query(
                cypher_query,
                {
                    "query": query,
                    "project_id": project_id
                }
            )
            
            entities = []
            for record in result:
                entity_data = dict(record["e"])
                entities.append(entity_data)
            
            logger.info("Entity search completed",
                       query=query,
                       project_id=project_id,
                       results_count=len(entities))
            
            return entities
            
        except Exception as e:
            logger.error("Entity search failed", error=str(e))
            return []
    
    async def analyze_project_structure(self, project_id: int) -> Dict[str, Any]:
        """Analyze the knowledge graph structure for a project"""
        try:
            # Get entity counts by type
            entity_counts_query = """
            MATCH (e)
            WHERE e.project_id = $project_id
            RETURN labels(e)[0] as entity_type, count(e) as count
            ORDER BY count DESC
            """
            
            entity_counts = self.neo4j_conn.execute_query(
                entity_counts_query,
                {"project_id": project_id}
            )
            
            # Get relationship counts by type
            relationship_counts_query = """
            MATCH (e1)-[r]->(e2)
            WHERE e1.project_id = $project_id AND e2.project_id = $project_id
            RETURN type(r) as relationship_type, count(r) as count
            ORDER BY count DESC
            """
            
            relationship_counts = self.neo4j_conn.execute_query(
                relationship_counts_query,
                {"project_id": project_id}
            )
            
            # Find highly connected entities (hubs)
            hubs_query = """
            MATCH (e)
            WHERE e.project_id = $project_id
            MATCH (e)-[r]-()
            WITH e, count(r) as connections
            WHERE connections > 2
            RETURN e.name as name, e.id as id, labels(e)[0] as type, connections
            ORDER BY connections DESC
            LIMIT 10
            """
            
            hubs = self.neo4j_conn.execute_query(
                hubs_query,
                {"project_id": project_id}
            )
            
            # Calculate graph density and other metrics
            total_entities_query = """
            MATCH (e)
            WHERE e.project_id = $project_id
            RETURN count(e) as total_entities
            """
            
            total_relationships_query = """
            MATCH (e1)-[r]->(e2)
            WHERE e1.project_id = $project_id AND e2.project_id = $project_id
            RETURN count(r) as total_relationships
            """
            
            total_entities_result = self.neo4j_conn.execute_query(total_entities_query, {"project_id": project_id})
            total_relationships_result = self.neo4j_conn.execute_query(total_relationships_query, {"project_id": project_id})
            
            total_entities = total_entities_result[0]["total_entities"] if total_entities_result else 0
            total_relationships = total_relationships_result[0]["total_relationships"] if total_relationships_result else 0
            
            # Calculate density (actual relationships / possible relationships)
            max_possible_relationships = total_entities * (total_entities - 1) if total_entities > 1 else 0
            density = total_relationships / max_possible_relationships if max_possible_relationships > 0 else 0
            
            analysis_result = {
                "project_id": project_id,
                "summary": {
                    "total_entities": total_entities,
                    "total_relationships": total_relationships,
                    "graph_density": density,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                },
                "entity_distribution": [
                    {"type": record["entity_type"], "count": record["count"]}
                    for record in entity_counts
                ],
                "relationship_