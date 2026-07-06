import asyncio
from app.database.connection import db
from app.services.task_service import TaskService
from app.services.board_service import BoardService
from app.ai.tools.domain_tools import UpdateTaskTool, UpdateTaskParams

async def main():
    await db.connect()
    async with db.pool.acquire() as conn:
        try:
            services = {
                "task_service": TaskService(conn),
                "board_service": BoardService(conn)
            }
            # The current_user dict (assuming user 10)
            current_user = {"id": 10, "organization_id": 3}
            
            tool = UpdateTaskTool()
            params = UpdateTaskParams(task_name="BKND task 2", board_name="Backend Refactoring", title="bro i am great")
            
            res = await tool.execute(params, current_user, services)
            print("Update success:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("Error:", type(e), str(e))
    await db.disconnect()

asyncio.run(main())
