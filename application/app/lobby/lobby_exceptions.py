class LobbyIsFullException(Exception):
    """
    Exception raised when a client tries to join a full lobby.
    """
    def __init__(self, lobby_id: int):
        self.lobby_id = lobby_id
        super().__init__(f"Lobby with ID {self.lobby_id} is full.")

class LobbyNotFound(Exception):
    """
    Exception raised when a client tries to join a full lobby.
    """
    def __init__(self, lobby_id: int):
        self.lobby_id = lobby_id
        super().__init__(f"Lobby with id : '{self.lobby_id}' was not found.")

class ConnectionNotFoundException(Exception):
    """
    Exception raised when a connection cannot be found for a given WebSocket.
    """
    pass