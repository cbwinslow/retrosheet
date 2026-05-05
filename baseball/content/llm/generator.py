"""
LLM Content Generator

Interface to various LLM APIs for generating baseball analysis content.
Handles prompt engineering, response parsing, and quality control.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import openai
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """Request structure for content generation."""
    template_name: str
    context: Dict[str, Any]
    content_type: str
    max_tokens: int = 1000
    temperature: float = 0.7
    model: str = "gpt-4"


@dataclass
class GenerationResponse:
    """Response structure for generated content."""
    content: str
    model_used: str
    tokens_used: int
    generation_time: float
    quality_score: Optional[float] = None
    metadata: Dict[str, Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content based on the request."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for content generation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize OpenAI provider."""
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAI provider initialized with model: {model}")
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using OpenAI API."""
        start_time = datetime.now()
        
        try:
            # Build system prompt based on content type
            system_prompt = self._build_system_prompt(request.content_type)
            
            # Build user prompt with context
            user_prompt = self._build_user_prompt(request)
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=request.model or self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # Calculate generation time
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Extract response
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Create response object
            result = GenerationResponse(
                content=content,
                model_used=response.model,
                tokens_used=tokens_used,
                generation_time=generation_time,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
            logger.info(f"Generated {len(content)} characters using {response.model}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def _build_system_prompt(self, content_type: str) -> str:
        """Build system prompt based on content type."""
        base_prompt = (
            "You are an expert baseball analyst and writer. "
            "Create engaging, insightful baseball content that is both "
            "statistically sound and accessible to fans. "
            "Use the provided data and predictions to create compelling narratives."
        )
        
        type_specific = {
            "game-preview": (
                "Focus on upcoming game analysis, pitching matchups, "
                "team trends, and predictions. Make it exciting and informative."
            ),
            "player-analysis": (
                "Focus on player performance, trends, strengths/weaknesses, "
                "and historical context. Provide deep insights."
            ),
            "statistical-breakdown": (
                "Focus on advanced statistics, trends, and what the numbers mean. "
                "Make complex stats understandable."
            ),
            "prediction-explanation": (
                "Focus on explaining model predictions, factors influencing outcomes, "
                "and probability analysis. Make predictions understandable."
            )
        }
        
        return base_prompt + "\n\n" + type_specific.get(content_type, base_prompt)
    
    def _build_user_prompt(self, request: GenerationRequest) -> str:
        """Build user prompt with context data."""
        context_str = json.dumps(request.context, indent=2, default=str)
        
        prompt = f"""
Generate a {request.content_type} article using the following data and context:

Template: {request.template_name}

Context Data:
{context_str}

Requirements:
- Create a compelling title
- Write 2-4 paragraphs of engaging content
- Incorporate the provided data naturally
- Maintain a professional yet accessible tone
- Include specific numbers and predictions when available
- End with a clear takeaway or prediction

Format the response as clean text without markdown formatting.
"""
        return prompt.strip()


class ContentGenerator:
    """Main content generation orchestrator."""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        """Initialize content generator."""
        self.provider = provider
        self.generation_history: List[GenerationResponse] = []
        logger.info("Content generator initialized")
    
    def set_provider(self, provider: LLMProvider) -> None:
        """Set the LLM provider."""
        self.provider = provider
        logger.info(f"LLM provider set: {type(provider).__name__}")
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate content using the configured LLM provider.
        
        Args:
            request: Content generation request
            
        Returns:
            Generated content response
            
        Raises:
            ValueError: If no provider is configured
        """
        if not self.provider:
            raise ValueError("No LLM provider configured. Call set_provider() first.")
        
        try:
            response = await self.provider.generate_content(request)
            
            # Store in history
            self.generation_history.append(response)
            
            # Log generation stats
            logger.info(
                f"Content generated: {len(response.content)} chars, "
                f"{response.tokens_used} tokens, {response.generation_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about content generation."""
        if not self.generation_history:
            return {"total_generations": 0}
        
        total = len(self.generation_history)
        total_tokens = sum(r.tokens_used for r in self.generation_history)
        avg_time = sum(r.generation_time for r in self.generation_history) / total
        avg_tokens = total_tokens / total
        
        return {
            "total_generations": total,
            "total_tokens_used": total_tokens,
            "average_generation_time": avg_time,
            "average_tokens_per_generation": avg_tokens,
            "last_generation": self.generation_history[-1].generation_time
        }
    
    def validate_content_quality(self, content: str) -> Dict[str, Any]:
        """
        Basic content quality validation.
        
        Args:
            content: Generated content to validate
            
        Returns:
            Quality assessment
        """
        if not content:
            return {"valid": False, "issues": ["Empty content"]}
        
        issues = []
        
        # Length checks
        if len(content) < 100:
            issues.append("Content too short (< 100 chars)")
        elif len(content) > 2000:
            issues.append("Content too long (> 2000 chars)")
        
        # Basic structure checks
        sentences = content.split('.')
        if len(sentences) < 3:
            issues.append("Too few sentences")
        
        # Check for data inclusion (should have numbers)
        has_numbers = any(char.isdigit() for char in content)
        if not has_numbers:
            issues.append("No numerical data found")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "length": len(content),
            "sentence_count": len(sentences),
            "has_numbers": has_numbers
        }
