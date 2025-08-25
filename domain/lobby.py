from typing import Set, List
from dataclasses import dataclass, field
from domain.connection import Connection
from domain.game_state import GameState
from fastapi import WebSocket

@dataclass
class Lobby:
    """Represents a single lobby with player limits and connections."""
    id: str
    max_players: int
    adventure_id : int = None
    connections: List[Connection] = field(default_factory=list)
    host: WebSocket = None
    game_state: GameState = field(default_factory=GameState)

    def to_dict(self):
        return {
            "id": self.id,
            "max_players": self.max_players,
            "connections": [conn.to_dict() for conn in self.connections],
            "adventure_id" : self.adventure_id,
            "game_state": self.game_state.to_dict(),
        }