from dotenv import load_dotenv

# Load environment variables BEFORE any other imports
load_dotenv()

from application.routes import lobby, adventure
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files for serving images
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(lobby.router, prefix="/lobby")
app.include_router(adventure.router, prefix="/adventures")