from dataclasses import dataclass
from fastapi import WebSocket

@dataclass
class User:
    """Represents a User and its informations."""
    def __init__(self, webSocket : WebSocket, name: str, is_ready = False):
        self.webSocket = webSocket
        self.name = name
        self.is_ready = is_ready
        

    def to_dict(self):
        return {"name": self.name, "is_ready": self.is_ready}
