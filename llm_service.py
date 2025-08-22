from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import structlog
from datetime import datetime

from langchain.llms import OpenAI, Ollama
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.callbacks import get_openai_callback

from ..core.config import settings

logger = structlog.get_logger()


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0,
            "requests_count": 0
        }
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion"""
        pass
    
    def update_usage_stats(self, token_usage: Dict[str, int], cost: float = 0.0):
        """Update usage statistics"""
        self.usage_stats["total_tokens"] += token_usage.get("total_tokens", 0)
        self.usage_stats["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
        self.usage_stats["completion_tokens"] += token_usage.get("completion_tokens", 0)
        self.usage_stats["total_cost"] += cost
        self.usage_stats["requests_count"] += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return self.usage_stats.copy()


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider"""
    
    def __init__(self, model_name: str = "gpt-4", **kwargs):
        super().__init__(model_name, **kwargs)
        self.client = ChatOpenAI(
            model_name=model_name,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000),
            **kwargs
        )
        
        # Token pricing (approximate, should be updated regularly)
        self.pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.002, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004}
        }
    
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using OpenAI"""
        try:
            with get_openai_callback() as cb:
                response = self.client.predict(prompt)
                
                # Calculate cost
                model_pricing = self.pricing.get(self.model_name, {"prompt": 0.002, "completion": 0.002})
                cost = (cb.prompt_tokens * model_pricing["prompt"] + 
                       cb.completion_tokens * model_pricing["completion"]) / 1000
                
                # Update usage stats
                token_usage = {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens
                }
                self.update_usage_stats(token_usage, cost)
                
                return {
                    "text": response,
                    "usage": token_usage,
                    "cost": cost,
                    "model": self.model_name,
                    "provider": "openai"
                }
                
        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e), model=self.model_name)
            raise
    
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using OpenAI"""
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            with get_openai_callback() as cb:
                response = self.client(langchain_messages)
                
                # Calculate cost
                model_pricing = self.pricing.get(self.model_name, {"prompt": 0.002, "completion": 0.002})
                cost = (cb.prompt_tokens * model_pricing["prompt"] + 
                       cb.completion_tokens * model_pricing["completion"]) / 1000
                
                # Update usage stats
                token_usage = {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens
                }
                self.update_usage_stats(token_usage, cost)
                
                return {
                    "message": {
                        "role": "assistant",
                        "content": response.content
                    },
                    "usage": token_usage,
                    "cost": cost,
                    "model": self.model_name,
                    "provider": "openai"
                }
                
        except Exception as e:
            logger.error("OpenAI chat generation failed", error=str(e), model=self.model_name)
            raise


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI LLM provider"""
    
    def __init__(self, model_name: str = "gpt-4", **kwargs):
        super().__init__(model_name, **kwargs)
        self.client = AzureChatOpenAI(
            deployment_name=model_name,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            openai_api_version=settings.AZURE_OPENAI_VERSION,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000),
            **kwargs
        )
    
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using Azure OpenAI"""
        try:
            with get_openai_callback() as cb:
                response = self.client.predict(prompt)
                
                token_usage = {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens
                }
                self.update_usage_stats(token_usage)
                
                return {
                    "text": response,
                    "usage": token_usage,
                    "cost": 0.0,  # Azure pricing varies by deployment
                    "model": self.model_name,
                    "provider": "azure_openai"
                }
                
        except Exception as e:
            logger.error("Azure OpenAI generation failed", error=str(e), model=self.model_name)
            raise
    
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Azure OpenAI"""
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            with get_openai_callback() as cb:
                response = self.client(langchain_messages)
                
                token_usage = {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens
                }
                self.update_usage_stats(token_usage)
                
                return {
                    "message": {
                        "role": "assistant",
                        "content": response.content
                    },
                    "usage": token_usage,
                    "cost": 0.0,
                    "model": self.model_name,
                    "provider": "azure_openai"
                }
                
        except Exception as e:
            logger.error("Azure OpenAI chat generation failed", error=str(e), model=self.model_name)
            raise


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, model_name: str = "llama2", **kwargs):
        super().__init__(model_name, **kwargs)
        self.client = Ollama(
            model=model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=kwargs.get("temperature", 0.7),
            **kwargs
        )
    
    async def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using Ollama"""
        try:
            response = self.client(prompt)
            
            # Ollama doesn't provide token counts, so we estimate
            estimated_tokens = len(prompt.split()) + len(response.split())
            token_usage = {
                "total_tokens": estimated_tokens,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response.split())
            }
            self.update_usage_stats(token_usage)
            
            return {
                "text": response,
                "usage": token_usage,
                "cost": 0.0,  # Local models have no per-token cost
                "model": self.model_name,
                "provider": "ollama"
            }
            
        except Exception as e:
            logger.error("Ollama generation failed", error=str(e), model=self.model_name)
            raise
    
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Ollama"""
        try:
            # Ollama's chat model handling (simplified)
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            prompt += "\nassistant:"
            
            response = self.client(prompt)
            
            # Estimate token usage
            estimated_tokens = len(prompt.split()) + len(response.split())
            token_usage = {
                "total_tokens": estimated_tokens,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response.split())
            }
            self.update_usage_stats(token_usage)
            
            return {
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "usage": token_usage,
                "cost": 0.0,
                "model": self.model_name,
                "provider": "ollama"
            }
            
        except Exception as e:
            logger.error("Ollama chat generation failed", error=str(e), model=self.model_name)
            raise


class LLMService:
    """Main LLM service that manages different providers"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_provider = settings.DEFAULT_LLM_PROVIDER
        self.default_model = settings.DEFAULT_MODEL
        
        # Initialize available providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers"""
        try:
            # OpenAI
            if settings.OPENAI_API_KEY:
                self.providers["openai"] = OpenAIProvider(self.default_model)
                logger.info("OpenAI provider initialized")
            
            # Azure OpenAI
            if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
                self.providers["azure_openai"] = AzureOpenAIProvider(self.default_model)
                logger.info("Azure OpenAI provider initialized")
            
            # Ollama (local)
            try:
                self.providers["ollama"] = OllamaProvider(self.default_model)
                logger.info("Ollama provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize Ollama provider", error=str(e))
            
            if not self.providers:
                logger.error("No LLM providers available!")
                
        except Exception as e:
            logger.error("Failed to initialize LLM providers", error=str(e))
    
    def get_provider(self, provider_name: Optional[str] = None, model_name: Optional[str] = None) -> BaseLLMProvider:
        """Get LLM provider by name"""
        provider_name = provider_name or self.default_provider
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available. Available: {list(self.providers.keys())}")
        
        provider = self.providers[provider_name]
        
        # If a different model is requested, create a new provider instance
        if model_name and model_name != provider.model_name:
            if provider_name == "openai":
                return OpenAIProvider(model_name)
            elif provider_name == "azure_openai":
                return AzureOpenAIProvider(model_name)
            elif provider_name == "ollama":
                return OllamaProvider(model_name)
        
        return provider
    
    async def generate_text(
        self,
        prompt: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using specified provider"""
        provider = self.get_provider(provider_name, model_name)
        
        start_time = datetime.now()
        try:
            result = await provider.generate_text(prompt, **kwargs)
            
            # Add timing information
            result["generation_time"] = (datetime.now() - start_time).total_seconds()
            result["timestamp"] = datetime.now().isoformat()
            
            logger.info(
                "Text generation completed",
                provider=result["provider"],
                model=result["model"],
                tokens=result["usage"]["total_tokens"],
                cost=result["cost"],
                time=result["generation_time"]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Text generation failed",
                provider=provider_name,
                model=model_name,
                error=str(e),
                time=(datetime.now() - start_time).total_seconds()
            )
            raise
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion using specified provider"""
        provider = self.get_provider(provider_name, model_name)
        
        start_time = datetime.now()
        try:
            result = await provider.generate_chat(messages, **kwargs)
            
            # Add timing information
            result["generation_time"] = (datetime.now() - start_time).total_seconds()
            result["timestamp"] = datetime.now().isoformat()
            
            logger.info(
                "Chat generation completed",
                provider=result["provider"],
                model=result["model"],
                tokens=result["usage"]["total_tokens"],
                cost=result["cost"],
                time=result["generation_time"]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Chat generation failed",
                provider=provider_name,
                model=model_name,
                error=str(e),
                time=(datetime.now() - start_time).total_seconds()
            )
            raise
    
    async def generate_user_story(
        self,
        requirements: str,
        context: Optional[str] = None,
        persona: Optional[str] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate user story from requirements"""
        
        # Build the prompt for user story generation
        system_prompt = """You are an expert business analyst specializing in writing clear, actionable user stories. 
Your task is to convert requirements into well-structured user stories following the format:
"As a [persona], I want [functionality] so that [benefit]."

Guidelines:
1. Each user story should be independent and testable
2. Focus on user value and clear acceptance criteria
3. Use specific, actionable language
4. Include relevant acceptance criteria
5. Consider edge cases and constraints

Return your response as a JSON object with the following structure:
{
    "user_stories": [
        {
            "title": "Brief descriptive title",
            "persona": "The user type/role",
            "functionality": "What the user wants to do",
            "benefit": "Why they want to do it/value gained",
            "story_text": "Complete user story in standard format",
            "acceptance_criteria": ["Criterion 1", "Criterion 2", ...],
            "priority": "high|medium|low",
            "complexity": "simple|medium|complex",
            "estimated_points": 1-13
        }
    ],
    "metadata": {
        "total_stories": number,
        "confidence_score": 0.0-1.0,
        "notes": "Any additional notes or assumptions"
    }
}"""

        user_prompt = f"""
Requirements: {requirements}

Additional Context: {context or "None provided"}

Target Persona: {persona or "Please identify appropriate personas from the requirements"}

Please generate comprehensive user stories based on these requirements."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            result = await self.generate_chat(
                messages=messages,
                provider_name=provider_name,
                model_name=model_name,
                temperature=0.7,
                max_tokens=3000
            )
            
            # Try to parse the JSON response
            import json
            try:
                user_stories_data = json.loads(result["message"]["content"])
                result["parsed_stories"] = user_stories_data
                result["success"] = True
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse user story JSON", error=str(e))
                result["parsed_stories"] = None
                result["success"] = False
                result["parse_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error("User story generation failed", error=str(e))
            raise
    
    async def improve_user_story(
        self,
        user_story: Dict[str, Any],
        feedback: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Improve existing user story based on feedback"""
        
        system_prompt = """You are an expert business analyst helping to improve user stories based on feedback.
Analyze the provided user story and feedback, then return an improved version.

Guidelines:
1. Address all points in the feedback
2. Maintain the core intent of the original story
3. Improve clarity, testability, and completeness
4. Ensure acceptance criteria are specific and measurable

Return the improved user story in the same JSON format as the original."""

        user_prompt = f"""
Original User Story:
{json.dumps(user_story, indent=2)}

Feedback for Improvement:
{feedback}

Please provide an improved version of this user story addressing the feedback."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self.generate_chat(
            messages=messages,
            provider_name=provider_name,
            model_name=model_name,
            temperature=0.5,
            max_tokens=2000
        )
    
    async def analyze_requirements(
        self,
        text: str,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze requirements text and extract key information"""
        
        system_prompt = """You are an expert business analyst. Analyze the provided requirements text and extract:
1. Key functional requirements
2. Non-functional requirements
3. Stakeholders and personas
4. Business rules and constraints
5. Dependencies and assumptions
6. Potential risks or issues

Return your analysis as a structured JSON object."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze these requirements:\n\n{text}"}
        ]
        
        return await self.generate_chat(
            messages=messages,
            provider_name=provider_name,
            model_name=model_name,
            temperature=0.3,
            max_tokens=2500
        )
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    def get_usage_stats(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get usage statistics for providers"""
        if provider_name:
            if provider_name in self.providers:
                return {provider_name: self.providers[provider_name].get_usage_stats()}
            else:
                raise ValueError(f"Provider '{provider_name}' not found")
        
        # Return stats for all providers
        return {
            name: provider.get_usage_stats()
            for name, provider in self.providers.items()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all LLM providers"""
        health_status = {}
        
        for name, provider in self.providers.items():
            try:
                # Simple test generation
                test_result = await provider.generate_text(
                    "Test prompt. Respond with 'OK' if working.",
                    max_tokens=10
                )
                health_status[name] = {
                    "status": "healthy",
                    "model": provider.model_name,
                    "response_time": test_result.get("generation_time", 0)
                }
            except Exception as e:
                health_status[name] = {
                    "status": "unhealthy",
                    "model": provider.model_name,
                    "error": str(e)
                }
        
        return health_status


# Global LLM service instance
llm_service = LLMService()


# Convenience functions
async def generate_text(prompt: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for text generation"""
    return await llm_service.generate_text(prompt, **kwargs)


async def generate_chat(messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Convenience function for chat generation"""
    return await llm_service.generate_chat(messages, **kwargs)


async def generate_user_stories(requirements: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for user story generation"""
    return await llm_service.generate_user_story(requirements, **kwargs)