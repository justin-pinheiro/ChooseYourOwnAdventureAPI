from enum import Enum
import json
import logging
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

class MessageType(Enum):
    START_GAME = "START_GAME"
    SWITCH_READY_STATE = "SWITCH_READY_STATE"
    SUBMIT_CHOICE = "SUBMIT_CHOICE"

    def from_str(value: str):
        try:
            return MessageType[value]
        except KeyError:
            raise ValueError(f"'{value}' is not a valid MessageType") 

class LobbiesManager:
    """
    Handles all lobbies and their clients connections.
    """
    def __init__(self):
        self.lobbies: Dict[str, Lobby] = {}  # key is lobby ID, value is a Lobby object.
        self.game_handler = GameHandler()
        self.logger = logging.getLogger()

    def create_lobby(self, max_players: int, adventure_id: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        
        if max_players < 1:
            raise ValueError("Invalid player limits: max_players must be at least 1")
        
        adventure = AdventureLoader.get_adventure_by_id(adventure_id)
        if not adventure:
            raise AdventureNotFoundException(adventure_id)
        
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, max_players, adventure)
        
        self.logger.info(f"Lobby '{lobby_id}' created with adventure: '{adventure.title}' (ID: {adventure_id}) and max:{max_players} players.")

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
        self.logger.info(f"Client {socket} successfully connected to lobby '{lobby_id}'. Total connections: {len(lobby.connections)}.")

    async def disconnect(self, socket: WebSocket, lobby_id: str):
        """Removes a client connection from a specified lobby."""
        if lobby_id in self.lobbies.keys():
            lobby = self.lobbies[lobby_id]
            
            for connection in lobby.connections:
                if connection.socket == socket:
                    lobby.connections.remove(connection)
                    self.logger.info(f"Client {socket} removed from lobby '{lobby_id}'. Total clients: {len(lobby.connections)}")
                    await self.broadcast_lobby_info(lobby_id)
                    break
                
            if not lobby.connections:
                del self.lobbies[lobby_id]
                self.logger.info(f"Lobby '{lobby_id}' is now empty and has been removed.")

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
                await self.disconnect(connection.socket, lobby_id)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {connection.socket}: {e}")

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

    async def _switch_client_ready_state(self, websocket: WebSocket, lobby_id: str) -> bool:
        """Switches the ready state of a client."""
        connection = self._get_connection_by_socket(lobby_id, websocket)
        if not connection:
            return None
            
        connection.is_ready = not connection.is_ready
        self.logger.info(f"Player '{connection.user.name}' in lobby '{lobby_id}' toggled ready state to: {connection.is_ready}")
        return connection.is_ready

    def _start_game(self, lobby_id: str):
        """
            Start the game in a given lobby.
            Raise a LobbyNotFound exception if lobby_id does not exist.
        """
        lobby = self.get_lobby(lobby_id)
        lobby.game_state.started = True

    def _parse_client_message(self, message : str):
        """
            Parses a command sent by a client.
        """
        try:
            data = json.loads(message)
            message_type = MessageType.from_str(data.get("type"))
            return message_type, data.get("value")
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse client message: {e}")
            raise e

    async def handle_client_message(self, websocket: WebSocket, lobby_id: str, type: MessageType, message: str):
        """
        Handles incoming messages from a client by delegating to the GameHandler.
        """
        match type:
            case MessageType.SWITCH_READY_STATE:
                await self._switch_client_ready_state(websocket, lobby_id)
                await self.broadcast_lobby_info(lobby_id)
            case MessageType.START_GAME:
                self._start_game(lobby_id)
                await self.broadcast_lobby_info(lobby_id)
            case MessageType.SUBMIT_CHOICE:
                await self.game_handler.submit_choice(lobby.game_state, data)

    def _are_all_connections_ready(self, lobby: Lobby) -> bool:
        """Check if all clients in the lobby have made their choices."""
        for connection in lobby.connections:
            connection_uuid = uuid.UUID(connection.id)
            if (connection_uuid not in self.game_manager.game_state.chapters or
                not self.game_manager.game_state.chapters[connection_uuid] or
                self.game_manager.game_state.chapters[connection_uuid][-1].choice == -1):
                return False
        return True
