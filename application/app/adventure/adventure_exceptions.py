
class AdventureNotFoundException(Exception):
    """
    Exception raised when an adventure with a given ID is not found.
    """
    def __init__(self, adventure_id: int):
        self.adventure_id = adventure_id
        super().__init__(f"Adventure with ID {self.adventure_id} not found.")
