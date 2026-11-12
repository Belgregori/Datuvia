from fastapi import APIRouter

from app.api import auth, chat, docs, workspaces

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(docs.router)
api_router.include_router(chat.router)
