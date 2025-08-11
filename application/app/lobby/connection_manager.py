# A dedicated class to manage WebSocket connections and lobbies.
from http.client import HTTPException
from typing import Dict
import uuid
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

import random

from domain.lobby import Lobby
from domain.lobby import User


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
        if len(lobby.connections) >= lobby.max_players:
            raise HTTPException(status_code=403, detail="Lobby is full")

        await websocket.accept()
        lobby.connections.add(websocket)
        
        # Find an available id
        player_id = 1
        while any(user.name == f"Player {player_id}" for user in lobby.users):
            player_id += 1

        lobby.users.append(User(f"Player {player_id}"))
            
        print(f"Client connected to lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
        return lobby

    def disconnect(self, websocket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies:
            lobby = self.lobbies[lobby_id]
            
            if websocket in lobby.connections:
                
                index = list(lobby.connections).index(websocket)
                
                lobby.connections.remove(websocket)
                if 0 <= index < len(lobby.users): lobby.users.pop(index)
                
                print(f"Client removed from lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
                
                # Clean up the lobby if it becomes empty
                if not lobby.connections:
                    del self.lobbies[lobby_id]
                    print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket):
        """Sends a message to all clients in a lobby, except the sender."""
        for client_ws in list(lobby.connections):
            if client_ws != sender:
                try:
                    await client_ws.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(client_ws, lobby.lobby_id)

    async def broadcast_lobby_info(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return
        info = {
            "type": "lobby_info",
            "info": {
                "lobby_id": lobby.lobby_id,
                "current_players": len(lobby.connections),
                "players": [user.toDict() for user in lobby.users],
                "max_players": lobby.max_players,
                "min_players": lobby.min_players
            }
        }
        
        for connection in lobby.connections:
            try:
                await connection.send_json(info)
            except WebSocketDisconnect:
                self.disconnect(connection, lobby_id)