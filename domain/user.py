from dataclasses import dataclass
from fastapi import WebSocket

@dataclass
class User:
    """Represents a User and its informations."""
    def __init__(self, name: str):
        self.name = name

    def to_dict(self):
        return {"name": self.name}
