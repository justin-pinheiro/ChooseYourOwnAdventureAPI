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
            "lobby": {
                "id": self.id,
                "max_players": self.max_players,
                "current_players": len(self.connections),
                "adventure_id": self.adventure_id,
                "adventure_title": self.game_state.adventure.title if self.game_state.adventure else None,
                "adventure_description": self.game_state.adventure.description if self.game_state.adventure else None,
                "game_started": self.game_state.started,
                "current_round": self.game_state.round,
                "players": [
                    {
                        "name": conn.user.name,
                        "is_ready": conn.is_ready
                    } for conn in self.connections
                ],
                "is_full": len(self.connections) >= self.max_players,
                "can_join": len(self.connections) < self.max_players and not self.game_state.started
            }
        }