"""
schemas.py
----------
The "forms" for messages going in and out of SOUL.
FastAPI uses these to check every message automatically.
"""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """What the web page sends to SOUL."""

    # Remove spaces at the start and end, so "   " counts as empty
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="What you want to say to SOUL",
    )


class ChatResponse(BaseModel):
    """What SOUL sends back after a chat message."""

    reply: str


class HealthResponse(BaseModel):
    """The answer to 'is SOUL alive and set up?'"""

    status: str
    assistant: str
    api_key_configured: bool
    model: str


class MessageResponse(BaseModel):
    """A simple answer like 'done'."""

    status: str


class ErrorResponse(BaseModel):
    """What SOUL sends when something goes wrong."""

    error: str
    detail: str