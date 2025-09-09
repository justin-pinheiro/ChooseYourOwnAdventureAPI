from typing import Set, List
from dataclasses import dataclass, field
from domain.adventure import Adventure
from domain.connection import Connection
from domain.game_state import GameState
from fastapi import WebSocket

@dataclass
class Lobby:
    """Represents a single lobby with player limits and connections."""
    id: str
    max_players: int
    adventure: Adventure
    game_state: GameState = GameState()
    connections: List[Connection] = field(default_factory=list)
    host: WebSocket = None

    def is_full(self):
        return len(self.connections) >= self.max_players

    def to_dict(self):
        return {
            "id": self.id,
            "max_players": self.max_players,
            "current_players": len(self.connections),
            "adventure_title": self.adventure.title if self.adventure else None,
            "adventure_description": self.adventure.description if self.adventure else None,
            "game_started": self.game_state.started,
            "current_round": self.game_state.round,
            "players": [
                {
                    "name": conn.user.name,
                    "is_ready": conn.is_ready
                } for conn in self.connections
            ],
            "is_full": len(self.connections) >= self.max_players
        }