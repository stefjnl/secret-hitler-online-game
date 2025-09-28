"""
Game management routes for Secret Hitler Online.
Handles game creation, joining, starting, and leaving.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
import logging

from ..models import (
    CreateGameRequest, JoinGameRequest, APIResponse, ErrorResponse,
    GameStateResponse
)
from ...services.game_manager import GameManager
from ...services.ai_integration import AIIntegrationService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/create", response_model=APIResponse)
async def create_game(
    request: CreateGameRequest,
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Create a new game room.

    - **creator_name**: Name of the player creating the game
    - Returns game ID and initial game state
    """
    try:
        game_id = await game_manager.create_game(request.creator_name)
        logger.info(f"Game created: {game_id} by {request.creator_name}")

        # Optionally fill with AI players for testing
        # await ai_integration.fill_with_ai_players(game_id)

        return APIResponse(
            success=True,
            message="Game created successfully",
            data={"game_id": game_id}
        )
    except Exception as e:
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to create game",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/join", response_model=APIResponse)
async def join_game(
    game_id: str,
    request: JoinGameRequest,
    game_manager: GameManager = Depends()
) -> APIResponse:
    """
    Join an existing game room.

    - **game_id**: ID of the game to join
    - **player_name**: Name of the joining player
    """
    try:
        result = await game_manager.join_game(game_id, request.player_name)
        logger.info(f"Player {request.player_name} joined game {game_id}")

        return APIResponse(
            success=True,
            message="Joined game successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Cannot join game",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to join game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to join game",
                details={"message": str(e)}
            ).model_dump()
        )

@router.post("/{game_id}/start", response_model=APIResponse)
async def start_game(
    game_id: str,
    game_manager: GameManager = Depends(),
    ai_integration: AIIntegrationService = Depends()
) -> APIResponse:
    """
    Start a game when enough players have joined.

    - **game_id**: ID of the game to start
    """
    try:
        result = await game_manager.start_game(game_id)

        # Process AI turns if needed
        await ai_integration.process_ai_turns(game_id)

        logger.info(f"Game {game_id} started successfully")

        return APIResponse(
            success=True,
            message="Game started successfully",
            data=result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Cannot start game",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to start game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to start game",
                details={"message": str(e)}
            ).model_dump()
        )

@router.delete("/{game_id}", response_model=APIResponse)
async def leave_game(
    game_id: str,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends()
) -> APIResponse:
    """
    Leave a game room.

    - **game_id**: ID of the game to leave
    - **player_id**: ID of the leaving player (from session/auth)
    """
    try:
        await game_manager.leave_game(game_id, player_id)
        logger.info(f"Player {player_id} left game {game_id}")

        return APIResponse(
            success=True,
            message="Left game successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Cannot leave game",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to leave game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to leave game",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    game_manager: GameManager = Depends()
) -> GameStateResponse:
    """
    Get the current state of a game.

    - **game_id**: ID of the game
    - Returns complete game state for the requesting player
    """
    try:
        game_state = await game_manager.get_game_state(game_id)
        return game_state
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get game state for {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get game state",
                details={"message": str(e)}
            ).model_dump()
        )