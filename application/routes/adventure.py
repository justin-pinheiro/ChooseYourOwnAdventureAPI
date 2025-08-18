from fastapi import APIRouter
from application.app.lobby.lobby_manager import LobbyManager
import json

router = APIRouter()
manager = LobbyManager()

@router.post("/get")
async def get_adventures():
    """
    An HTTP endpoint that returns the existing adventures
    """
    with open("adventures.json", "r") as file: return json.load(file)