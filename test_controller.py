import uuid
from src.agents.coder.controller import CoderController
from dotenv import load_dotenv

load_dotenv()

task_id = str(uuid.uuid4())
# We give it a task that requires it to write a script that runs without crashing.
plan = """
Using the link below of the ollam tunnel create a simple legal chatbot for pakistan law with memroy and history and metrices to evaluate the repsonse of the LLM/chatbot.
LLM_BASE_URL: str = "https://joke-abilities-assistant-ticket.trycloudflare.com/v1"
LLM_MODEL: str = "qwen3-coder-next:latest"
"""

controller = CoderController(task_id=task_id, plan_summary=plan)

print("🚀 Starting Autonomous Coder Loop...")
final_state = controller.run()

print("\n🏁 Loop Finished!")
print(f"Status: {final_state.status}")
print(f"Total Iterations: {final_state.iteration}")
print(f"Exported Artifacts: artifacts/{task_id}/workspace/")