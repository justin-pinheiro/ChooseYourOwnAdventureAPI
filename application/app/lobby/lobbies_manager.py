import json
from typing import Dict
import uuid
from application.app.adventure.adventure_exceptions import AdventureNotFoundException
from application.app.adventure.adventure_loader import AdventureLoader
from application.app.lobby.lobby_exceptions import ConnectionNotFoundException, LobbyIsFullException, LobbyNotFound
from domain.connection import Connection
from domain.game_state import GameState
from fastapi import WebSocket, WebSocketDisconnect

from domain.lobby import Lobby
from domain.user import User
from ..game.game_handler import GameHandler

class LobbiesManager:
    """
    Handles all lobbies and their clients connections.
    """
    def __init__(self):
        self.lobbies: Dict[str, Lobby] = {}  # key is lobby ID, value is a Lobby object.
        self.game_handler = GameHandler()

    def create_lobby(self, max_players: int, adventure_id: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        
        if max_players < 1:
            raise ValueError("Invalid player limits: max_players must be at least 1")
        
        adventure = AdventureLoader.get_adventure_by_id(adventure_id)
        if not adventure:
            raise AdventureNotFoundException(adventure_id)
        
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, max_players, adventure)
        
        print(f"Lobby '{lobby_id}' created with adventure: '{adventure.title}' (ID: {adventure_id}) and max:{max_players} players.")

        return lobby_id
    
    def get_lobby(self, lobby_id: str) -> Lobby:
        """
        Get a lobby by its ID.
        Raise a LobbyNotFound exception if the lobby id does not exist.
        """
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            raise LobbyNotFound(lobby_id)
        return lobby
    
    def get_all_lobbies(self) -> Dict:
        """Get information about all existing lobbies."""
        lobbies_info = []
        
        for lobby in self.lobbies.values():
            lobbies_info.append(lobby.to_dict())
        
        return {
            "total_lobbies": len(self.lobbies),
            "lobbies": lobbies_info
        }
    
    async def connect(self, socket: WebSocket, lobby_id: str):
        """
        Adds a new client connection to a specified lobby.
        This method raises:
        - LobbyNotFound if lobby does not exist
        - LobbyIsFullException if lobby is full
        """
        lobby = self.get_lobby(lobby_id)

        if lobby.is_full():
            raise LobbyIsFullException(lobby_id)
        
        lobby.connections.append(
            Connection(socket=socket, user=User(f"Player"))
        )
        print(f"Client {socket} successfully connected to lobby '{lobby_id}'. Total connections: {len(lobby.connections)}.")

    async def disconnect(self, socket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies.keys():
            lobby = self.lobbies[lobby_id]
            
            for connection in lobby.connections:
                if connection.socket == socket:
                    lobby.connections.remove(connection)
                    print(f"Client {socket} removed from lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
                    await self.broadcast_lobby_info(lobby_id)
                    break
                
            if not lobby.connections:
                del self.lobbies[lobby_id]
                print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast_lobby_info(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return
        
        message = {
            "type" : "lobby_info",
            "lobby" : lobby.to_dict()
        }

        connections = lobby.connections.copy()
        for connection in connections:
            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)
                self.broadcast_lobby_info(lobby_id)
            except Exception as e:
                print(f"Error broadcasting to {connection.socket}: {e}")

    def _get_connection_by_socket(self, lobby_id: str, socket: WebSocket):
        """
        Helper method to find a specific connection in a lobby by its WebSocket.
        
        :raises ConnectionNotFoundException: If no matching connection is found.
        """
        lobby = self.get_lobby(lobby_id)
        for connection in lobby.connections:
            if connection.socket == socket:
                return connection
        raise ConnectionNotFoundException(f"Connection not found for socket in lobby '{lobby_id}'.")

    async def switch_client_ready_state(self, websocket: WebSocket, lobby_id: str) -> bool:
        """Switches the ready state of a client."""
        connection = self._get_connection_by_socket(lobby_id, websocket)
        if not connection:
            return None
            
        connection.is_ready = not connection.is_ready
        print(f"Player '{connection.user.name}' in lobby '{lobby_id}' toggled ready state to: {connection.is_ready}")
        return connection.is_ready

    async def handle_client_message(self, websocket: WebSocket, lobby_id: str, data: str):
        """
        Handles incoming messages from a client by delegating to the GameHandler.
        """
        try:
            lobby = self.get_lobby(lobby_id)
            await self.game_handler.handle_client_message(websocket, lobby, data)
            await self.broadcast_lobby_info(lobby_id)
        except Exception as e:
            print(f"An error occurred while processing message in lobby '{lobby_id}': {e}")
