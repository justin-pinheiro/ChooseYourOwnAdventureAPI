from http.client import HTTPException
from typing import Dict
import uuid
from domain.connection import Connection
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from domain.lobby import Lobby
from domain.user import User
from domain.chapter import Chapter
from domain.adventure import Adventure
from domain.map import Map, Area

from utils.llm_client import OpenRouterClient

class LobbyManager:
    """
    Manages all active WebSocket connections, organized by Lobby objects.
    """
    def __init__(self):
        # The key is the lobby ID, and the value is a Lobby object.
        self.lobbies: Dict[str, Lobby] = {}
        self.llm_client = OpenRouterClient()

    def create_lobby(self, max_players: int) -> str:
        """Generates a unique ID and creates a new lobby."""
        
        if max_players < 1:
            raise HTTPException(status_code=400, detail="Invalid player limits: max_players must be at least 1")
        
        lobby_id = str(uuid.uuid4())[:8]
        self.lobbies[lobby_id] = Lobby(lobby_id, max_players)
        
        # ==================================
        # TODO : To remove later. For now, creating default adventure
        # ==================================
        
        entrance_hall = Area(0, "Entrance Hall", "A grand foyer with a dusty chandelier hanging ominously overhead. Moonlight filters through cracked windows, casting eerie shadows on the marble floor.")
        living_room = Area(1, "Living Room", "Furniture covered in white sheets creates ghostly silhouettes. A cold fireplace holds only ashes, and family portraits seem to watch your every move.")
        kitchen = Area(2, "Kitchen", "Rusted pots and pans hang from hooks, and the old stove creaks in the silence. A foul smell emanates from the pantry.")
        dining_room = Area(3, "Dining Room", "A long table set for dinner, though the food has long since rotted away. Candles flicker mysteriously despite no visible flame source.")
        library = Area(4, "Library", "Towering bookshelves filled with ancient tomes. Some books seem to whisper when you pass by, and ladder wheels creak on their own.")
        master_bedroom = Area(5, "Master Bedroom", "A four-poster bed with tattered curtains. The mirror on the vanity shows reflections that don't quite match reality.")
        attic = Area(6, "Attic", "Cobwebs hang like curtains from the rafters. Old trunks and furniture create a maze of shadows and hiding places.")
        basement = Area(7, "Basement", "Stone walls weep with moisture. Chains hang from the ceiling, and strange symbols are carved into the floor.")
        
        haunted_map = Map(0, [entrance_hall, living_room, kitchen, dining_room, library, master_bedroom, attic, basement])
        
        haunted_map.add_connection(0, 1)  # Entrance Hall <-> Living Room
        haunted_map.add_connection(0, 3)  # Entrance Hall <-> Dining Room
        haunted_map.add_connection(0, 7)  # Entrance Hall <-> Basement (secret passage)
        haunted_map.add_connection(1, 2)  # Living Room <-> Kitchen
        haunted_map.add_connection(1, 4)  # Living Room <-> Library
        haunted_map.add_connection(2, 3)  # Kitchen <-> Dining Room
        haunted_map.add_connection(3, 4)  # Dining Room <-> Library
        haunted_map.add_connection(4, 5)  # Library <-> Master Bedroom
        haunted_map.add_connection(5, 6)  # Master Bedroom <-> Attic
        haunted_map.add_connection(7, 2)  # Basement <-> Kitchen (cellar access)
        
        self.lobbies[lobby_id].game_state.adventure = Adventure(
            0,
            "The haunted house",
            "Whispers of an abandoned mansion on the edge of town have circulated for generations. Locals say its windows glow at night, and strange figures roam the halls when the moon is high. When a mysterious letter invites you to spend a single night inside, you and your companions must uncover the secrets buried within its crumbling walls. Shadows move on their own, the air hums with restless spirits, and every door could lead to salvation… or doom. Will you survive the horrors lurking in the dark—or become part of the house's curse forever?",
            1,
            5,
            haunted_map
        )
        
        # ==================================
        
        print(f"Lobby '{lobby_id}' created with max:{max_players} players.")
        return lobby_id
    
    def get_lobby(self, lobby_id: str) -> Lobby:
        """Get a lobby by its ID."""
        return self.lobbies.get(lobby_id)
    
    async def start_lobby(self, lobby_id: int):
        """Start a given lobby"""

        lobby = self.lobbies[lobby_id]

        # if(not self.adventure): raise Exception("No adventure selected")

        all_players_ready = all(connection.is_ready for connection in lobby.connections)
        if not all_players_ready: raise Exception("All players must be ready")

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

    async def submit_choice(self, lobby_id: str, sender : WebSocket, message):
        
        sender_name = "Unknown"
        sender_connection = None
        for connection in self.lobbies[lobby_id].connections:
            if connection.socket == sender:
                sender_name = connection.user.name
                sender_connection = connection
                break
        
        print(f"Lobby '{lobby_id}' : {sender_name} submitted : {message}")

        lobby = self.lobbies.get(lobby_id)
        if not lobby or not sender_connection:
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
        

    async def start_new_round(self, lobby_id: int):
        """Start a new round, and send a message to inform all players"""
        
        print(f"[DEBUG] start_new_round called with lobby_id: {lobby_id}")
        
        lobby = self.lobbies.get(lobby_id)
        if not lobby:
            print(f"[DEBUG] ERROR: Lobby {lobby_id} not found in lobbies: {list(self.lobbies.keys())}")
            return

        if not lobby.game_state.adventure : 
            
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
                    "player_name": connection.character,
                    "last_chapter": last_chapter.text,
                    "available_choices": last_chapter.possiblities,
                    "chosen_index": last_chapter.choice,
                    "chosen_action": last_chapter.possiblities[last_chapter.choice] if last_chapter.choice != -1 and last_chapter.choice < len(last_chapter.possiblities) else "No choice made"
                })
            else:
                print(f"[DEBUG] No chapters for {connection.user.name}, using default story state")
                story_state.append({
                    "player_name": connection.character,
                    "last_chapter": "Beginning of adventure",
                    "available_choices": [],
                    "chosen_index": -1,
                    "chosen_action": "Starting the adventure"
                })

        print(f"[DEBUG] Story state built: \n{story_state}")

        # Create a plan using LLM
        
        client = OpenRouterClient()
        print(f"[DEBUG] Created OpenRouter client")
        
        planning_prompt = f"""
            Based on the current story state, create a plan for what direction each player's story should go next.
            Current round: {lobby.game_state.round}
            
            Players and their last actions:
            {story_state}
            
            Adventure : {lobby.game_state.adventure.title}
            {lobby.game_state.adventure.description}
            
            Map :
            {lobby.game_state.adventure.map.to_dict()}

            For each player, provide a brief direction (1-2 sentences) for what should happen next in their story.
            Return only a JSON array with objects containing 'player_name' and 'next_direction' fields.
            Make the directions engaging and build on their previous choices.
        """
        
        print(f"[DEBUG] Sending planning prompt to LLM...")
        response = await client.chat_completion([
            {"role": "system", "content": "You are a creative adventure game master. Create engaging story directions based on player choices."},
            {"role": "user", "content": planning_prompt}
        ])
        
        print(f"[DEBUG] LLM Planning Response received: {response.content}")
        
        # Parse the response to get directions (fallback if parsing fails)
        try:
            directions = client.parse_json_response(
                response.content, 
                fallback_value=[{"player_name": conn.user.name, "next_direction": "Continue your adventure with new challenges ahead."} for conn in lobby.connections]
            )
            print(f"[DEBUG] Successfully parsed LLM directions: {len(directions)} directions")
        except Exception as e:
            # Fallback directions if LLM response can't be parsed
            print(f"[DEBUG] Could not parse the directions: {e}")
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
            
            # Generate story context based on direction and player's history
            if connection_uuid in lobby.game_state.chapters and lobby.game_state.chapters[connection_uuid]:
                last_chapter = lobby.game_state.chapters[connection_uuid][-1]
                story_context = f"""
                    Adventure: {lobby.game_state.adventure.title}
                    {lobby.game_state.adventure.description}
                    
                    Story Direction: {player_direction}
                    
                    Previous Chapter:
                    {last_chapter.text}
                    
                    Player's Last Choice: {last_chapter.possiblities[last_chapter.choice] if last_chapter.choice != -1 and last_chapter.choice < len(last_chapter.possiblities) else "No choice made yet"}
                    
                    Current area : Entrance Hall
                    
                    Connected Areas:
                    {chr(10).join([f"- {lobby.game_state.adventure.map.areas[conn_id].name}" for conn_id in lobby.game_state.adventure.map.get_connected_areas(0)])}
                """
                print(f"[DEBUG] Using previous chapter context for {connection.user.name}")
            else:
                story_context = f"""
                    Adventure: {lobby.game_state.adventure.title}
                    {lobby.game_state.adventure.description}
                    
                    Story Direction: {player_direction}
                    
                    This is the beginning of the adventure. The player is starting their journey.
                    
                    Current area : Entrance Hall
                    
                    Connected Areas:
                    {chr(10).join([f"- {lobby.game_state.adventure.map.areas[conn_id].name}" for conn_id in lobby.game_state.adventure.map.get_connected_areas(0)])}
                """
                print(f"[DEBUG] Using first chapter context for {connection.user.name}")
            
            print(f"[DEBUG] Calling LLM to generate chapter for {connection.user.name}")
            
            # Generate complete chapter (text + choices) in single LLM call
            chapter = await self.llm_client.generate_chapter(
                prompt=f"""Generate the next chapter for this {lobby.game_state.adventure.title} adventure. 
                
                Create an immersive, atmospheric scene that fits the haunted mansion setting. The chapter should:
                - Be 2-4 sentences long and set a spooky, engaging mood
                - Reference specific areas from the mansion map when appropriate
                - Build tension and mystery
                - Lead naturally to meaningful player choices
                - Follow the story direction provided in the context
                
                Remember this is a horror/mystery adventure in an abandoned haunted mansion.""",
                context=story_context,
                num_choices=3
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
                self.disconnect(connection.socket, lobby_id)
            except Exception as e:
                print(f"[DEBUG] Error sending message to {connection.user.name}: {e}")

        print(f"[DEBUG] start_new_round completed for lobby {lobby_id}")

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
            try:
                print(f"Broadcast : {message}")
                await connection.socket.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection.socket, lobby_id)