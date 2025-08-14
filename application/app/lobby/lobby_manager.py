# A dedicated class to manage WebSocket connections and lobbies.
from http.client import HTTPException
from typing import Dict
import uuid
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from domain.lobby import Lobby
from domain.lobby import User


class LobbyManager:
    """
    Manages all active WebSocket connections, organized by Lobby objects.
    """
    def __init__(self):
        # The key is the lobby ID, and the value is a Lobby object.
        self.lobbies: Dict[str, Lobby] = {}

    def create_lobby(self, max_players: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        
        if max_players < 1:
            raise HTTPException(status_code=400, detail="Invalid player limits: max_players must be at least 1")
        
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, max_players)
        print(f"Lobby '{lobby_id}' created with max:{max_players} players.")
        return lobby_id

    async def connect(self, websocket: WebSocket, lobby_id: str):
        """Adds a new client connection to a specified lobby."""
        print(f"lobbies ids: {self.lobbies.keys()}")
        if lobby_id not in self.lobbies.keys():
            raise HTTPException(status_code=404, detail="Lobby not found")
        
        lobby = self.lobbies[lobby_id]
        print(f"connections for lobby {lobby_id}: {lobby.connections}")
        if len(lobby.connections) >= lobby.max_players:
            raise HTTPException(status_code=403, detail="Lobby is full")

        await websocket.accept()

        connection = Connection(websocket, User("player")) # TO-DO : handle user name
        lobby.connections.append(connection)
        
        print(f"Client {websocket} connected to lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
        return lobby

    def disconnect(self, websocket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies.keys():
            lobby = self.lobbies[lobby_id]
            
            for connection in lobby.connections:
                if connection.socket == websocket:
                    lobby.connections.remove(connection)
                    print(f"Client {websocket} removed from lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
                    break
                
            # Clean up the lobby if it becomes empty
            if not lobby.connections:
                del self.lobbies[lobby_id]
                print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket):
        """Sends a message to all clients in a lobby, except the sender."""
        for connection in list(lobby.connections):
            try:
                await connection.socket.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby.id)

    async def broadcast_lobby(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return # TO-DO handle exception
        
        lobby_info = lobby.to_dict()

        for connection in lobby.connections:
            try:
                await connection.socket.send_json(lobby_info)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)