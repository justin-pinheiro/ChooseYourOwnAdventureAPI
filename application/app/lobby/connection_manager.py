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
        if len(lobby.users) >= lobby.max_players:
            raise HTTPException(status_code=403, detail="Lobby is full")

        await websocket.accept()
        
        # Find an available id
        player_id = 1
        while any(user.name == f"Player {player_id}" for user in lobby.users):
            player_id += 1

        # Add the user to the list
        lobby.users.append(User(websocket, f"Player {player_id}"))
        
        print(f"Client connected to lobby '{lobby_id}'. Total clients: {len(lobby.users)}")
        return lobby

    def disconnect(self, websocket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies:
            lobby = self.lobbies[lobby_id]
            
            for user in lobby.users:
                if user.webSocket == websocket:
                    lobby.users.remove(user)
                    print(f"Client removed from lobby '{lobby_id}'. Total clients: {len(lobby.users)}")
                    break
                
            # Clean up the lobby if it becomes empty
            if not lobby.users:
                del self.lobbies[lobby_id]
                print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket):
        """Sends a message to all clients in a lobby, except the sender."""
        for user in list(lobby.users):
            if user.webSocket != sender:
                try:
                    await user.webSocket.send_text(message)
                except WebSocketDisconnect:
                    self.disconnect(user.webSocket, lobby.lobby_id)

    async def toggle_player_ready_state(self, websocket: WebSocket, lobby_id: str):
        """Toggles the ready state for a player and broadcasts the updated lobby info."""
        if lobby_id not in self.lobbies:
            return None
        
        lobby = self.lobbies[lobby_id]
        for user in lobby.users:
            if user.webSocket == websocket:
                user.is_ready = not user.is_ready
                print(f"Player '{user.name}' in lobby '{lobby_id}' toggled ready state to: {user.is_ready}")
                await self.broadcast_lobby_info(lobby_id)
                return user.is_ready
        return None

    async def broadcast_lobby_info(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return
        info = {
            "type": "lobby_info",
            "info": {
                "lobby_id": lobby.lobby_id,
                "current_players": len(lobby.users),
                "players": [user.toDict() for user in lobby.users],
                "max_players": lobby.max_players,
                "min_players": lobby.min_players
            }
        }
        
        for user in lobby.users:
            try:
                await user.webSocket.send_json(info)
            except WebSocketDisconnect:
                self.disconnect(user.webSocket, lobby_id)