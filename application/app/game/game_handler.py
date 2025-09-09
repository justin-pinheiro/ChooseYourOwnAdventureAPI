import json
from typing import Dict
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from domain.lobby import Lobby

class GameHandler:
    """
    Handles all game-related logic and message processing.
    This class is responsible for managing the game state, processing player actions,
    and coordinating game progression.
    """
    async def handle_client_message(self, websocket: WebSocket, lobby: Lobby, data: str):
        """
        Handles incoming messages from a client and dispatches them to the correct handler.
        """
        try:
            message = json.loads(data)
            message_type = message.get("type")

            if message_type == "toggle_ready":
                new_ready_state = await self.switch_client_ready_state(websocket, lobby)
                await websocket.send_json({
                    "type": "ready_toggled",
                    "success": new_ready_state is not None,
                    "is_ready": new_ready_state
                })

            elif message_type == "start_adventure":
                await self.start_game(lobby)
                await self.start_new_round(lobby)

            elif message_type == "submit_choice":
                await self.submit_choice(lobby, websocket, message)

            else:
                # Handle unknown or default message types gracefully.
                response_message = f"Server received your message: '{data}'"
                await websocket.send_text(response_message)
                print(f"Sent response to client in '{lobby.id}': '{response_message}'")
        
        except json.JSONDecodeError:
            response_message = f"Server received non-JSON message: '{data}'"
            await websocket.send_text(response_message)
            print(f"Sent response to client in '{lobby.id}': {response_message}")
        except Exception as e:
            # This catch-all is for unexpected errors in message processing.
            print(f"An error occurred while processing message in lobby '{lobby.id}': {e}")

    async def start_game(self, lobby: Lobby):
        """Start the game in a given lobby"""
        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready:
            raise Exception("All players must be ready")

        lobby.game_state.started = True

        for connection in lobby.connections:
            self.game_manager.game_state.chapters[connection.id] = []
            message = {
                "type": "start_adventure",
                "info": {
                    "success": True,
                }
            }
            try:
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                raise

    async def submit_choice(self, lobby: Lobby, sender: WebSocket, choice: int):
        """Handle player choice submission"""
        sender_connection = self._get_connection_by_socket(lobby, sender)
        if not sender_connection:
            return

        sender_uuid = uuid.UUID(sender_connection.id)
        
        if sender_uuid in self.game_state.chapters and self.game_state.chapters[sender_uuid]:
            latest_chapter = self.game_state.chapters[sender_uuid][-1]
            latest_chapter.choice = choice["choice_index"]

        if self._are_all_choices_made(lobby):
            await self.start_new_round(lobby)

        print(f"Lobby '{lobby.id}': {sender_connection.user.name} submitted choice: {choice}")

    async def start_new_round(self, lobby: Lobby):
        """Start a new round, and send a message to inform all players"""
        if not self.game_manager.game_state.adventure:
            print(f"[ERROR] No adventure set for lobby {lobby.id}")
            return

        self.game_state.round += 1

        for player_id, chapters in self.game_state.chapters.items():

            new_chapter = await self.story_manager.generate_chapter(
                player_name="Jean",
                previous_chapters=None,
                last_choice=None
            )
            
            chapters.append(new_chapter)

        for connection in lobby.connections:
            message = {
                "type": "new_round",
                "info": {
                    "round_index": self.game_manager.game_state.round,
                    "text": self.game_manager.game_state.chapters[connection.id][-1].text,
                    "choices": self.game_manager.game_state.chapters[connection.id][-1].possiblities,
                }
            }
            try:
                await connection.socket.send_json(message)
            except Exception as e:
                print(f"[ERROR] Error sending message to {connection.user.name}: {e}")

    def _are_all_choices_made(self, lobby: Lobby) -> bool:
        """Check if all players in the lobby have made their choices."""
        for connection in lobby.connections:
            connection_uuid = uuid.UUID(connection.id)
            if (connection_uuid not in self.game_manager.game_state.chapters or
                not self.game_manager.game_state.chapters[connection_uuid] or
                self.game_manager.game_state.chapters[connection_uuid][-1].choice == -1):
                return False
        return True
