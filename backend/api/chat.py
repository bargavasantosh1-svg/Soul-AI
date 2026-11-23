"""
chat.py (api)
-------------
The door between the web page and SOUL's brain.

  POST /api/chat   -> send a message, get SOUL's reply
  POST /api/reset  -> make SOUL forget the current conversation
"""

from fastapi import APIRouter

from backend.logging_config import get_logger
from backend.schemas import ChatRequest, ChatResponse, MessageResponse
from backend.services.brain import brain

router = APIRouter(prefix="/api", tags=["chat"])
log = get_logger("api.chat")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to SOUL and get a reply."""
    reply = brain.chat(request.message)
    return ChatResponse(reply=reply)


@router.post("/reset", response_model=MessageResponse)
def reset() -> MessageResponse:
    """Clear the current conversation."""
    brain.reset()
    return MessageResponse(status="conversation cleared")