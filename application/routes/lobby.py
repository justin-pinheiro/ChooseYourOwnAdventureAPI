from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import traceback
from application.app.lobby.lobby_manager import LobbyManager

router = APIRouter()
manager = LobbyManager()

@router.post("/create")
async def create_lobby_endpoint(max_players: int):
    """
    An HTTP endpoint to create a new lobby and return its ID.
    The client can specify max_players in the request body.
    """
    lobby_id = manager.create_lobby(max_players)
    return {"lobby_id": lobby_id}

@router.websocket("/join/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str):
    """
    The main WebSocket endpoint. Clients connect to this route using a lobby ID.
    """
    try:
        lobby = await manager.connect(websocket, lobby_id)
        
        await websocket.send_text(f"Welcome to lobby '{lobby.id}'.")
        
        await manager.broadcast_lobby(lobby_id)
        
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received message from client in '{lobby.id}': {data}")

                response_message = f"Server received your message: '{data}'"
                await websocket.send_text(response_message)
                print(f"Sent response to client in '{lobby.id}': {response_message}")
                
            except WebSocketDisconnect:
                raise
            except Exception as e:
                print(f"An error occurred in lobby '{lobby.id}': {e}")
                traceback.print_exc()
                break
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
    except WebSocketDisconnect:
        print(f"Client disconnected from lobby '{lobby_id}'.")
    finally:
        manager.disconnect(websocket, lobby_id)