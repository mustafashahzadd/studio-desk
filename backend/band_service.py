"""
band_service.py — Band SDK integration for Studio Desk backend
Handles: creating chat rooms, triggering agents, subscribing to events.
"""
import os
import asyncio
import json
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

BAND_REST_URL = "https://app.band.ai"
BAND_WS_URL = "wss://app.band.ai/api/v1/socket/websocket"


class BandService:
    """
    Manages communication with the Band platform.
    - Creates a chat room per job
    - Adds the transcriber agent as participant
    - Sends the video URL to kick off the pipeline
    - Streams events back via WebSocket
    """

    def __init__(self):
        self.human_api_key = os.environ.get(
            "BAND_HUMAN_API_KEY",
            os.environ.get("TRANSCRIBER_API_KEY", "")
        )
        self.transcriber_id = os.environ.get("TRANSCRIBER_AGENT_ID", "")
        self.thumbnailer_id = os.environ.get("THUMBNAILER_AGENT_ID", "")
        self.editor_id = os.environ.get("EDITOR_AGENT_ID", "")
        self._rest = None

    def _get_rest(self):
        if self._rest is None:
            from band.client.rest import AsyncRestClient
            self._rest = AsyncRestClient(
                api_key=self.human_api_key,
                base_url=BAND_REST_URL
            )
        return self._rest

    async def start_pipeline(self, job_id: str, video_url: str) -> tuple[Optional[str], list]:
        """
        Create a Band chat room, add transcriber, and send the video URL.
        Returns (room_id, initial_events_list).
        """
        events = []

        if not self.human_api_key or not self.transcriber_id:
            events.append({
                "sender": "System",
                "message": "⚠️ Band API keys not configured. Running in demo mode.",
                "type": "warning"
            })
            return None, events

        try:
            from band.client.rest import AsyncRestClient
            from thenvoi_rest.human_api_chats.types import CreateMyChatRoomRequestChat
            from thenvoi_rest.types.participant_request import ParticipantRequest
            from thenvoi_rest.types.chat_message_request import ChatMessageRequest
            from thenvoi_rest.types.chat_message_request_mentions_item import (
                ChatMessageRequestMentionsItem,
            )

            rest = self._get_rest()

            # 1. Create a chat room for this job
            room_resp = await rest.human_api_chats.create_my_chat_room(
                chat=CreateMyChatRoomRequestChat()
            )
            room_id = room_resp.chat.id
            logger.info(f"[{job_id}] Created Band chat room: {room_id}")

            events.append({
                "sender": "System",
                "message": f"📋 Band Room created — job {job_id[:8]}",
                "type": "info",
            })

            # 2. Add transcriber agent as participant
            await rest.human_api_participants.add_my_chat_participant(
                chat_id=room_id,
                participant=ParticipantRequest(participant_id=self.transcriber_id),
            )

            # 3. Send video URL with @mention to trigger the transcriber
            mention_content = (
                f"@Transcriber please transcribe and process this video: {video_url}"
            )
            await rest.human_api_messages.send_my_chat_message(
                chat_id=room_id,
                message=ChatMessageRequest(
                    content=mention_content,
                    mentions=[
                        ChatMessageRequestMentionsItem(id=self.transcriber_id)
                    ],
                ),
            )

            events.append({
                "sender": "Transcriber",
                "message": f"audio received — processing {video_url}",
                "type": "info",
            })

            return room_id, events

        except Exception as exc:
            logger.warning(f"[{job_id}] Band API error (falling back to demo): {exc}")
            events.append({
                "sender": "System",
                "message": f"Band API error: {exc}. Running in demo mode.",
                "type": "warning",
            })
            return None, events

    async def stream_room_events(
        self,
        room_id: str,
        api_key: str,
        agent_id: str,
        callback: Callable[[dict], None],
        stop_event: asyncio.Event,
    ):
        """
        Connect to the Band WebSocket and relay events to the callback.
        This uses the agent's own API key and ID.
        """
        from band.client.streaming import WebSocketClient, MessageCreatedPayload

        try:
            async with WebSocketClient(
                ws_url=BAND_WS_URL,
                api_key=api_key,
                agent_id=agent_id,
            ) as ws:
                # Subscribe to the specific room
                await ws.join_room(room_id)

                async for event in ws:
                    if stop_event.is_set():
                        break
                    try:
                        if isinstance(event, MessageCreatedPayload):
                            callback({
                                "sender": getattr(event, "sender_name", "Agent"),
                                "content": getattr(event, "content", ""),
                                "type": "message",
                            })
                    except Exception as e:
                        logger.debug(f"Event parse error: {e}")
        except Exception as exc:
            logger.warning(f"WebSocket stream error for room {room_id}: {exc}")

    async def list_room_messages(self, chat_id: str) -> list:
        """Poll the latest messages from a Band chat room."""
        try:
            rest = self._get_rest()
            resp = await rest.human_api_messages.list_my_chat_messages(
                chat_id=chat_id
            )
            return resp.messages or []
        except Exception as exc:
            logger.warning(f"list_room_messages error: {exc}")
            return []
