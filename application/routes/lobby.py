from application.app.adventure.adventure_exceptions import AdventureNotFoundException
from application.app.lobby.lobby_exceptions import LobbyIsFullException, LobbyNotFound
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import traceback
import logging
from application.app.lobby.lobbies_manager import LobbiesManager

router = APIRouter()
logger = logging.getLogger(__name__)
lobby_manager = LobbiesManager()

@router.post("/create")
async def create_lobby_endpoint(max_players: int, adventure_id : int):
    """
    An HTTP endpoint to create a new lobby and return its ID.
    """
    logger.info(f"Attempting to create lobby with max_players={max_players}, adventure_id={adventure_id}")
    try: 
        lobby_id = lobby_manager.create_lobby(max_players, adventure_id)
        logger.info(f"Successfully created lobby {lobby_id}")
    except ValueError as e:
        logger.warning(f"Invalid lobby creation parameters: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except AdventureNotFoundException as e:
        logger.warning(f"Adventure not found during lobby creation: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
    return {"lobby_id": lobby_id}

@router.get("/")
async def get_all_lobbies():
    """
    Get information about all existing lobbies.
    Returns a list of lobbies with their current status, players, and game state.
    """
    try:
        logger.debug("Retrieving all lobbies")
        result = lobby_manager.get_all_lobbies()
        logger.debug(f"Found {result['total_lobbies']} lobbies")
        return result
    except Exception as e:
        logger.error(f"Failed to retrieve lobbies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lobbies: {str(e)}")

@router.get("/{lobby_id}")
async def get_lobby_info(lobby_id: str):
    """
    Get detailed information about a specific lobby.
    """
    logger.debug(f"Retrieving information for lobby {lobby_id}")
    try:
        lobby = lobby_manager.get_lobby(lobby_id)
        logger.debug(f"Found lobby {lobby_id} with {len(lobby.connections)} players")
        return lobby.to_dict()
    except LobbyNotFound as e:
        logger.warning(f"Lobby not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
@router.websocket("/join/{lobby_id}")
async def join_lobby(websocket: WebSocket, lobby_id: str):
    """
    The main WebSocket endpoint for clients to connect to a specific lobby.
    """
    logger.info(f"New WebSocket connection attempt to lobby {lobby_id}")
    try:
        await lobby_manager.connect(websocket, lobby_id)
        await websocket.accept()
        logger.info(f"Client successfully connected to lobby {lobby_id}")
        await lobby_manager.broadcast_lobby_info(lobby_id)
        while True:
            data = await websocket.receive_text()
            message_type, message_content = lobby_manager._parse_client_message(data)
            await lobby_manager.handle_client_message(websocket, lobby_id, message_type, message_content)

    except (LobbyNotFound, LobbyIsFullException) as e:
        logger.warning(f"Connection attempt failed: {e}")
        await websocket.close(code=1008, reason=str(e))

    except WebSocketDisconnect:
        await lobby_manager.disconnect(websocket, lobby_id)
        logger.info(f"Client disconnected from lobby '{lobby_id}'.")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred in lobby '{lobby_id}': {e}")
        logger.error(traceback.format_exc())
        if websocket.client_state == 'CONNECTED':
            await websocket.close(code=1011)

    finally:
        logger.debug(f"Cleaning up connection for lobby '{lobby_id}'.")
        try:
            await lobby_manager.disconnect(websocket, lobby_id)
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")