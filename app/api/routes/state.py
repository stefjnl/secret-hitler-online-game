"""
Game state routes for Secret Hitler Online.
Provides read-only access to game state, history, and available actions.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any
import logging

from ..models import (
    PlayerResponse, BoardStateResponse, GameHistoryEntry,
    AvailableActionsResponse, APIResponse, ErrorResponse
)
from ...services.game_manager import GameManager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{game_id}/players", response_model=List[PlayerResponse])
async def get_players(
    game_id: str,
    game_manager: GameManager = Depends()
) -> List[PlayerResponse]:
    """
    Get all players in a game.

    - **game_id**: ID of the game
    - Returns list of player information (roles hidden appropriately)
    """
    try:
        players = await game_manager.get_players(game_id)
        return players
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get players for game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get players",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}/board", response_model=BoardStateResponse)
async def get_board_state(
    game_id: str,
    game_manager: GameManager = Depends()
) -> BoardStateResponse:
    """
    Get the current board state.

    - **game_id**: ID of the game
    - Returns policy counts, election tracker, and available powers
    """
    try:
        board_state = await game_manager.get_board_state(game_id)
        return board_state
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get board state for game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get board state",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}/history", response_model=List[GameHistoryEntry])
async def get_game_history(
    game_id: str,
    limit: int = 50,
    game_manager: GameManager = Depends()
) -> List[GameHistoryEntry]:
    """
    Get the game action history.

    - **game_id**: ID of the game
    - **limit**: Maximum number of history entries to return (default: 50)
    - Returns chronological list of game events
    """
    try:
        history = await game_manager.get_game_history(game_id, limit)
        return history
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get game history for {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get game history",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}/available", response_model=AvailableActionsResponse)
async def get_available_actions(
    game_id: str,
    player_id: str = Query(..., description="Player ID (from session/auth)"),
    game_manager: GameManager = Depends()
) -> AvailableActionsResponse:
    """
    Get available actions for a specific player.

    - **game_id**: ID of the game
    - **player_id**: ID of the player (from auth)
    - Returns what actions the player can currently take
    """
    try:
        actions = await game_manager.get_available_actions(game_id, player_id)
        return actions
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game or player not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get available actions for player {player_id} in game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get available actions",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}/phase", response_model=APIResponse)
async def get_current_phase(
    game_id: str,
    game_manager: GameManager = Depends()
) -> APIResponse:
    """
    Get the current game phase.

    - **game_id**: ID of the game
    - Returns current phase and relevant phase data
    """
    try:
        phase_info = await game_manager.get_current_phase(game_id)
        return APIResponse(
            success=True,
            message="Phase retrieved successfully",
            data=phase_info
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get current phase for game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get current phase",
                details={"message": str(e)}
            ).model_dump()
        )

@router.get("/{game_id}/turn", response_model=APIResponse)
async def get_current_turn(
    game_id: str,
    game_manager: GameManager = Depends()
) -> APIResponse:
    """
    Get whose turn it currently is.

    - **game_id**: ID of the game
    - Returns current player turn information
    """
    try:
        turn_info = await game_manager.get_current_turn(game_id)
        return APIResponse(
            success=True,
            message="Turn information retrieved successfully",
            data=turn_info
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="Game not found",
                details={"message": str(e)}
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to get current turn for game {game_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to get current turn",
                details={"message": str(e)}
            ).model_dump()
        )