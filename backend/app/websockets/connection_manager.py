"""
WebSocket connection manager
"""
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication
    """

    def __init__(self):
        """
        Initialize connection manager
        """
        # Active connections: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Room-based connections: {room_id: {client_id, ...}}
        self.rooms: Dict[str, Set[str]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """
        Accept and store new WebSocket connection

        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """
        Remove WebSocket connection

        Args:
            client_id: Client identifier to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            # Remove from all rooms
            for room_id in list(self.rooms.keys()):
                if client_id in self.rooms[room_id]:
                    self.rooms[room_id].remove(client_id)
                    # Clean up empty rooms
                    if not self.rooms[room_id]:
                        del self.rooms[room_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, client_id: str):
        """
        Send message to specific client

        Args:
            message: Message to send
            client_id: Target client identifier
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)

    async def send_json_message(self, data: dict, client_id: str):
        """
        Send JSON message to specific client

        Args:
            data: Data to send as JSON
            client_id: Target client identifier
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(data)

    async def broadcast(self, message: str, exclude: List[str] = None):
        """
        Broadcast message to all connected clients

        Args:
            message: Message to broadcast
            exclude: List of client IDs to exclude from broadcast
        """
        exclude = exclude or []
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")

    async def broadcast_json(self, data: dict, exclude: List[str] = None):
        """
        Broadcast JSON message to all connected clients

        Args:
            data: Data to broadcast as JSON
            exclude: List of client IDs to exclude from broadcast
        """
        exclude = exclude or []
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")

    def join_room(self, client_id: str, room_id: str):
        """
        Add client to a room

        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(client_id)
        logger.info(f"Client {client_id} joined room {room_id}")

    def leave_room(self, client_id: str, room_id: str):
        """
        Remove client from a room

        Args:
            client_id: Client identifier
            room_id: Room identifier
        """
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            self.rooms[room_id].remove(client_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
            logger.info(f"Client {client_id} left room {room_id}")

    async def broadcast_to_room(self, room_id: str, message: str, exclude: List[str] = None):
        """
        Broadcast message to all clients in a room

        Args:
            room_id: Room identifier
            message: Message to broadcast
            exclude: List of client IDs to exclude from broadcast
        """
        exclude = exclude or []
        if room_id in self.rooms:
            for client_id in self.rooms[room_id]:
                if client_id not in exclude and client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_text(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id} in room {room_id}: {e}")

    async def broadcast_json_to_room(self, room_id: str, data: dict, exclude: List[str] = None):
        """
        Broadcast JSON message to all clients in a room

        Args:
            room_id: Room identifier
            data: Data to broadcast as JSON
            exclude: List of client IDs to exclude from broadcast
        """
        exclude = exclude or []
        if room_id in self.rooms:
            for client_id in self.rooms[room_id]:
                if client_id not in exclude and client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_json(data)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {client_id} in room {room_id}: {e}")

    def get_room_clients(self, room_id: str) -> List[str]:
        """
        Get list of clients in a room

        Args:
            room_id: Room identifier

        Returns:
            List of client identifiers
        """
        return list(self.rooms.get(room_id, set()))

    def get_connection_count(self) -> int:
        """
        Get total number of active connections

        Returns:
            Number of active connections
        """
        return len(self.active_connections)


# Create singleton instance
manager = ConnectionManager()
