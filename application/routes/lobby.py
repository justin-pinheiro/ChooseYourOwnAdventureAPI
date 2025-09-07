from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import traceback
from application.app.lobby_manager import LobbyManager
from application.app.game_manager import GameManager

router = APIRouter()
lobby_manager = LobbyManager()
game_manager = GameManager(lobby_manager)

@router.post("/create")
async def create_lobby_endpoint(max_players: int, adventure_id : int):
    """
    An HTTP endpoint to create a new lobby and return its ID.
    The client can specify max_players in the request body.
    """
    lobby_id = lobby_manager.create_lobby(max_players, adventure_id)
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
        if not lobby:
            raise HTTPException(status_code=404, detail="Lobby not found")
        
        return lobby.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lobby info: {str(e)}")

@router.websocket("/join/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str):
    """
    The main WebSocket endpoint. Clients connect to this route using a lobby ID.
    """
    try:
        print("Connecting new player to lobby ", lobby_id)
        lobby = await lobby_manager.connect(websocket, lobby_id)
        
        await websocket.send_text(f"Welcome to lobby '{lobby.id}'.")
        
        await lobby_manager.broadcast_lobby(lobby_id)
        
        while True:
            try:
                data = await websocket.receive_text()
                print(f"Received message from client in '{lobby.id}': {data}")

                try:
                    import json
                    message = json.loads(data)
                    
                    if message.get("type") == "toggle_ready":
                        new_ready_state = await lobby_manager.toggle_player_ready_state(websocket, lobby_id)
                        await websocket.send_json({
                            "type": "ready_toggled",
                            "success": new_ready_state is not None,
                            "is_ready": new_ready_state
                        })
                            
                    elif message.get("type") == "start_adventure":
                        
                        try: 
                            await game_manager.start_lobby(lobby_id)
                            await game_manager.start_new_round(lobby_id)
                        except Exception as e: 
                            print(e)

                    elif message.get("type") == "submit_choice":
                       
                        try: 
                            await game_manager.submit_choice(lobby_id, websocket, message)
                        except Exception as e: 
                            print(e)

                    else:
                        response_message = f"Server received your message: '{data}'"
                        await websocket.send_text(response_message)
                        print(f"Sent response to client in '{lobby.id}': '{response_message}'")
                        
                except json.JSONDecodeError:
                    
                    response_message = f"Server received your message: '{data}'"
                    await websocket.send_text(response_message)
                    print(f"Sent response to client in '{lobby.lobby_id}': {response_message}")
                
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
        lobby_manager.disconnect(websocket, lobby_id)