import asyncio
import json
import httpx
from httpx import AsyncClient
from app.main import app
from app.database.connection import db
from app.auth.dependencies import get_current_user

async def run_test():
    await db.connect()
    try:
        app.dependency_overrides[get_current_user] = lambda: {"id": 1, "first_name": "Test", "last_name": "User", "email": "test@example.com", "organization_id": 1}
        transport = httpx.ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "conversation_id": "test_conv",
                "messages": [
                    {"role": "user", "content": "hi", "conversation_id": "test_conv"}
                ]
            }
            print("Testing greeting (expecting 0 LLM calls):")
            async with client.stream("POST", "/api/v1/ai/chat", json=request_data) as response:
                async for line in response.aiter_lines():
                    if line:
                        print(line)

            request_data["messages"][0]["content"] = "show my boards"
            print("\nTesting fast action (expecting 0 LLM calls):")
            async with client.stream("POST", "/api/v1/ai/chat", json=request_data) as response:
                async for line in response.aiter_lines():
                    if line:
                        print(line)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_test())
