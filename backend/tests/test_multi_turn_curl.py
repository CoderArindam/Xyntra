import httpx
import json
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # 1. Login
        resp = await client.post("/api/v1/auth/login", json={"email": "admin@devarc.com", "password": "12345678"})
        if resp.status_code != 200:
            print("Login failed:", resp.status_code, resp.text)
            return
        
        cookies = resp.cookies
        headers = {}
        
        # 2. Start Conversation (Turn 1)
        print("--- TURN 1 ---")
        req1 = {
            "conversation_id": "test_multi_1",
            "messages": [
                {"role": "user", "content": "Create a task"}
            ]
        }
        
        async with client.stream("POST", "/api/v1/ai/chat", json=req1, headers=headers, cookies=cookies) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)
        
        # 3. Turn 2
        print("\n--- TURN 2 ---")
        req2 = {
            "conversation_id": "test_multi_1",
            "messages": [
                {"role": "user", "content": "Create a task"},
                {"role": "assistant", "content": "What should the task be named, and which project should it go into?"},
                {"role": "user", "content": "Name it 'Login Bug' in the Frontend project"}
            ]
        }
        
        async with client.stream("POST", "/api/v1/ai/chat", json=req2, headers=headers, cookies=cookies) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

if __name__ == "__main__":
    asyncio.run(test())
