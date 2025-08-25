import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket

from domain.user import User

@dataclass
class Connection:
    """Represents a client connection to a lobby."""
    socket: WebSocket
    user: User
    character: str = "Jean"
    is_ready: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return {
            "user": self.user.to_dict(),
            "is_ready": self.is_ready,
        }
