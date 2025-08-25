from fastapi import APIRouter, HTTPException
from application.app.lobby.lobby_manager import LobbyManager
from utils.adventure_loader import load_adventures_from_json, get_adventure_by_id
import json
import os

router = APIRouter()
manager = LobbyManager()

@router.get("/")
async def get_adventures():
    """
    Get all available adventures with their cover images.
    Returns a JSON array of adventures with image URLs.
    """
    try:
        # Load raw JSON data for image handling
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "adventures.json")
        
        with open(json_path, 'r', encoding='utf-8') as file:
            adventures = json.load(file)
        
        # Add full image URLs to each adventure
        for adventure in adventures:
            if adventure.get("image"):
                # Convert relative path to full URL
                adventure["image_url"] = f"/static/images/adventures/{adventure['image']}"
            else:
                adventure["image_url"] = None
        
        return {"adventures": adventures}
        
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Adventures file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format in adventures file")

@router.get("/objects")
async def get_adventures_as_objects():
    """
    Get all adventures as fully parsed Adventure objects (useful for game logic).
    """
    try:
        adventures = load_adventures_from_json()
        return {"adventures": [adventure.to_dict() for adventure in adventures]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load adventure objects: {str(e)}")

@router.post("/get")
async def get_adventures_legacy():
    """
    Legacy endpoint - An HTTP endpoint that returns the existing adventures
    """
    try:
        with open("adventures.json", "r") as file: 
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Adventures file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format in adventures file")

@router.get("/{adventure_id}")
async def get_adventure_by_id_endpoint(adventure_id: int):
    """
    Get a specific adventure by its ID with image URL.
    """
    try:
        # Load raw JSON data for image handling
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "adventures.json")
        
        with open(json_path, 'r', encoding='utf-8') as file:
            adventures = json.load(file)
        
        # Find the specific adventure
        adventure = next((adv for adv in adventures if adv["id"] == adventure_id), None)
        
        if not adventure:
            raise HTTPException(status_code=404, detail="Adventure not found")
        
        # Add image URL
        if adventure.get("image"):
            adventure["image_url"] = f"/static/images/adventures/{adventure['image']}"
        else:
            adventure["image_url"] = None
        
        return adventure
        
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Adventures file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON format in adventures file")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load adventure: {str(e)}")

@router.get("/{adventure_id}/object")
async def get_adventure_object_by_id(adventure_id: int):
    """
    Get a specific adventure as a fully parsed Adventure object (useful for game logic).
    """
    try:
        adventure = get_adventure_by_id(adventure_id)
        if not adventure:
            raise HTTPException(status_code=404, detail="Adventure not found")
        return adventure.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load adventure object: {str(e)}")

@router.get("/players/{min_players}/{max_players}")
async def get_adventures_by_player_count(min_players: int, max_players: int):
    """
    Get adventures that support a specific player count range.
    """
    try:
        from utils.adventure_loader import get_adventures_by_player_count
        adventures = get_adventures_by_player_count(min_players, max_players)
        
        # Convert to dict and add image URLs
        result_adventures = []
        
        # Load raw JSON for image URLs
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "adventures.json")
        with open(json_path, 'r', encoding='utf-8') as file:
            raw_adventures = json.load(file)
        
        for adventure in adventures:
            adventure_dict = adventure.to_dict()
            
            # Find corresponding raw data for image
            raw_adventure = next((adv for adv in raw_adventures if adv["id"] == adventure.id), None)
            if raw_adventure and raw_adventure.get("image"):
                adventure_dict["image_url"] = f"/static/images/adventures/{raw_adventure['image']}"
            else:
                adventure_dict["image_url"] = None
                
            result_adventures.append(adventure_dict)
        
        return {"adventures": result_adventures}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to filter adventures: {str(e)}")