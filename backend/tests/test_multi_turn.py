import asyncio
import os
import sys
sys.path.insert(0, r"d:\kanban-project\backend")
import json
import logging

logging.basicConfig(level=logging.ERROR)

from app.database.connection import db
from app.services.ai_service import AIService
from app.schemas.ai import AIChatRequest, ChatMessage
import uuid

async def test_multi_turn():
    await db.connect()
    async with db.pool.acquire() as conn:
        ai_service = AIService(conn)
        
        # Test User
        current_user = {
            "id": 1,
            "organization_id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "SUPER_ADMIN"
        }
        
        # Turn 1
        req1 = AIChatRequest(
            conversation_id="test_conv_1",
            messages=[ChatMessage(role="user", content="Create a task", conversation_id="test_conv_1")]
        )
        print("\n--- TURN 1 ---")
        async for chunk in ai_service.chat_stream(req1, current_user, str(uuid.uuid4())):
            print(chunk.strip())
            
        # Turn 2
        req2 = AIChatRequest(
            conversation_id="test_conv_1",
            messages=[
                ChatMessage(role="user", content="Create a task", conversation_id="test_conv_1"),
                ChatMessage(role="assistant", content="What should the task be named, and which board should it go into?", conversation_id="test_conv_1"),
                ChatMessage(role="user", content="Name it 'Login Bug' in the Frontend board", conversation_id="test_conv_1")
            ]
        )
        print("\n--- TURN 2 ---")
        async for chunk in ai_service.chat_stream(req2, current_user, str(uuid.uuid4())):
            print(chunk.strip())

if __name__ == "__main__":
    asyncio.run(test_multi_turn())
