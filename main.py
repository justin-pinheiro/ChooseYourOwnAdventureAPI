from application.routes import lobby
from fastapi import FastAPI

app = FastAPI()

app.include_router(lobby.router, prefix="/lobby")