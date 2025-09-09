import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket

from domain.user import User

@dataclass
class Connection:
    """
        Represents a websocket connection to a lobby.
        It is associated with a unique id and user information.
    """
    socket: WebSocket
    user: User
    is_ready: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict(),
            "is_ready": self.is_ready,
        }
