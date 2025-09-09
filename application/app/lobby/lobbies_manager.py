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
from ..game_manager import GameManager

class LobbiesManager:
    """
    Handles all lobbies and their clients connections.
    """
    def __init__(self, game_manager : GameManager):
        self.lobbies: Dict[str, Lobby] = {} # key is lobby ID, value is a Lobby object.
        self.game_manager = game_manager

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





    async def handle_client_message(self, websocket: WebSocket, lobby_id: str, data: str):
        """
        Handles incoming messages from a client and dispatches them to the correct handler.
        """
        try:
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "toggle_ready":
                new_ready_state = await self.switch_client_ready_state(websocket, lobby_id)
                await websocket.send_json({
                    "type": "ready_toggled",
                    "success": new_ready_state is not None,
                    "is_ready": new_ready_state
                })

            elif message_type == "start_adventure":
                # The game manager is now responsible for handling its own exceptions.
                await self.start_game(lobby_id)
                await self.start_new_round(lobby_id)

            elif message_type == "submit_choice":
                await self.submit_choice(lobby_id, websocket, message)

            else:
                # Handle unknown or default message types gracefully.
                response_message = f"Server received your message: '{data}'"
                await websocket.send_text(response_message)
                print(f"Sent response to client in '{lobby_id}': '{response_message}'")
        
        except json.JSONDecodeError:
            response_message = f"Server received non-JSON message: '{data}'"
            await websocket.send_text(response_message)
            print(f"Sent response to client in '{lobby_id}': {response_message}")
        except Exception as e:
            # This catch-all is for unexpected errors in message processing.
            print(f"An error occurred while processing message in lobby '{lobby_id}': {e}")

    async def start_game(self, lobby_id: int):
        """Start the game in a given lobby"""

        lobby = self.get_lobby(lobby_id)
        
        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready: raise Exception("All players must be ready")

        self.game_manager.start_game()

        for connection in lobby.connections:

            self.game_manager.game_state.chapters[connection.id] = []

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


    def _get_connection_by_socket(self, lobby_id: str, socket: WebSocket):
        """
        Helper method to find a specific connection in a lobby by its WebSocket.
        
        :raises ConnectionNotFoundException: If no matching connection is found.
        """
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            raise ValueError("Lobby does not exist.") # Or a more specific exception
        
        for connection in lobby.connections:
            if connection.socket == socket:
                return connection
        
        raise ConnectionNotFoundException(f"Connection not found for socket in lobby '{lobby_id}'.")

    async def switch_client_ready_state(self, socket: WebSocket, lobby_id: str):
        """Switches the ready state of a client."""
        try:
            connection = self._get_connection_by_socket(lobby_id, socket)
            connection.is_ready = not connection.is_ready
            print(f"Player '{connection.user.name}' in lobby '{lobby_id}' toggled ready state to: {connection.is_ready}")
            return connection.is_ready
        except (ConnectionNotFoundException, ValueError) as e:
            print(f"Error switching ready state: {e}")
            return None
    
    async def submit_choice(self, lobby_id: str, sender: WebSocket, choice : int):
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
        
        self.game_manager.submit_choice(sender_uuid, choice)
        
        all_choices_made = True
        for connection in lobby.connections:
            connection_uuid = uuid.UUID(connection.id)
            if (connection_uuid not in self.game_manager.game_state.chapters or 
                not self.game_manager.game_state.chapters[connection_uuid] or 
                self.game_manager.game_state.chapters[connection_uuid][-1].choice == -1):
                all_choices_made = False
                break

        if all_choices_made: await self.game_manager.start_new_round(lobby)

        print(f"Lobby '{lobby.id}' : {sender_name} submitted : {message}")
            
        return None

    async def start_new_round(self, lobby: Lobby):
        """Start a new round, and send a message to inform all players"""

        if not self.game_manager.game_state.adventure:
            print(f"[ERROR] No adventure set for lobby {lobby.id}")
            return
        
        self.game_manager.start_new_round()

        for connection in lobby.connections:

            message = {
                "type" : "new_round",
                "info" : {
                    "round_index" : self.game_manager.game_state.round,
                    "text" : self.game_manager.game_state.chapters[connection.id][-1].text,
                    "choices" : self.game_manager.game_state.chapters[connection.id][-1].possiblities,
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
                
            if not lobby.connections:
                del self.lobbies[lobby_id]
                print(f"Lobby '{lobby_id}' is now empty and has been removed.")

    async def broadcast(self, lobby: Lobby, message: str, sender: WebSocket = None):
        """Sends a message to all clients in a lobby, except the sender."""
        # Create a copy of connections to avoid modification during iteration
        connections = lobby.connections.copy()
        for connection in connections:
            if sender == connection.socket:
                continue
            try:
                await connection.socket.send_text(message)
            except WebSocketDisconnect:
                # Handle disconnect outside the broadcast loop
                self.disconnect(connection.socket, lobby.id)
            except Exception as e:
                print(f"Error broadcasting to {connection.user.name}: {e}")

    async def broadcast_lobby(self, lobby_id: str):
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            return
        
        message = {
            "type" : "lobby_info",
            "lobby" : lobby.to_dict()
        }

        # Create a copy of connections to avoid modification during iteration
        connections = lobby.connections.copy()
        for connection in connections:
            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                # Handle disconnect outside the broadcast loop
                self.disconnect(connection.socket, lobby_id)
            except Exception as e:
                print(f"Error broadcasting to {connection.user.name}: {e}")