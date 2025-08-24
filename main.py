from dotenv import load_dotenv

# Load environment variables BEFORE any other imports
load_dotenv()

from application.routes import lobby
from fastapi import FastAPI

app = FastAPI()

app.include_router(lobby.router, prefix="/lobby")