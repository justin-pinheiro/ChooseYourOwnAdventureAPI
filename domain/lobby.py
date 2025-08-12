from typing import Set, List
from fastapi import WebSocket
from .user import User

class Lobby:
    """Represents a single lobby with player limits and connections."""
    def __init__(self, lobby_id: str, min_players: int, max_players: int):
        self.lobby_id = lobby_id
        self.min_players = min_players
        self.max_players = max_players
        self.users: List[User] = []