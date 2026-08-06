"""
LLM client for interacting with OpenRouter API
"""

from typing import Optional, Dict, Any, List
import httpx
from app.utils.logger import setup_logger
import os

logger = setup_logger(__name__)


class LLMClient:
    """Client for LLM API calls using OpenRouter"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("LLM_MODEL", "anthropic/claude-3-haiku:beta")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set. LLM calls will fail.")
    
    async def generate_response_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generate LLM response asynchronously
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use
            
        Returns:
            Generated response
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self._call_api_async(
            messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            model=model or self.model
        )
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Generate LLM response synchronously (safe inside FastAPI async handlers).
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self._call_api_sync(
            messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            model=model or self.model,
        )
    
    async def _call_api_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> str:
        """Make async API call to OpenRouter"""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Enterprise RAG"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """Chat with LLM using message history."""
        return self._call_api_sync(
            messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            model=model or self.model,
        )

    def _call_api_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: str
    ) -> str:
        """Make synchronous API call to OpenRouter."""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Enterprise RAG",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise
    
    def stream_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ):
        """
        Stream LLM response (generator)
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use
            
        Yields:
            Response chunks
        """
        # For simplicity, return full response. In production, implement actual streaming
        response = self.generate_response(prompt, system_prompt, temperature, max_tokens, model)
        yield response
