from application.app.adventure.adventure_loader import AdventureLoader
from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter()

@router.get("/")
async def get_adventures():
    """
    Get all available adventures with their cover images.
    Returns a JSON array of adventures with image URLs.
    """
    try:
        # Load raw JSON data for image handling
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static/adventures.json")
        
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
        adventure = AdventureLoader().get_adventure_by_id(adventure_id)
        if not adventure:
            raise HTTPException(status_code=404, detail="Adventure not found")
        return adventure.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load adventure object: {str(e)}")
