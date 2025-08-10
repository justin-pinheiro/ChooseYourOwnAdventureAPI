from http.client import HTTPException
import json
import traceback
from application.app.lobby.connection_manager import ConnectionManager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
manager = ConnectionManager()

@app.post("/lobby/create")
async def create_lobby_endpoint(min_players: int, max_players: int):
    """
    An HTTP endpoint to create a new lobby and return its ID.
    The client can specify min_players and max_players in the request body.
    """
    if not (1 <= min_players <= max_players):
        raise HTTPException(
            status_code=400,
            detail="Invalid player limits: min_players must be at least 1 and less than or equal to max_players"
        )
    lobby_id = manager.create_lobby(min_players, max_players)
    return {"lobby_id": lobby_id}

@app.websocket("/lobby/join/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str):
    """
    The main WebSocket endpoint. Clients connect to this route using a lobby ID.
    """
    try:
        lobby = await manager.connect(websocket, lobby_id)
        
        await websocket.send_text(f"Welcome to lobby '{lobby.lobby_id}'.")
        
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received message from client in '{lobby.lobby_id}': {data}")

                response_message = f"Server received your message: '{data}'"
                await websocket.send_text(response_message)
                print(f"Sent response to client in '{lobby.lobby_id}': {response_message}")
                
            except WebSocketDisconnect:
                raise
            except Exception as e:
                print(f"An error occurred in lobby '{lobby.lobby_id}': {e}")
                traceback.print_exc()
                break
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
    except WebSocketDisconnect:
        print(f"Client disconnected from lobby '{lobby_id}'.")
    finally:
        manager.disconnect(websocket, lobby_id)
