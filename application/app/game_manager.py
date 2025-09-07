from typing import Dict
import uuid
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect
from domain.game_state import GameState
from domain.adventure import Adventure

from .story_manager import StoryManager

class GameManager:
    """
    Manages in-game operations: story generation, choice handling, and game progression.
    """
    def __init__(self):
        self.story_manager = StoryManager()

    async def submit_choice(self, game_state: GameState, player_id: str, message):
        """Handle player choice submission"""

        if player_id in game_state.chapters and game_state.chapters[player_id]:
            latest_chapter = game_state.chapters[player_id][-1]
            latest_chapter.choice = message["choice_index"]
        
    async def start_new_round(self, game_state: GameState, adventure : Adventure):
        """Start a new round, and send a message to inform all players"""

        game_state.round += 1

        for player_id, chapters in game_state.chapters.items():

            new_chapter = await self.story_manager.generate_chapter(
                player_name="Jean",
                adventure=adventure,
                previous_chapters=None,
                last_choice=None
            )
            
            chapters.append(new_chapter)
