from http.client import HTTPException
from typing import Dict
import uuid
from application.app.adventure_loader import AdventureLoader
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from domain.lobby import Lobby
from domain.user import User
from .game_manager import GameManager

class LobbyManager:
    """
    Manages all active WebSocket connections, organized by Lobby objects.
    """
    def __init__(self, game_manager : GameManager):
        self.lobbies: Dict[str, Lobby] = {} # The key is the lobby ID, and the value is a Lobby object.
        self.game_manager = game_manager

    def create_lobby(self, max_players: int, adventure_id: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        
        if max_players < 1:
            raise HTTPException(status_code=400, detail="Invalid player limits: max_players must be at least 1")
        
        try:
            adventure = AdventureLoader.get_adventure_by_id(adventure_id)
            if not adventure:
                raise HTTPException(status_code=404, detail=f"Adventure with ID {adventure_id} not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load adventure: {str(e)}")
            
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, max_players, adventure_id)
        self.lobbies[lobby_id].game_state.adventure = adventure
        
        print(f"Lobby '{lobby_id}' created with adventure: '{adventure.title}' (ID: {adventure_id}) and max:{max_players} players.")

        return lobby_id
    
    def get_lobby(self, lobby_id: str) -> Lobby:
        """Get a lobby by its ID."""
        return self.lobbies.get(lobby_id)
    
    def get_all_lobbies(self) -> Dict:
        """Get information about all existing lobbies."""
        lobbies_info = []
        
        for lobby in self.lobbies.values():
            lobbies_info.append(lobby.to_dict())
        
        return {
            "total_lobbies": len(self.lobbies),
            "lobbies": lobbies_info
        }
    
    async def start_lobby(self, lobby_id: int):
        """Start a given lobby"""

        lobby = self.lobbies[lobby_id]

        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready: raise Exception("All players must be ready")

        lobby.game_state.started = True

        for connection in list[Connection](lobby.connections):

            lobby.game_state.chapters[connection.id] = []

            message = {
                "type" : "start_adventure",
                "info" : {
                    "success": True,
                }
            }

            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby.id)

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
        
        # Find an available name
        player_id = 1
        while any(connection.user.name == f"Player {player_id}" for connection in lobby.connections):
            player_id += 1

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
    
    async def submit_choice(self, lobby_id: str, sender: WebSocket, message):
        """Handle player choice submission"""
        
        if lobby_id not in self.lobbies: return None
        else : lobby : Lobby = self.lobbies[lobby_id]
        
        sender_name = "Unknown"
        sender_connection = None
        for connection in lobby.connections:
            if connection.socket == sender:
                sender_name = connection.user.name
                sender_connection = connection
                break
            
        if not sender_connection:
            return
        
        sender_uuid = uuid.UUID(sender_connection.id)
        
        self.game_manager.submit_choice(lobby, sender_uuid, message)
        
        all_choices_made = True
        for connection in lobby.connections:
            connection_uuid = uuid.UUID(connection.id)
            if (connection_uuid not in lobby.game_state.chapters or 
                not lobby.game_state.chapters[connection_uuid] or 
                lobby.game_state.chapters[connection_uuid][-1].choice == -1):
                all_choices_made = False
                break

        if all_choices_made: await self.game_manager.start_new_round(lobby)

        print(f"Lobby '{lobby.id}' : {sender_name} submitted : {message}")
            
        return None

    async def start_new_round(self, lobby: Lobby):
        """Start a new round, and send a message to inform all players"""

        if not lobby.game_state.adventure:
            print(f"[ERROR] No adventure set for lobby {lobby.id}")
            return
        
        self.game_manager.start_new_round()

        for connection in lobby.connections:

            message = {
                "type" : "new_round",
                "info" : {
                    "round_index" : lobby.game_state.round,
                    "text" : lobby.game_state.chapters[connection.id][-1].text,
                    "choices" : lobby.game_state.chapters[connection.id][-1].possiblities,
                }
            }
            
            try:
                await connection.socket.send_json(message)
            except Exception as e:
                print(f"[ERROR] Error sending message to {connection.user.name}: {e}")


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

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket = None):
        """Sends a message to all clients in a lobby, except the sender."""
        for connection in list[Connection](lobby.connections):
            try:
                if(sender != connection.socket) : await connection.socket.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby.id)

    async def broadcast_lobby(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return
        
        message = {
            "type" : "lobby_info",
            "info" : lobby.to_dict()
        }

        for connection in lobby.connections:
            print("- " + connection.user.name)
            try:
                print(f"Broadcast : {message}")
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)