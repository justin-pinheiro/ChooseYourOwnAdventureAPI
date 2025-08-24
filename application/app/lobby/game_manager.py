from typing import Dict
import uuid
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect

from domain.lobby import Lobby
from domain.chapter import Chapter
from utils.llm_client import OpenRouterClient
from .story_manager import StoryManager


class GameManager:
    """
    Manages in-game operations: story generation, choice handling, and game progression.
    """
    def __init__(self, lobby_manager):
        self.lobby_manager = lobby_manager
        self.llm_client = OpenRouterClient()
        self.story_manager = StoryManager()

    async def start_lobby(self, lobby_id: str):
        """Start a given lobby"""
        lobby = self.lobby_manager.get_lobby(lobby_id)
        if not lobby:
            raise Exception(f"Lobby {lobby_id} not found")

        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready: 
            raise Exception("All players must be ready")

        lobby.game_state.started = True

        for connection in list[Connection](lobby.connections):
            message = {
                "type" : "start_adventure",
                "info" : {
                    "success": True,
                }
            }            

            try:
                print("Sending:", message)
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.lobby_manager.disconnect(connection.socket, lobby.id)

    async def submit_choice(self, lobby_id: str, sender: WebSocket, message):
        """Handle player choice submission"""
        lobby = self.lobby_manager.get_lobby(lobby_id)
        if not lobby:
            return

        sender_name = "Unknown"
        sender_connection = None
        for connection in lobby.connections:
            if connection.socket == sender:
                sender_name = connection.user.name
                sender_connection = connection
                break
        
        print(f"Lobby '{lobby_id}' : {sender_name} submitted : {message}")

        if not sender_connection:
            return
        
        # Convert connection ID to UUID and update the choice
        sender_uuid = uuid.UUID(sender_connection.id)
        if sender_uuid in lobby.game_state.chapters and lobby.game_state.chapters[sender_uuid]:
            latest_chapter = lobby.game_state.chapters[sender_uuid][-1]
            latest_chapter.choice = message["choice_index"]

        # Check if all players have made their choice
        all_choices_made = True
        for connection in lobby.connections:
            connection_uuid = uuid.UUID(connection.id)
            if (connection_uuid not in lobby.game_state.chapters or 
                not lobby.game_state.chapters[connection_uuid] or 
                lobby.game_state.chapters[connection_uuid][-1].choice == -1):
                all_choices_made = False
                break

        if all_choices_made:
            await self.start_new_round(lobby_id)
        else:
            remaining_players = sum(1 for connection in lobby.connections 
                                  if (uuid.UUID(connection.id) not in lobby.game_state.chapters or 
                                      not lobby.game_state.chapters[uuid.UUID(connection.id)] or
                                      lobby.game_state.chapters[uuid.UUID(connection.id)][-1].choice == -1))
            print(f"Waiting for {remaining_players} more players to make their choice")

    async def start_new_round(self, lobby_id: str):
        """Start a new round, and send a message to inform all players"""
        
        print(f"[DEBUG] start_new_round called with lobby_id: {lobby_id}")
        
        lobby = self.lobby_manager.get_lobby(lobby_id)
        if not lobby:
            print(f"[DEBUG] ERROR: Lobby {lobby_id} not found")
            return

        if not lobby.game_state.adventure:
            print(f"[DEBUG] No adventure set for lobby {lobby_id}")
            return

        print(f"[DEBUG] Found lobby {lobby_id} with {len(lobby.connections)} connections")
        print(f"[DEBUG] Starting round {lobby.game_state.round}!")

        # Collect last chapters and choices for planning
        story_state = []
        print(f"[DEBUG] Building story state for {len(lobby.connections)} connections")
        
        for i, connection in enumerate(lobby.connections):
            print(f"[DEBUG] Processing connection {i}: {connection.user.name}, ID: {connection.id}")
            
            # Convert connection.id (str) to UUID for chapters lookup
            try:
                connection_uuid = uuid.UUID(connection.id)
                print(f"[DEBUG] Converted connection ID to UUID: {connection_uuid}")
                user_chapters = lobby.game_state.chapters.get(connection_uuid, [])
                print(f"[DEBUG] User {connection.user.name} has {len(user_chapters)} chapters")
            except (ValueError, TypeError) as e:
                # If conversion fails, create new entry
                print(f"[DEBUG] UUID conversion failed for {connection.id}: {e}")
                user_chapters = []
                connection_uuid = uuid.UUID(connection.id)
                lobby.game_state.chapters[connection_uuid] = user_chapters
                print(f"[DEBUG] Created new chapters entry for {connection_uuid}")
            
            if user_chapters:
                last_chapter = user_chapters[-1]
                print(f"[DEBUG] Last chapter for {connection.user.name}: choice={last_chapter.choice}")
                
                story_state.append({
                    "player_name": getattr(connection, 'character', connection.user.name),
                    "last_chapter": last_chapter.text,
                    "available_choices": last_chapter.possiblities,
                    "chosen_index": last_chapter.choice,
                    "chosen_action": last_chapter.possiblities[last_chapter.choice] if last_chapter.choice != -1 and last_chapter.choice < len(last_chapter.possiblities) else "No choice made"
                })
            else:
                print(f"[DEBUG] No chapters for {connection.user.name}, using default story state")
                story_state.append({
                    "player_name": getattr(connection, 'character', connection.user.name),
                    "last_chapter": "Beginning of adventure",
                    "available_choices": [],
                    "chosen_index": -1,
                    "chosen_action": "Starting the adventure"
                })

        print(f"[DEBUG] Story state built: \\n{story_state}")

        # Use StoryManager to generate story directions
        print(f"[DEBUG] Using StoryManager to generate directions")
        
        try:
            directions = await self.story_manager.generate_story_directions(
                story_state=story_state,
                adventure=lobby.game_state.adventure,
                current_round=lobby.game_state.round
            )
            print(f"[DEBUG] Successfully generated {len(directions)} story directions")
        except Exception as e:
            # Fallback directions if story generation fails
            print(f"[DEBUG] StoryManager error: {e}")
            directions = [{"player_name": conn.user.name, "next_direction": "Continue your adventure with new challenges ahead."} for conn in lobby.connections]
            print(f"[DEBUG] Using fallback directions: {len(directions)} directions")

        print(f"[DEBUG] Final directions: {directions}")

        # Generate individual stories for each player based on planning directions
        print(f"[DEBUG] Starting individual story generation for {len(lobby.connections)} players")
        
        for i, connection in enumerate(lobby.connections):
            print(f"[DEBUG] Generating story for player {i}: {connection.user.name}")
            
            player_direction = None
            for direction in directions:
                if direction.get("player_name") == connection.user.name:
                    player_direction = direction.get("next_direction", "Continue your adventure.")
                    print(f"[DEBUG] Found direction for {connection.user.name}: {player_direction}")
                    break
            
            if player_direction is None:
                player_direction = "Continue your adventure with new challenges ahead."
                print(f"[DEBUG] No specific direction found, using default for {connection.user.name}")
            
            connection_uuid = uuid.UUID(connection.id)
            print(f"[DEBUG] Using UUID {connection_uuid} for chapter storage")
            
            # Get previous chapters and last choice for context
            previous_chapters = lobby.game_state.chapters.get(connection_uuid, [])
            last_choice = None
            if previous_chapters:
                last_chapter = previous_chapters[-1]
                if last_chapter.choice != -1 and last_chapter.choice < len(last_chapter.possiblities):
                    last_choice = last_chapter.possiblities[last_chapter.choice]
            
            print(f"[DEBUG] Using StoryManager to generate chapter for {connection.user.name}")
            # Use StoryManager to generate chapter
            chapter = await self.story_manager.generate_chapter(
                player_name=connection.user.name,
                story_direction=player_direction,
                adventure=lobby.game_state.adventure,
                previous_chapters=previous_chapters,
                last_choice=last_choice
            )
            
            print(f"[DEBUG] Generated chapter for {connection.user.name}: {len(chapter.text)} chars, {len(chapter.possiblities)} choices")
            
            # Ensure the chapters list exists for this connection
            if connection_uuid not in lobby.game_state.chapters:
                lobby.game_state.chapters[connection_uuid] = []
                print(f"[DEBUG] Created new chapters list for {connection_uuid}")
            
            lobby.game_state.chapters[connection_uuid].append(chapter)
            lobby.game_state.round += 1
            print(f"[DEBUG] Added chapter to {connection.user.name}, round is now {lobby.game_state.round}")

            message = {
                "type" : "new_round",
                "info" : {
                    "round_index" : lobby.game_state.round,
                    "text" : lobby.game_state.chapters[connection_uuid][-1].text,
                    "choices" : lobby.game_state.chapters[connection_uuid][-1].possiblities,
                }
            }
            
            print(f"[DEBUG] Prepared message for {connection.user.name}: {message}")
            
            try:
                print(f"[DEBUG] Sending message to {connection.user.name} via WebSocket...")
                await connection.socket.send_json(message)
                print(f"[DEBUG] Successfully sent message to {connection.user.name}")
            except WebSocketDisconnect as e:
                print(f"[DEBUG] WebSocket disconnect for {connection.user.name}: {e}")
                self.lobby_manager.disconnect(connection.socket, lobby_id)
            except Exception as e:
                print(f"[DEBUG] Error sending message to {connection.user.name}: {e}")

        print(f"[DEBUG] start_new_round completed for lobby {lobby_id}")
