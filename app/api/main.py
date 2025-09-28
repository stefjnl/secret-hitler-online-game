"""
FastAPI application for Secret Hitler Online.
Provides REST API endpoints and WebSocket support for real-time gameplay.
"""
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import json
from typing import Dict, Any

from .models import (
    CreateGameRequest, JoinGameRequest, NominateChancellorRequest,
    VoteRequest, DiscardPolicyRequest, EnactPolicyRequest,
    PresidentialPowerRequest, ChatMessageRequest,
    APIResponse, ErrorResponse, GameStateResponse
)
from .routes import game, actions, state
from .websocket_manager import WebSocketManager
from ..services.game_manager import GameManager
from ..services.ai_integration import AIIntegrationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
websocket_manager = WebSocketManager()
game_manager = GameManager(websocket_manager)
ai_integration = AIIntegrationService(game_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting Secret Hitler Online API server")
    # Startup tasks
    game_manager.start_cleanup_task()
    await websocket_manager.start_cleanup_task()
    yield
    # Shutdown tasks
    logger.info("Shutting down Secret Hitler Online API server")
    await websocket_manager.shutdown()
    await game_manager.cleanup_all_games()

# Create FastAPI application
app = FastAPI(
    title="Secret Hitler Online API",
    description="Real-time multiplayer Secret Hitler game API",
    version="1.0.0"
    # lifespan=lifespan  # Temporarily disabled for testing
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
def get_game_manager() -> GameManager:
    return game_manager

def get_ai_integration() -> AIIntegrationService:
    return ai_integration

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            details={"message": str(exc)}
        ).model_dump()
    )

# Include routers
app.include_router(
    game.router,
    prefix="/api/games",
    tags=["Game Management"]
)

app.include_router(
    actions.router,
    prefix="/api/games",
    tags=["Player Actions"]
)

app.include_router(
    state.router,
    prefix="/api/games",
    tags=["Game State"]
)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "secret-hitler-api"}

# WebSocket endpoint
@app.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    player_id: str = Query(..., description="Player ID for authentication")
):
    """
    WebSocket endpoint for real-time game communication.

    - **game_id**: ID of the game to connect to
    - **player_id**: ID of the connecting player (from query param for now)
    """
    connection_id = await websocket_manager.connect(websocket, game_id, player_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            message_type = message.get("type")

            if message_type == "ping":
                # Handle ping/pong for connection health
                pong_response = await websocket_manager.handle_ping(connection_id)
                await websocket.send_text(json.dumps(pong_response))

            elif message_type == "subscribe":
                # Client is subscribing to game updates (already handled in connect)
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "game_id": game_id,
                    "timestamp": json.dumps({"timestamp": "now"})  # Will be replaced with proper datetime
                }))

            else:
                # Unknown message type
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"Unknown message type: {message_type}",
                    "timestamp": json.dumps({"timestamp": "now"})
                }))

    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Secret Hitler Online API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws/{game_id}?player_id={player_id}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )