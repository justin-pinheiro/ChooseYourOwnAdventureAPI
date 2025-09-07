# Choose your own adventure - Backend API

## Purpose

This API acts as the game manager for our multiplayer mobile game.

It handles lobby management and in-game communication.

## Endpoints

### HTTP API Endpoints

These RESTful endpoints are used for lobby creation and retrieval. All endpoints start with `/lobbies`.

#### **`POST /create`**

Creates a new lobby and initializes it with a specific adventure.

**Request parameters:**
- `max_players` (int): The maximum number of players allowed in the lobby.
- `adventure_id` (int): The unique ID of the adventure for this game.

**Response:**
- **Success (200 OK):** Returns the unique `lobby_id` for the newly created lobby.

    Example:

    ```json
    {
        "lobby_id": "a1b2c3d4"
    }
    ```

#### **`GET /`**

Retrieves a summary of all active lobbies.

**Response:**

- **Success (200 OK):** A JSON object containing a list of lobbies and their current status.
    
    Example:
    ```json
    {
        "total_lobbies": 2,
        "lobbies": [
        {
            "id": "a1b2c3d4",
            "max_players": 4,
            "current_players": 2,
            "adventure_title": "The Cursed Mansion",
            "game_started": false,
            "is_full": false,
            "players": [
                { 
                    "name": "Player 1", 
                    "is_ready": true 
                },
                { 
                    "name": "Player 2", 
                    "is_ready": false 
                }
            ]
        }
        ]
    }
    ```

#### **`GET /{lobby_id}`**

Fetches detailed information for a specific lobby.

**Request parameter:**
- `lobby_id` (string): The unique ID of the lobby.

**Response:**

- **Success (200 OK):** A JSON object with detailed lobby information.

    Example:
    ```json
    {
        "id": "a1b2c3d4",
        "max_players": 4,
        "current_players": 2,
        "adventure_title": "The Cursed Mansion",
        "game_started": false,
        "is_full": false,
        "players": [
            { 
                "name": "Player 1", 
                "is_ready": true 
            },
            { 
                "name": "Player 2", 
                "is_ready": false 
            }
        ]
    }
    ```

- **Error (404 Not Found):** If the specified lobby does not exist.

-----

### WebSocket communication

All in-game communication, including joining a lobby, readying up, and playing the game, is handled via a WebSocket connection for fast and bidirectional messages.

#### **Connection URL:**

`ws://<server-address>/lobbies/join/{lobby_id}`

Upon a successful connection, the server will broadcast the updated lobby state to all connected clients. If the lobby is full or not found, the connection will be rejected with an HTTP error.

#### **Client-Server communication**

Clients send these JSON messages to the server to perform actions.

| `type` | Payload | Effect |
|--------|---------|-------------|
| `toggle_ready` | `{ "type": "toggle_ready" }` | Informs that player is ready.
| `start_adventure` | `{ "type": "start_adventure" }` | Starts the game if all players are ready. Request will only be accepted by the server if the client is the host of the lobby |
| `submit_choice` | `{ "type": "submit_choice", "choice_index": 0 }` | Submits the player's choice for the current round. |

#### **Server-client communication**

The server sends these messages to clients to update the game state or provide new information.

| `type`| Payload | Description |
--------|---------|-------------|
| `lobby_info` | `{ "type": "lobby_info", "info": { ... } }` | A broadcasted message with the full, updated lobby state. |
| `ready_toggled` | `{ "type": "ready_toggled", "success": true, "is_ready": true }` | Confirms that the player's ready state was successfully changed. |
| `start_adventure` | `{ "type": "start_adventure", "info": { "success": true } }` | Broadcasts to all players that the adventure has begun. |
| `new_round` | `{ "type": "new_round", "info": { "round_index": 1, "text": "...", "choices": ["...", "..."] } }` | Provides the new story chapter and available choices for a player. |

## Running the server

Follow these instructions to get the server running.

### Step 1: Install requirements

First, you'll need to set up a virtual environment and install the necessary dependencies.

1.  **Create a virtual environment:**
    `python -m venv .venv`

2.  **Activate the environment:**
    `.\.venv\Scripts\activate`

3.  **Install dependencies:**
    `pip install -r requirements.txt`

---

### Step 2: Run the server

Once your requirements are installed, you can start the server.

-   **Start the server with live reloading:**
    `uvicorn main:app --reload`

This command runs the `uvicorn` server, which hosts the FastAPI application defined in `main.py`. The `--reload` flag is useful for development as it automatically restarts the server whenever you save changes to your code.