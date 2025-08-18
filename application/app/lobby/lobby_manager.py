# A dedicated class to manage WebSocket connections and lobbies.
from http.client import HTTPException
from typing import Dict
import uuid
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from domain.lobby import Lobby
from domain.user import User
from domain.chapter import Chapter

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
    
    async def start_lobby(self, lobby_id: int):
        """Start a given lobby"""

        lobby = self.lobbies[lobby_id]

        # if(not self.adventure): raise Exception("No adventure selected")

        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready: raise Exception("All players must be ready")

        lobby.game_state.started = True

    async def connect(self, socket: WebSocket, lobby_id: str):
        """Adds a new client connection to a specified lobby."""
        print(f"lobbies ids: {self.lobbies.keys()}")
        if lobby_id not in self.lobbies.keys():
            raise HTTPException(status_code=404, detail="Lobby not found")
        
        lobby = self.lobbies[lobby_id]
        print(f"connections for lobby {lobby_id}: {lobby.connections}")
        if len(lobby.connections) >= lobby.max_players:
            raise HTTPException(status_code=403, detail="Lobby is full")

        await socket.accept()
        
        # Find an available id
        player_id = 1
        while any(connection.user.name == f"Player {player_id}" for connection in lobby.connections):
            player_id += 1

        # Add the connection to the list
        lobby.connections.append(Connection(socket, User(f"Player {player_id}")))
        
        print(f"Client {socket} connected to lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
        return lobby

    async def toggle_player_ready_state(self, socket: WebSocket, lobby_id: str):
        """Toggles the ready state for a player and broadcasts the updated lobby info."""
        if lobby_id not in self.lobbies:
            return None
        
        lobby = self.lobbies[lobby_id]
        for connection in lobby.connections:
            if connection.socket == socket:
                connection.is_ready = not connection.is_ready
                print(f"Player '{connection.user.name}' in lobby '{lobby_id}' toggled ready state to: {connection.is_ready}")
                await self.broadcast_lobby(lobby_id)
                return connection.is_ready
        return None

    def disconnect(self, socket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies.keys():
            lobby = self.lobbies[lobby_id]
            
            for connection in lobby.connections:
                if connection.socket == socket:
                    lobby.connections.remove(connection)
                    print(f"Client {socket} removed from lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
                    break
                
            # Clean up the lobby if it becomes empty
            if not lobby.connections:
                del self.lobbies[lobby_id]
                print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def start_new_round(self, lobby_id: int):
        """Start a new round, and send a message to inform all players"""
        
        for i, connection in enumerate(self.lobbies[lobby_id].connections):
            
            text = "Testing"
            choices = ["Choix 1", "Choix 2", "Choix 3"]
            self.lobbies[lobby_id].game_state.chapters.append(Chapter(text, choices))

            message = {
                "type" : "new_round",
                "info" : {
                    "text" : text,
                    "choices" : choices,
                }
            }
            
            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket):
        """Sends a message to all clients in a lobby, except the sender."""
        for connection in list[Connection](lobby.connections):
            try:
                if(sender != connection.socket) : await connection.socket.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby.id)

    async def broadcast_lobby(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return # TO-DO handle exception
        
        message = {
            "type" : "lobby_info",
            "info" : lobby.to_dict()
        }
        
        for connection in lobby.connections:
            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)