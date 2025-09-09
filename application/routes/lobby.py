from application.app.adventure.adventure_exceptions import AdventureNotFoundException
from application.app.lobby.lobby_exceptions import LobbyIsFullException, LobbyNotFound
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import traceback
from application.app.lobby.lobbies_manager import LobbiesManager
from application.app.game_manager import GameManager

router = APIRouter()
game_manager = GameManager()
lobby_manager = LobbiesManager(game_manager)

@router.post("/create")
async def create_lobby_endpoint(max_players: int, adventure_id : int):
    """
    An HTTP endpoint to create a new lobby and return its ID.
    """
    try: 
        lobby_id = lobby_manager.create_lobby(max_players, adventure_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AdventureNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {"lobby_id": lobby_id}

@router.get("/")
async def get_all_lobbies():
    """
    Get information about all existing lobbies.
    Returns a list of lobbies with their current status, players, and game state.
    """
    try:
        return lobby_manager.get_all_lobbies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lobbies: {str(e)}")

@router.get("/{lobby_id}")
async def get_lobby_info(lobby_id: str):
    """
    Get detailed information about a specific lobby.
    """
    try:
        lobby = lobby_manager.get_lobby(lobby_id)
        return lobby.to_dict()
    except LobbyNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.websocket("/join/{lobby_id}")
async def join_lobby(websocket: WebSocket, lobby_id: str):
    """
    The main WebSocket endpoint for clients to connect to a specific lobby.
    """
    try:
        await lobby_manager.connect(websocket, lobby_id)
        await websocket.accept()
        await lobby_manager.broadcast_lobby_info(lobby_id)
        while True:
            data = await websocket.receive_text()
            await lobby_manager.handle_client_message(websocket, lobby_id, data)

    except (LobbyNotFound, LobbyIsFullException) as e:
        print(f"Connection attempt failed: {e}")
        await websocket.close(code=1008, reason=str(e))

    except WebSocketDisconnect:
        print(f"Client disconnected from lobby '{lobby_id}'.")
    
    except Exception as e:
        print(f"An unexpected error occurred in lobby '{lobby_id}': {e}")
        traceback.print_exc()
        if websocket.client_state == 'CONNECTED':
            await websocket.close(code=1011)

    finally:
        print(f"Cleaning up connection for lobby '{lobby_id}'.")
        lobby_manager.disconnect(websocket, lobby_id)