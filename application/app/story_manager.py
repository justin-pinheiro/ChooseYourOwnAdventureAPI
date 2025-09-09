from typing import List, Dict, Any
from application.app.llm_client import OpenRouterClient
from domain.chapter import Chapter
from domain.adventure import Adventure


class StoryManager:
    """
    Manages story generation, LLM interactions, and narrative logic.
    Separated from game mechanics to focus purely on storytelling.
    """
    
    def __init__(self, adventure : Adventure):
        self.adventure = adventure
        self.llm_client = OpenRouterClient()

    async def generate_chapter(
        self, 
        player_name: str, 
        previous_chapters: List[Chapter] = None, 
        last_choice: str = None
    ) -> Chapter:
        """
        Generate a single chapter for a specific player.

        Returns:
            Default Chapter object
        """
        print(f"[STORY] Generating chapter for {player_name}")
        
        chapter = Chapter(
            self.llm_client.chat_completion(),
            possiblities=["choice 1", "choice 2", "choice 3"],
            choice=None
        )
        
        print(f"[STORY] Generated chapter for {player_name}: {len(chapter.text)} chars, {len(chapter.possiblities)} choices")
        return chapter
