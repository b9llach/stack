"""
WebSocket router and endpoints
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import logging

from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    room: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication

    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
        room: Optional room to join
    """
    await manager.connect(client_id, websocket)

    # Join room if specified
    if room:
        manager.join_room(client_id, room)
        await manager.broadcast_json_to_room(
            room,
            {
                "type": "user_joined",
                "client_id": client_id,
                "message": f"{client_id} joined the room"
            },
            exclude=[client_id]
        )

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": f"Welcome {client_id}! You are connected.",
            "total_connections": manager.get_connection_count()
        })

        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                # Parse message as JSON
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")

                if message_type == "join_room":
                    # Join a room
                    new_room = message_data.get("room")
                    if new_room:
                        manager.join_room(client_id, new_room)
                        await websocket.send_json({
                            "type": "room_joined",
                            "room": new_room,
                            "message": f"Joined room {new_room}"
                        })

                elif message_type == "leave_room":
                    # Leave a room
                    leave_room = message_data.get("room")
                    if leave_room:
                        manager.leave_room(client_id, leave_room)
                        await websocket.send_json({
                            "type": "room_left",
                            "room": leave_room,
                            "message": f"Left room {leave_room}"
                        })

                elif message_type == "room_message":
                    # Send message to room
                    target_room = message_data.get("room")
                    content = message_data.get("content", "")
                    if target_room:
                        await manager.broadcast_json_to_room(
                            target_room,
                            {
                                "type": "room_message",
                                "from": client_id,
                                "content": content,
                                "room": target_room
                            }
                        )

                elif message_type == "broadcast":
                    # Broadcast to all clients
                    content = message_data.get("content", "")
                    await manager.broadcast_json({
                        "type": "broadcast",
                        "from": client_id,
                        "content": content
                    }, exclude=[client_id])

                elif message_type == "private":
                    # Send private message
                    to_client = message_data.get("to")
                    content = message_data.get("content", "")
                    if to_client:
                        await manager.send_json_message({
                            "type": "private",
                            "from": client_id,
                            "content": content
                        }, to_client)

                else:
                    # Default: echo message back
                    await websocket.send_json({
                        "type": "echo",
                        "message": data
                    })

            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)

        # Notify room members if in a room
        if room:
            await manager.broadcast_json_to_room(
                room,
                {
                    "type": "user_left",
                    "client_id": client_id,
                    "message": f"{client_id} left the room"
                }
            )

        logger.info(f"Client {client_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


@router.websocket("/ws/chat/{room_id}")
async def chat_room_endpoint(
    websocket: WebSocket,
    room_id: str,
    client_id: str = Query(...)
):
    """
    WebSocket endpoint for chat rooms

    Args:
        websocket: WebSocket connection
        room_id: Chat room identifier
        client_id: Client identifier
    """
    await manager.connect(client_id, websocket)
    manager.join_room(client_id, room_id)

    try:
        # Notify others about new user
        await manager.broadcast_json_to_room(
            room_id,
            {
                "type": "user_joined",
                "client_id": client_id,
                "room": room_id,
                "members": manager.get_room_clients(room_id)
            },
            exclude=[client_id]
        )

        # Send room info to new user
        await websocket.send_json({
            "type": "joined_room",
            "room": room_id,
            "members": manager.get_room_clients(room_id)
        })

        # Listen for messages
        while True:
            data = await websocket.receive_text()

            # Broadcast message to room
            await manager.broadcast_json_to_room(
                room_id,
                {
                    "type": "message",
                    "from": client_id,
                    "content": data,
                    "room": room_id
                }
            )

    except WebSocketDisconnect:
        manager.leave_room(client_id, room_id)
        manager.disconnect(client_id)

        # Notify others about user leaving
        await manager.broadcast_json_to_room(
            room_id,
            {
                "type": "user_left",
                "client_id": client_id,
                "room": room_id,
                "members": manager.get_room_clients(room_id)
            }
        )

        logger.info(f"Client {client_id} left room {room_id}")
