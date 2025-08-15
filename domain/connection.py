from dataclasses import dataclass

from fastapi import WebSocket

from domain.user import User

@dataclass
class Connection:
    """Represents a client connection to a lobby."""
    socket: WebSocket
    user: User
    is_ready: bool = False

    def to_dict(self):
        return {
            "user": self.user.to_dict(),
            "is_ready": self.is_ready
        }
