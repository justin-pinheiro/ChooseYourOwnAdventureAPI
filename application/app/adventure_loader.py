import json
import os
from typing import List
from domain.adventure import Adventure
from domain.map import Map, Area

class AdventureLoader():

    @staticmethod
    def load_adventures_from_json(file_path: str) -> List[Adventure]:
        """
        Load adventures from a JSON file and convert them to Adventure objects.
        
        Args:
            file_path: Path to the adventures JSON file (relative to backend folder)
            
        Returns:
            List of Adventure objects
            
        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            json.JSONDecodeError: If the JSON file is malformed
            KeyError: If required fields are missing from the JSON
        """
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.join(base_dir, file_path)
        
        print(f"[DEBUG] Loading adventures from: {full_path}")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Adventures file not found: {full_path}")
        
        # Read and parse JSON
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                adventures_data = json.load(file)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in adventures file: {e}")
        
        adventures = []
        
        for adventure_data in adventures_data:
            try:
                # Extract basic adventure info
                adventure_id = adventure_data["id"]
                title = adventure_data["title"]
                description = adventure_data["description"]
                min_players = adventure_data["min_players"]
                max_players = adventure_data["max_players"]
                
                print(f"[DEBUG] Processing adventure: {title} (ID: {adventure_id})")
                
                # Process the map data
                map_data = adventure_data["map"]
                areas_data = map_data["areas"]
                
                # Create Area objects and build area name to ID mapping
                areas = []
                area_name_to_id = {}
                
                for i, (area_key, area_info) in enumerate(areas_data.items()):
                    area = Area(
                        id=i,
                        name=area_info["name"],
                        description=area_info["description"]
                    )
                    areas.append(area)
                    area_name_to_id[area_key] = i
                    
                    print(f"[DEBUG] Created area {i}: {area_info['name']}")
                
                # Create Map object with areas
                adventure_map = Map(
                    id=adventure_id,  # Use adventure ID as map ID
                    areas=areas
                )
                
                # Add connections between areas
                for area_key, area_info in areas_data.items():
                    area_id = area_name_to_id[area_key]
                    
                    for connected_area_key in area_info["connections"]:
                        if connected_area_key in area_name_to_id:
                            connected_area_id = area_name_to_id[connected_area_key]
                            adventure_map.add_connection(area_id, connected_area_id)
                            
                            print(f"[DEBUG] Connected {area_key} (ID: {area_id}) to {connected_area_key} (ID: {connected_area_id})")
                
                # Create Adventure object
                adventure = Adventure(
                    id=adventure_id,
                    title=title,
                    description=description,
                    minPlayers=min_players,
                    maxPlayers=max_players,
                    map=adventure_map
                )
                
                adventures.append(adventure)
                print(f"[DEBUG] Successfully created adventure: {title}")
                
            except KeyError as e:
                print(f"[ERROR] Missing required field in adventure data: {e}")
                continue
            except Exception as e:
                print(f"[ERROR] Error processing adventure {adventure_data.get('title', 'Unknown')}: {e}")
                continue
        
        print(f"[DEBUG] Successfully loaded {len(adventures)} adventures")
        return adventures

    @staticmethod
    def get_adventure_by_id(adventure_id: int, adventures: List[Adventure] = None) -> Adventure:
        """
        Get a specific adventure by its ID.
        
        Args:
            adventure_id: The ID of the adventure to retrieve
            adventures: Optional list of adventures. If None, will load from file.
            
        Returns:
            Adventure object if found, None otherwise
        """
        if adventures is None:
            adventures = AdventureLoader.load_adventures_from_json("static/adventures.json")
        
        for adventure in adventures:
            if adventure.id == adventure_id:
                return adventure
        
        return None

    @staticmethod
    def get_adventures_by_player_count(min_players: int, max_players: int, adventures: List[Adventure] = None) -> List[Adventure]:
        """
        Get adventures that support a specific player count range.
        
        Args:
            min_players: Minimum number of players
            max_players: Maximum number of players
            adventures: Optional list of adventures. If None, will load from file.
            
        Returns:
            List of compatible Adventure objects
        """
        if adventures is None:
            adventures = AdventureLoader.load_adventures_from_json("static/adventures.json")
        
        compatible_adventures = []
        
        for adventure in adventures:
            # Check if the requested player count overlaps with adventure's supported range
            if (min_players <= adventure.maxPlayers and max_players >= adventure.minPlayers):
                compatible_adventures.append(adventure)
        
        return compatible_adventures
