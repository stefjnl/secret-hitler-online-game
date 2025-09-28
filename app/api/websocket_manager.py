"""
WebSocket Manager for Secret Hitler Online.
Handles real-time communication, connection management, and broadcasting.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timedelta

from fastapi import WebSocket, WebSocketDisconnect
from ..api.models import WebSocketMessage, ConnectionStatusMessage

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time communication."""

    def __init__(self):
        # Active connections: connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Game rooms: game_id -> set of connection_ids
        self.game_rooms: Dict[str, Set[str]] = {}

        # Player connections: player_id -> connection_id
        self.player_connections: Dict[str, str] = {}

        # Connection metadata: connection_id -> {"game_id", "player_id", "connected_at", "last_ping"}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # Network quality tracking: connection_id -> {"latency_ms", "packet_loss", "quality"}
        self.network_quality: Dict[str, Dict[str, Any]] = {}

        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_stale_connections())

    async def connect(self, websocket: WebSocket, game_id: str, player_id: str) -> str:
        """
        Accept a WebSocket connection and add it to the game room.

        Args:
            websocket: The WebSocket connection
            game_id: ID of the game to join
            player_id: ID of the connecting player

        Returns:
            connection_id: Unique identifier for this connection
        """
        await websocket.accept()

        # Generate unique connection ID
        connection_id = f"{player_id}_{game_id}_{id(websocket)}"

        # Store connection
        self.active_connections[connection_id] = websocket

        # Add to game room
        if game_id not in self.game_rooms:
            self.game_rooms[game_id] = set()
        self.game_rooms[game_id].add(connection_id)

        # Update player connection (disconnect previous if exists)
        if player_id in self.player_connections:
            old_connection_id = self.player_connections[player_id]
            await self._disconnect_connection(old_connection_id, "new_connection")

        self.player_connections[player_id] = connection_id

        # Store metadata
        self.connection_metadata[connection_id] = {
            "game_id": game_id,
            "player_id": player_id,
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }

        # Initialize network quality tracking
        self.network_quality[connection_id] = {
            "latency_ms": 0,
            "packet_loss": 0,
            "quality": "good"
        }

        logger.info(f"WebSocket connected: {connection_id} (player: {player_id}, game: {game_id})")

        # Send connection confirmation
        await self._send_to_connection(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        })

        return connection_id

    async def disconnect(self, connection_id: str, reason: str = "client_disconnect") -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            connection_id: ID of the connection to disconnect
            reason: Reason for disconnection
        """
        await self._disconnect_connection(connection_id, reason)

    async def _disconnect_connection(self, connection_id: str, reason: str) -> None:
        """Internal method to handle disconnection."""
        if connection_id not in self.active_connections:
            return

        # Get metadata before cleanup
        metadata = self.connection_metadata.get(connection_id, {})
        game_id = metadata.get("game_id")
        player_id = metadata.get("player_id")

        # Remove from active connections
        websocket = self.active_connections.pop(connection_id)

        # Remove from game room
        if game_id and game_id in self.game_rooms:
            self.game_rooms[game_id].discard(connection_id)
            if not self.game_rooms[game_id]:
                del self.game_rooms[game_id]

        # Remove player connection
        if player_id and self.player_connections.get(player_id) == connection_id:
            del self.player_connections[player_id]

        # Clean up metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]

        if connection_id in self.network_quality:
            del self.network_quality[connection_id]

        # Close WebSocket if still open
        try:
            await websocket.close(code=1000, reason=reason)
        except Exception as e:
            logger.warning(f"Error closing WebSocket {connection_id}: {e}")

        logger.info(f"WebSocket disconnected: {connection_id} (reason: {reason})")

    async def broadcast_to_game(self, game_id: str, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connections in a game room.

        Args:
            game_id: ID of the game room
            message: Message to broadcast
        """
        if game_id not in self.game_rooms:
            logger.warning(f"Attempted to broadcast to non-existent game room: {game_id}")
            return

        connection_ids = self.game_rooms[game_id].copy()
        message["timestamp"] = datetime.now().isoformat()

        successful_sends = 0
        failed_sends = 0

        for connection_id in connection_ids:
            try:
                await self._send_to_connection(connection_id, message)
                successful_sends += 1
            except Exception as e:
                logger.warning(f"Failed to send message to {connection_id}: {e}")
                failed_sends += 1
                # Mark connection for cleanup
                await self._disconnect_connection(connection_id, "send_failed")

        logger.debug(f"Broadcast to game {game_id}: {successful_sends} successful, {failed_sends} failed")

    async def send_to_player(self, player_id: str, message: Dict[str, Any]) -> None:
        """
        Send a message to a specific player.

        Args:
            player_id: ID of the target player
            message: Message to send
        """
        connection_id = self.player_connections.get(player_id)
        if not connection_id:
            logger.warning(f"No active connection for player {player_id}")
            return

        message["timestamp"] = datetime.now().isoformat()
        await self._send_to_connection(connection_id, message)

    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Send a message to a specific connection."""
        if connection_id not in self.active_connections:
            raise ValueError(f"Connection {connection_id} not found")

        websocket = self.active_connections[connection_id]

        # Convert message to JSON
        json_message = json.dumps(message)

        # Send message
        await websocket.send_text(json_message)

        # Update last activity
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["last_ping"] = datetime.now()

    async def handle_ping(self, connection_id: str) -> Dict[str, Any]:
        """Handle a ping from a client and return pong with latency info."""
        if connection_id not in self.connection_metadata:
            return {"error": "Connection not found"}

        now = datetime.now()
        metadata = self.connection_metadata[connection_id]
        last_ping = metadata.get("last_ping", now)

        # Calculate latency (simplified)
        latency_ms = int((now - last_ping).total_seconds() * 1000)

        # Update network quality
        self.network_quality[connection_id]["latency_ms"] = latency_ms
        self.network_quality[connection_id]["last_ping"] = now

        # Determine connection quality
        if latency_ms < 100:
            quality = "excellent"
        elif latency_ms < 200:
            quality = "good"
        elif latency_ms < 500:
            quality = "fair"
        else:
            quality = "poor"

        self.network_quality[connection_id]["quality"] = quality

        return {
            "type": "pong",
            "latency_ms": latency_ms,
            "quality": quality,
            "timestamp": now.isoformat()
        }

    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection."""
        if connection_id not in self.connection_metadata:
            return None

        metadata = self.connection_metadata[connection_id]
        network_info = self.network_quality.get(connection_id, {})

        return {
            "connection_id": connection_id,
            "game_id": metadata.get("game_id"),
            "player_id": metadata.get("player_id"),
            "connected_at": metadata.get("connected_at").isoformat(),
            "last_ping": metadata.get("last_ping").isoformat(),
            "network_quality": network_info
        }

    async def get_game_connections(self, game_id: str) -> List[Dict[str, Any]]:
        """Get all connections for a game."""
        if game_id not in self.game_rooms:
            return []

        connection_ids = self.game_rooms[game_id]
        connections = []

        for connection_id in connection_ids:
            info = await self.get_connection_info(connection_id)
            if info:
                connections.append(info)

        return connections

    async def _cleanup_stale_connections(self) -> None:
        """Background task to clean up stale connections."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                now = datetime.now()
                stale_threshold = timedelta(minutes=5)  # 5 minutes without ping
                stale_connections = []

                for connection_id, metadata in self.connection_metadata.items():
                    last_ping = metadata.get("last_ping", metadata.get("connected_at", now))
                    if now - last_ping > stale_threshold:
                        stale_connections.append(connection_id)

                for connection_id in stale_connections:
                    logger.info(f"Cleaning up stale connection: {connection_id}")
                    await self._disconnect_connection(connection_id, "stale_connection")

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    async def shutdown(self) -> None:
        """Shutdown the WebSocket manager and close all connections."""
        logger.info("Shutting down WebSocket manager")

        # Cancel cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self._disconnect_connection(connection_id, "server_shutdown")

        logger.info("WebSocket manager shutdown complete")