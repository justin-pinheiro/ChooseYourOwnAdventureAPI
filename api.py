import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

lobbies: dict[str, set[WebSocket]] = {}

@app.websocket("/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str):
    """
    WebSocket endpoint for a specific lobby.
    A new connection is established for each client.
    """
    await websocket.accept()
    
    try:
        if lobby_id not in lobbies:
            lobbies[lobby_id] = set()
            print(f"Lobby '{lobby_id}' created.")
        
        lobbies[lobby_id].add(websocket)
        print(f"Client connected to lobby '{lobby_id}'. Total clients: {len(lobbies[lobby_id])}")

        await websocket.send_text(f"Welcome to lobby '{lobby_id}'.")

        while True:
            data = await websocket.receive_text()
            print(f"Received message from client in '{lobby_id}': {data}")

            broadcast_message = json.dumps({"lobby_id": lobby_id, "message": data})

            for client_ws in list(lobbies[lobby_id]):
                if client_ws != websocket:
                    try:
                        await client_ws.send_text(broadcast_message)
                    except WebSocketDisconnect:
                        lobbies[lobby_id].discard(client_ws)
                        print(f"Client disconnected during broadcast, removing from lobby '{lobby_id}'.")

    except WebSocketDisconnect:
        print(f"Client disconnected from lobby '{lobby_id}'.")
    finally:
        if websocket in lobbies.get(lobby_id, set()):
            lobbies[lobby_id].remove(websocket)
            print(f"Client removed from lobby '{lobby_id}'. Total clients: {len(lobbies[lobby_id])}")

        if not lobbies.get(lobby_id):
            lobbies.pop(lobby_id, None)
            print(f"Lobby '{lobby_id}' is now empty and has been removed.")
