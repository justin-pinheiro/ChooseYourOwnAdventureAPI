from fastapi import WebSocket

class User:
    
    """Represents a User and its informations."""
    def __init__(self, webSocket : WebSocket, name: str):
        self.webSocket = webSocket
        self.name = name
        

    def toDict(self):
        return {"name": self.name}