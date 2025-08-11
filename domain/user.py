class User:
    
    """Represents a User and its informations."""
    def __init__(self, name: str):
        self.name = name

    def toDict(self):
        return {"name": self.name}