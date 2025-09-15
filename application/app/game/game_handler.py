import uuid
from domain.game_state import GameState
from fastapi import WebSocket, WebSocketDisconnect
from domain.lobby import Lobby

class GameHandler:
    """
    Handles all game-related logic and message processing.
    This class is responsible for managing the game state, processing player actions, and coordinating game progression.
    """
    async def submit_choice(self, lobby: Lobby, sender: WebSocket, choice: int):
        """Handle player choice submission"""
        sender_connection = self._get_connection_by_socket(lobby, sender)
        if not sender_connection:
            return

        sender_uuid = uuid.UUID(sender_connection.id)
        
        if sender_uuid in self.game_state.chapters and self.game_state.chapters[sender_uuid]:
            latest_chapter = self.game_state.chapters[sender_uuid][-1]
            latest_chapter.choice = choice["choice_index"]

        if self._are_all_choices_made(lobby):
            await self.start_new_round(lobby)

        print(f"Lobby '{lobby.id}': {sender_connection.user.name} submitted choice: {choice}")

