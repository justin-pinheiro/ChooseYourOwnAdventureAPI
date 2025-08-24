import os
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Response from LLM API call"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class OpenRouterClient:
    """Client for making LLM calls through OpenRouter API"""
    
    def __init__(self, api_key: Optional[str] = None, app_name: str = "ChooseYourOwnStory"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.app_name = app_name
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "mistralai/mistral-small-3.2-24b-instruct:free",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Make a chat completion request to OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: Claude 3.5 Sonnet)
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0-1)
            **kwargs: Additional parameters
        
        Returns:
            LLMResponse object with content and metadata
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": self.app_name,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "error" in data:
                    return LLMResponse(
                        content="",
                        model=model,
                        error=data["error"]["message"]
                    )
                
                choice = data["choices"][0]
                content = choice["message"]["content"]
                usage = data.get("usage", {})
                
                return LLMResponse(
                    content=content,
                    model=model,
                    usage=usage
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            return LLMResponse(content="", model=model, error=error_msg)
        except Exception as e:
            return LLMResponse(content="", model=model, error=str(e))
    
    async def generate_chapter(
        self,
        prompt: str,
        context: str = "",
        num_choices: int = 3,
        model: str = "mistralai/mistral-small-3.2-24b-instruct:free"
    ):
        """
        Generate a complete chapter with story text and choices in a single LLM call
        
        Args:
            prompt: The main prompt for story generation
            context: Additional context about the story
            num_choices: Number of choices to generate
            model: Model to use
        
        Returns:
            Chapter object with text and choices
        """
        from domain.chapter import Chapter
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a creative storyteller for an interactive adventure game. 
                Generate engaging, immersive narrative content with player choices.
                
                Return your response as a JSON object with this exact structure:
                {{
                    "text": "The story text for this chapter (concise but descriptive)",
                    "choices": ["Choice 1", "Choice 2", "Choice 3"]
                }}
                
                Generate exactly {num_choices} meaningful choices that lead to different story paths.
                Keep the story text engaging but concise (2-4 sentences)."""
            }
        ]
        
        if context:
            messages.append({
                "role": "system", 
                "content": f"Story context: {context}"
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        response = await self.chat_completion(
            messages=messages,
            model=model,
            max_tokens=600,
            temperature=0.8
        )
        
        # Parse the JSON response and create Chapter object
        try:
            chapter_data = self.parse_json_response(
                response.content, 
                fallback_value={
                    "text": "You continue your adventure through unknown territory...",
                    "choices": ["Continue forward", "Look around", "Go back"]
                }
            )
            text = chapter_data.get("text", "You continue your adventure...")
            choices = chapter_data.get("choices", ["Continue", "Look around", "Go back"])
            
            return Chapter(text=text, possiblities=choices)
            
        except Exception as e:
            # Fallback chapter if parsing fails
            print(f"[DEBUG] Chapter generation parsing failed: {e}")
            return Chapter(
                text="You continue your adventure through unknown territory...",
                possiblities=["Continue forward", "Look around", "Go back"]
            )

    def parse_json_response(self, response_content: str, fallback_value=None):
        """
        Parse JSON response from LLM, handling various formats including markdown code blocks.
        
        Args:
            response_content: The raw response content from the LLM
            fallback_value: Value to return if parsing fails (default: None)
            
        Returns:
            Parsed JSON object or fallback_value if parsing fails
            
        Raises:
            json.JSONDecodeError: If parsing fails and no fallback_value is provided
        """
        import json
        import re
        
        # Clean the response content
        content = response_content.strip()
        
        # Try to parse as-is first (clean JSON)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        # Look for ```json ... ``` or ``` ... ``` patterns
        json_patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',      # ``` ... ```
            r'`(.*?)`',                 # `...`
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        # Clean the extracted JSON
                        json_content = match.strip()
                        return json.loads(json_content)
                    except json.JSONDecodeError:
                        continue
        
        # Try to find JSON-like structures without markdown
        # Look for content that starts with [ or { and ends with ] or }
        json_like_patterns = [
            r'(\[.*?\])',  # Array pattern
            r'(\{.*?\})',  # Object pattern
        ]
        
        for pattern in json_like_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue
        
        # Try to extract JSON from mixed content
        # Look for the largest JSON-like structure in the response
        lines = content.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        bracket_count = 0
        
        for line in lines:
            stripped_line = line.strip()
            
            # Check if this line starts a JSON structure
            if not in_json and (stripped_line.startswith('[') or stripped_line.startswith('{')):
                in_json = True
                json_lines = [stripped_line]
                brace_count = stripped_line.count('{') - stripped_line.count('}')
                bracket_count = stripped_line.count('[') - stripped_line.count(']')
            elif in_json:
                json_lines.append(stripped_line)
                brace_count += stripped_line.count('{') - stripped_line.count('}')
                bracket_count += stripped_line.count('[') - stripped_line.count(']')
                
                # Check if JSON structure is complete
                if brace_count <= 0 and bracket_count <= 0:
                    try:
                        json_content = '\n'.join(json_lines)
                        return json.loads(json_content)
                    except json.JSONDecodeError:
                        pass
                    in_json = False
                    json_lines = []
                    brace_count = 0
                    bracket_count = 0
        
        # If we still have fallback_value, return it
        if fallback_value is not None:
            return fallback_value
        
        # If no fallback and nothing worked, raise the original error
        raise json.JSONDecodeError(f"Could not parse JSON from response: {content[:200]}...")

async def quick_llm_call(
    prompt: str,
    system_message: str = "",
    model: str = "mistralai/mistral-small-3.2-24b-instruct:free"
) -> str:
    """
    Quick LLM call for simple text generation
    
    Args:
        prompt: User prompt
        system_message: Optional system message
        model: Model to use
        
    Returns:
        Generated text content
    """
    client = OpenRouterClient()
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    response = await client.chat_completion(messages=messages, model=model)
    
    if response.error:
        raise Exception(f"LLM call failed: {response.error}")
    
    return response.content
