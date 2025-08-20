from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import traceback
from application.app.lobby.lobby_manager import LobbyManager, Connection

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

                try:
                    import json
                    message = json.loads(data)
                    
                    if message.get("type") == "toggle_ready":
                        new_ready_state = await manager.toggle_player_ready_state(websocket, lobby_id)
                        if new_ready_state is not None:
                            await websocket.send_json({
                                "type": "ready_toggled",
                                "success": True,
                                "is_ready": new_ready_state
                            })
                            
                    elif message.get("type") == "start_adventure":
                        
                        try: 
                            await manager.start_lobby(lobby_id)
                            await manager.start_new_round(lobby_id)
                        except Exception as e: 
                            print(e)

                    elif message.get("type") == "submit_choice":
                       
                        try: 
                            await manager.submit_choice(lobby_id, websocket, message)
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
        manager.disconnect(websocket, lobby_id)