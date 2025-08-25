# Lobby Information API Endpoints

## Overview
These endpoints allow you to retrieve information about existing lobbies in the system.

## Endpoints

### 1. Get All Lobbies
**GET** `/lobby/`

Returns information about all existing lobbies.

**Response Format:**
```json
{
  "total_lobbies": 2,
  "lobbies": [
    {
      "id": "12345678",
      "max_players": 4,
      "current_players": 2,
      "adventure_id": 1,
      "adventure_title": "The Crypt of the Serpent King",
      "game_started": false,
      "current_round": 0,
      "players": [
        {
          "name": "Player 1",
          "is_ready": true
        },
        {
          "name": "Player 2",
          "is_ready": false
        }
      ],
      "is_full": false,
      "can_join": true
    }
  ]
}
```

### 2. Get Specific Lobby Info
**GET** `/lobby/{lobby_id}`

Returns detailed information about a specific lobby.

**Parameters:**
- `lobby_id` (path): The ID of the lobby to retrieve

**Response Format:**
```json
{
  "lobby": {
    "id": "12345678",
    "max_players": 4,
    "current_players": 2,
    "adventure_id": 1,
    "adventure_title": "The Crypt of the Serpent King",
    "adventure_description": "You and your companions have been tasked with exploring...",
    "game_started": false,
    "current_round": 0,
    "players": [
      {
        "name": "Player 1",
        "is_ready": true
      },
      {
        "name": "Player 2",
        "is_ready": false
      }
    ],
    "is_full": false,
    "can_join": true
  }
}
```

**Error Responses:**
- `404 Not Found`: Lobby with the specified ID doesn't exist
- `500 Internal Server Error`: Server error occurred

### 3. Create Lobby (Existing)
**POST** `/lobby/create`

Creates a new lobby with the specified parameters.

**Parameters:**
- `max_players` (query): Maximum number of players (integer)
- `adventure_id` (query): ID of the adventure to use (integer)

**Response Format:**
```json
{
  "lobby_id": "12345678"
}
```

## Field Descriptions

### Lobby Fields
- `id`: Unique identifier for the lobby (8-character string)
- `max_players`: Maximum number of players allowed
- `current_players`: Current number of connected players
- `adventure_id`: ID of the associated adventure
- `adventure_title`: Title of the adventure
- `adventure_description`: Full description of the adventure (only in specific lobby endpoint)
- `game_started`: Whether the game has started
- `current_round`: Current round number (0 if not started)
- `is_full`: Whether the lobby has reached maximum capacity
- `can_join`: Whether new players can join (not full and game not started)

### Player Fields
- `name`: Player's display name
- `is_ready`: Whether the player is ready to start

## Usage Examples

### Frontend Integration
```javascript
// Get all lobbies for lobby browser
const response = await fetch('/lobby/');
const data = await response.json();
const availableLobbies = data.lobbies.filter(lobby => lobby.can_join);

// Get specific lobby details
const lobbyResponse = await fetch(`/lobby/${lobbyId}`);
const lobbyData = await lobbyResponse.json();
const lobby = lobbyData.lobby;

// Display lobby status
console.log(`${lobby.adventure_title}: ${lobby.current_players}/${lobby.max_players} players`);
```

### Lobby Browser Component
Use these endpoints to create a lobby browser that shows:
- Available lobbies to join
- Adventure information
- Player counts
- Ready status
- Game progress

## WebSocket Connection
After retrieving lobby information, players can join using the WebSocket endpoint:
**WebSocket** `/lobby/join/{lobby_id}`

## Error Handling
All endpoints return appropriate HTTP status codes:
- `200 OK`: Success
- `404 Not Found`: Lobby not found
- `500 Internal Server Error`: Server error

Make sure to handle these status codes in your frontend application.
