from fastapi import WebSocket, WebSocketDisconnect
from domain.game_state import GameState
from domain.adventure import Adventure

from .story_manager import StoryManager

class GameManager:
    """
    Manages in-game operations: story generation, choice handling, and game progression.
    """
    def __init__(self):
        self.story_manager : StoryManager = None
        self.game_state = GameState()

    async def start_game(self, adventure : Adventure):
        self.story_manager = StoryManager(adventure)
        self.game_state.started = True

    async def submit_choice(self, player_id: str, message):
        """Handle player choice submission"""

        if player_id in self.game_state.chapters and self.game_state.chapters[player_id]:
            latest_chapter = self.game_state.chapters[player_id][-1]
            latest_chapter.choice = message["choice_index"]
        
    async def start_new_round(self):
        """Start a new round"""

        self.game_state.round += 1

        for player_id, chapters in self.game_state.chapters.items():

            new_chapter = await self.story_manager.generate_chapter(
                player_name="Jean",
                previous_chapters=None,
                last_choice=None
            )
            
            chapters.append(new_chapter)
