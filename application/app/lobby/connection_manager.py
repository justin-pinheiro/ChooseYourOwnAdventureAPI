# A dedicated class to manage WebSocket connections and lobbies.
from http.client import HTTPException
from typing import Dict
import uuid
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from domain.lobby import Lobby


class ConnectionManager:
    """
    Manages all active WebSocket connections, organized by Lobby objects.
    """
    def __init__(self):
        # The key is the lobby ID, and the value is a Lobby object.
        self.lobbies: Dict[str, Lobby] = {}

    def create_lobby(self, min_players: int, max_players: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, min_players, max_players)
        print(f"Lobby '{lobby_id}' created with min:{min_players}, max:{max_players} players.")
        return lobby_id

    async def connect(self, websocket: WebSocket, lobby_id: str):
        """Adds a new client connection to a specified lobby."""
        # Validate lobby existence and player count before accepting
        if lobby_id not in self.lobbies:
            raise HTTPException(status_code=404, detail="Lobby not found")
        
        lobby = self.lobbies[lobby_id]
        if len(lobby.active_connections) >= lobby.max_players:
            raise HTTPException(status_code=403, detail="Lobby is full")

        await websocket.accept()
        lobby.active_connections.add(websocket)
        print(f"Client connected to lobby '{lobby_id}'. Total clients: {len(lobby.active_connections)}")
        return lobby

    def disconnect(self, websocket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies:
            lobby = self.lobbies[lobby_id]
            if websocket in lobby.active_connections:
                lobby.active_connections.remove(websocket)
                print(f"Client removed from lobby '{lobby_id}'. Total clients: {len(lobby.active_connections)}")
                # Clean up the lobby if it becomes empty
                if not lobby.active_connections:
                    del self.lobbies[lobby_id]
                    print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket):
        """Sends a message to all clients in a lobby, except the sender."""
        for client_ws in list(lobby.active_connections):
            if client_ws != sender:
                try:
                    await client_ws.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(client_ws, lobby.lobby_id)