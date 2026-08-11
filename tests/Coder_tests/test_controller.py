import uuid
from src.agents.coder.controller import CoderController
from dotenv import load_dotenv

load_dotenv()

task_id = str(uuid.uuid4())
# We give it a task that requires it to write a script that runs without crashing.
plan = """
Write the fastapi crud operations for a simple todo app.
"""

controller = CoderController(task_id=task_id, plan_summary=plan)

print("🚀 Starting Autonomous Coder Loop...")
final_state = controller.run()

print("\n🏁 Loop Finished!")
print(f"Status: {final_state.status}")
print(f"Total Iterations: {final_state.iteration}")
print(f"Exported Artifacts: artifacts/{task_id}/workspace/")