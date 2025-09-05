import os
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

class OpenRouterClient:
    """Client for making LLM calls through OpenRouter API"""
    
    async def chat_completion(self) -> str:
        """
        Returns a dummy response.
        """
        return "Dummy response."