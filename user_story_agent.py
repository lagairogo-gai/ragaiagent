from typing import Dict, Any, List, Optional, TypedDict, Annotated
import json
import structlog
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from ..services.llm_service import llm_service
from ..services.rag_service import rag_service
from ..services.knowledge_graph_service import knowledge_graph_service
from ..core.config import settings

logger = structlog.get_logger()


class UserStoryState(TypedDict):
    """State for the user story generation workflow"""
    # Input
    requirements: str
    project_id: int
    user_id: int
    persona: Optional[str]
    additional_context: Optional[str]
    generation_options: Dict[str, Any]
    
    # Workflow state
    messages: Annotated[List, add_messages]
    current_step: str
    analysis_complete: bool
    context_retrieved: bool
    stories_generated: bool
    quality_checked: bool
    
    # Results
    requirements_analysis: Optional[Dict[str, Any]]
    retrieved_context: List[Dict[str, Any]]
    generated_stories: List[Dict[str, Any]]
    quality_scores: Dict[str, Any]
    knowledge_graph_entities: List[Dict[str, Any]]
    
    # Metadata
    generation_metadata: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class UserStoryAgent:
    """LangGraph-based agent for user story generation"""
    
    def __init__(self):
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the user story generation workflow"""
        workflow = StateGraph(UserStoryState)
        
        # Add nodes
        workflow.add_node("analyze_requirements", self._analyze_requirements)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("extract_kg_entities", self._extract_kg_entities)
        workflow.add_node("generate_stories", self._generate_stories)
        workflow.add_node("quality_check", self._quality_check)
        workflow.add_node("finalize_results", self._finalize_results)
        
        # Set entry point
        workflow.set_entry_point("analyze_requirements")
        
        # Add edges
        workflow.add_edge("analyze_requirements", "retrieve_context")
        workflow.add_edge("retrieve_context", "extract_kg_entities")
        workflow.add_edge("extract_kg_entities", "generate_stories")
        workflow.add_edge("generate_stories", "quality_check")
        workflow.add_edge("quality_check", "finalize_results")
        workflow.add_edge("finalize_results", END)
        
        return workflow
    
    async def _analyze_requirements(self, state: UserStoryState) -> UserStoryState:
        """Analyze the input requirements"""
        try:
            logger.info("Starting requirements analysis", project_id=state["project_id"])
            
            analysis_prompt = """
You are a senior business analyst. Analyze the following requirements and extract:

1. **Functional Requirements**: What the system should do
2. **Non-functional Requirements**: Performance, security, usability constraints  
3. **Business Rules**: Rules and policies that govern the system
4. **Stakeholders**: Who will use or be affected by the system
5. **Key Entities**: Important objects, data, or concepts
6. **Dependencies**: External systems or prerequisites
7. **Assumptions**: What we're assuming to be true
8. **Scope**: What's included and excluded

Return your analysis as a JSON object with these sections.

Requirements to analyze:
{requirements}

Additional context:
{context}
"""
            
            result = await llm_service.generate_text(
                prompt=analysis_prompt.format(
                    requirements=state["requirements"],
                    context=state.get("additional_context", "None provided")
                ),
                temperature=0.3,
                max_tokens=2000
            )
            
            # Try to parse JSON response
            try:
                analysis = json.loads(result["text"])
                state["requirements_analysis"] = analysis
                state["analysis_complete"] = True
                state["messages"].append(AIMessage(content=f"Requirements analysis completed: {len(analysis)} sections analyzed"))
                
                logger.info("Requirements analysis completed", 
                           project_id=state["project_id"],
                           sections_analyzed=len(analysis))
            except json.JSONDecodeError:
                # If JSON parsing fails, store as text
                state["requirements_analysis"] = {"raw_analysis": result["text"]}
                state["analysis_complete"] = True
                state["warnings"].append("Requirements analysis returned non-JSON format")
            
        except Exception as e:
            error_msg = f"Requirements analysis failed: {str(e)}"
            state["errors"].append(error_msg)
            state["analysis_complete"] = False
            logger.error("Requirements analysis failed", error=str(e))
        
        state["current_step"] = "analyze_requirements"
        return state
    
    async def _retrieve_context(self, state: UserStoryState) -> UserStoryState:
        """Retrieve relevant context from documents"""
        try:
            logger.info("Retrieving context", project_id=state["project_id"])
            
            # Use requirements as query for context retrieval
            context_docs = await rag_service.retrieve_relevant_context(
                query=state["requirements"],
                project_id=state["project_id"],
                k=settings.TOP_K_RETRIEVAL
            )
            
            state["retrieved_context"] = context_docs
            state["context_retrieved"] = True
            state["messages"].append(AIMessage(content=f"Retrieved {len(context_docs)} relevant context documents"))
            
            logger.info("Context retrieval completed", 
                       project_id=state["project_id"],
                       context_docs_count=len(context_docs))
            
        except Exception as e:
            error_msg = f"Context retrieval failed: {str(e)}"
            state["errors"].append(error_msg)
            state["context_retrieved"] = False
            state["retrieved_context"] = []
            logger.error("Context retrieval failed", error=str(e))
        
        state["current_step"] = "retrieve_context"
        return state
    
    async def _extract_kg_entities(self, state: UserStoryState) -> UserStoryState:
        """Extract knowledge graph entities from requirements"""
        try:
            logger.info("Extracting knowledge graph entities", project_id=state["project_id"])
            
            # Extract entities using the knowledge graph service
            entities = await knowledge_graph_service.extract_entities_from_text(
                text=state["requirements"],
                project_id=state["project_id"],
                context=state.get("additional_context")
            )
            
            state["knowledge_graph_entities"] = entities
            state["messages"].append(AIMessage(content=f"Extracted {len(entities)} knowledge graph entities"))
            
            logger.info("Knowledge graph entity extraction completed",
                       project_id=state["project_id"],
                       entities_count=len(entities))
            
        except Exception as e:
            error_msg = f"Knowledge graph entity extraction failed: {str(e)}"
            state["errors"].append(error_msg)
            state["knowledge_graph_entities"] = []
            logger.warning("Knowledge graph entity extraction failed", error=str(e))
        
        state["current_step"] = "extract_kg_entities"
        return state
    
    async def _generate_stories(self, state: UserStoryState) -> UserStoryState:
        """Generate user stories"""
        try:
            logger.info("Generating user stories", project_id=state["project_id"])
            
            # Build comprehensive context for story generation
            context_parts = []
            
            # Add requirements analysis
            if state.get("requirements_analysis"):
                context_parts.append("=== REQUIREMENTS ANALYSIS ===")
                context_parts.append(json.dumps(state["requirements_analysis"], indent=2))
            
            # Add retrieved document context
            if state.get("retrieved_context"):
                context_parts.append("=== RELEVANT DOCUMENTS ===")
                for i, ctx in enumerate(state["retrieved_context"][:3]):  # Top 3 documents
                    context_parts.append(f"Document {i+1} (similarity: {ctx['similarity_score']:.3f}):")
                    context_parts.append(ctx["content"][:300] + "..." if len(ctx["content"]) > 300 else ctx["content"])
            
            # Add knowledge graph entities
            if state.get("knowledge_graph_entities"):
                context_parts.append("=== KEY ENTITIES ===")
                entity_summary = [f"- {entity['name']} ({entity['type']})" for entity in state["knowledge_graph_entities"][:10]]
                context_parts.extend(entity_summary)
            
            # Add additional context
            if state.get("additional_context"):
                context_parts.append("=== ADDITIONAL CONTEXT ===")
                context_parts.append(state["additional_context"])
            
            combined_context = "\n".join(context_parts)
            
            # Generate user stories using LLM service
            generation_options = state.get("generation_options", {})
            result = await llm_service.generate_user_story(
                requirements=state["requirements"],
                context=combined_context,
                persona=state.get("persona"),
                provider_name=generation_options.get("llm_provider"),
                model_name=generation_options.get("llm_model")
            )
            
            if result.get("success") and result.get("parsed_stories"):
                stories_data = result["parsed_stories"]
                state["generated_stories"] = stories_data.get("user_stories", [])
                state["stories_generated"] = True
                state["messages"].append(AIMessage(content=f"Generated {len(state['generated_stories'])} user stories"))
                
                # Store generation metadata
                state["generation_metadata"].update({
                    "llm_provider": result.get("provider"),
                    "llm_model": result.get("model"),
                    "generation_time": result.get("generation_time"),
                    "token_usage": result.get("usage"),
                    "cost": result.get("cost", 0),
                    "confidence_score": stories_data.get("metadata", {}).get("confidence_score"),
                    "context_docs_used": len(state.get("retrieved_context", [])),
                    "kg_entities_used": len(state.get("knowledge_graph_entities", []))
                })
                
                logger.info("User stories generated successfully",
                           project_id=state["project_id"],
                           stories_count=len(state["generated_stories"]))
            else:
                state["generated_stories"] = []
                state["stories_generated"] = False
                error_msg = f"Story generation failed: {result.get('parse_error', 'Unknown error')}"
                state["errors"].append(error_msg)
                logger.error("User story generation failed", project_id=state["project_id"])
            
        except Exception as e:
            error_msg = f"Story generation failed: {str(e)}"
            state["errors"].append(error_msg)
            state["generated_stories"] = []
            state["stories_generated"] = False
            logger.error("Story generation failed", error=str(e))
        
        state["current_step"] = "generate_stories"
        return state
    
    async def _quality_check(self, state: UserStoryState) -> UserStoryState:
        """Perform quality checks on generated stories"""
        try:
            logger.info("Performing quality checks", project_id=state["project_id"])
            
            if not state["generated_stories"]:
                state["quality_scores"] = {"overall_score": 0, "checks": []}
                state["quality_checked"] = True
                return state
            
            quality_prompt = """
You are a quality assurance expert for user stories. Evaluate the following user stories based on these criteria:

1. **INVEST Criteria**:
   - Independent: Can be developed independently
   - Negotiable: Details can be discussed
   - Valuable: Provides business value
   - Estimable: Can be estimated for effort
   - Small: Can be completed in one iteration
   - Testable: Has clear acceptance criteria

2. **Clarity**: Clear and unambiguous language
3. **Completeness**: Has all necessary components
4. **Consistency**: Consistent with other stories
5. **Feasibility**: Technically and practically achievable

For each story, provide:
- Overall score (1-10)
- Scores for each INVEST criterion (1-10)
- Specific feedback and suggestions for improvement
- Risk assessment (low/medium/high)

Return as JSON with detailed feedback.

User Stories to evaluate:
{stories}
"""
            
            stories_text = json.dumps(state["generated_stories"], indent=2)
            result = await llm_service.generate_text(
                prompt=quality_prompt.format(stories=stories_text),
                temperature=0.3,
                max_tokens=3000
            )
            
            try:
                quality_data = json.loads(result["text"])
                state["quality_scores"] = quality_data
                
                # Calculate overall quality score
                if "story_evaluations" in quality_data:
                    scores = [eval_data.get("overall_score", 5) for eval_data in quality_data["story_evaluations"]]
                    overall_score = sum(scores) / len(scores) if scores else 5
                    state["quality_scores"]["overall_score"] = overall_score
                
                state["quality_checked"] = True
                state["messages"].append(AIMessage(content=f"Quality check completed. Overall score: {state['quality_scores'].get('overall_score', 'N/A')}"))
                
                logger.info("Quality check completed",
                           project_id=state["project_id"],
                           overall_score=state["quality_scores"].get("overall_score"))
                
            except json.JSONDecodeError:
                state["quality_scores"] = {"raw_feedback": result["text"]}
                state["quality_checked"] = True
                state["warnings"].append("Quality check returned non-JSON format")
            
        except Exception as e:
            error_msg = f"Quality check failed: {str(e)}"
            state["errors"].append(error_msg)
            state["quality_scores"] = {}
            state["quality_checked"] = False
            logger.error("Quality check failed", error=str(e))
        
        state["current_step"] = "quality_check"
        return state
    
    async def _finalize_results(self, state: UserStoryState) -> UserStoryState:
        """Finalize and package the results"""
        try:
            logger.info("Finalizing results", project_id=state["project_id"])
            
            # Update generation metadata
            state["generation_metadata"].update({
                "workflow_completed": True,
                "completion_time": datetime.utcnow().isoformat(),
                "total_errors": len(state["errors"]),
                "total_warnings": len(state["warnings"]),
                "steps_completed": [
                    {"step": "analyze_requirements", "completed": state.get("analysis_complete", False)},
                    {"step": "retrieve_context", "completed": state.get("context_retrieved", False)},
                    {"step": "extract_kg_entities", "completed": len(state.get("knowledge_graph_entities", [])) > 0},
                    {"step": "generate_stories", "completed": state.get("stories_generated", False)},
                    {"step": "quality_check", "completed": state.get("quality_checked", False)}
                ]
            })
            
            # Add final summary message
            summary_parts = [
                f"User story generation workflow completed for project {state['project_id']}",
                f"Generated {len(state.get('generated_stories', []))} user stories",
                f"Quality score: {state.get('quality_scores', {}).get('overall_score', 'N/A')}",
                f"Context documents used: {len(state.get('retrieved_context', []))}",
                f"Knowledge graph entities: {len(state.get('knowledge_graph_entities', []))}"
            ]
            
            if state["errors"]:
                summary_parts.append(f"Errors encountered: {len(state['errors'])}")
            if state["warnings"]:
                summary_parts.append(f"Warnings: {len(state['warnings'])}")
            
            state["messages"].append(AIMessage(content="\n".join(summary_parts)))
            
            logger.info("Results finalized successfully",
                       project_id=state["project_id"],
                       stories_generated=len(state.get("generated_stories", [])),
                       errors_count=len(state["errors"]))
            
        except Exception as e:
            error_msg = f"Result finalization failed: {str(e)}"
            state["errors"].append(error_msg)
            logger.error("Result finalization failed", error=str(e))
        
        state["current_step"] = "finalize_results"
        return state
    
    async def generate_user_stories(
        self,
        requirements: str,
        project_id: int,
        user_id: int,
        persona: Optional[str] = None,
        additional_context: Optional[str] = None,
        generation_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Main method to generate user stories using the workflow"""
        
        # Initialize state
        initial_state = UserStoryState(
            requirements=requirements,
            project_id=project_id,
            user_id=user_id,
            persona=persona,
            additional_context=additional_context,
            generation_options=generation_options or {},
            messages=[HumanMessage(content=f"Generate user stories for: {requirements[:100]}...")],
            current_step="initialize",
            analysis_complete=False,
            context_retrieved=False,
            stories_generated=False,
            quality_checked=False,
            requirements_analysis=None,
            retrieved_context=[],
            generated_stories=[],
            quality_scores={},
            knowledge_graph_entities=[],
            generation_metadata={
                "start_time": datetime.utcnow().isoformat(),
                "project_id": project_id,
                "user_id": user_id,
                "workflow_version": "1.0"
            },
            errors=[],
            warnings=[]
        )
        
        try:
            # Run the workflow
            logger.info("Starting user story generation workflow",
                       project_id=project_id,
                       user_id=user_id)
            
            final_state = await self.app.ainvoke(initial_state)
            
            # Package the results
            result = {
                "success": final_state.get("stories_generated", False),
                "user_stories": final_state.get("generated_stories", []),
                "requirements_analysis": final_state.get("requirements_analysis"),
                "quality_scores": final_state.get("quality_scores"),
                "context_documents": final_state.get("retrieved_context"),
                "knowledge_graph_entities": final_state.get("knowledge_graph_entities"),
                "metadata": final_state.get("generation_metadata"),
                "messages": [msg.content for msg in final_state.get("messages", [])],
                "errors": final_state.get("errors", []),
                "warnings": final_state.get("warnings", [])
            }
            
            logger.info("User story generation workflow completed",
                       project_id=project_id,
                       success=result["success"],
                       stories_count=len(result["user_stories"]))
            
            return result
            
        except Exception as e:
            logger.error("User story generation workflow failed",
                        project_id=project_id,
                        error=str(e))
            
            return {
                "success": False,
                "user_stories": [],
                "requirements_analysis": None,
                "quality_scores": {},
                "context_documents": [],
                "knowledge_graph_entities": [],
                "metadata": initial_state["generation_metadata"],
                "messages": [f"Workflow failed: {str(e)}"],
                "errors": [f"Workflow execution failed: {str(e)}"],
                "warnings": []
            }


# Global user story agent instance
user_story_agent = UserStoryAgent()