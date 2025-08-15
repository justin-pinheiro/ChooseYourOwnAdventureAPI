from dataclasses import dataclass

from fastapi import WebSocket

from domain.user import User


@dataclass
class Connection:
    """Represents a client connection to a lobby."""
    socket: WebSocket
    user: User
    ready: bool = False

    def to_dict(self):
        return {
            "user": self.user.to_dict(),
            "ready": self.ready
        }
