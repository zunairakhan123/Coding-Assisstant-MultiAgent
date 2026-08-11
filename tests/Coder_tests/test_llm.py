import uuid
import os
from src.agents.coder.state import CoderState, StructuredError
from src.agents.coder.llm import CoderLLM
from dotenv import load_dotenv

load_dotenv()

# 1. Mock a Coder State
task_id = str(uuid.uuid4())
state = CoderState(
    task_id=task_id,
    plan_summary="Create a simple math.py file with an add(a, b) function.",
    workspace_tree=[],
    active_files={},
    iteration=1,
    latest_error=None
)

# 2. Invoke the LLM
llm = CoderLLM()
action = llm.invoke(state)

print("\n--- LLM OUTPUT ---")
print("Thought:", action.thought)
print("Action:", action.action)
print("File:", action.file_path)
print("Content:\n", action.content)

# 3. Test the Error Fix Context
print("\n--- SIMULATING ERROR FIX ---")
state.workspace_tree = ["math.py"]
state.active_files = {"math.py": action.content}
state.latest_error = StructuredError(
    error_type="SyntaxError",
    message="invalid syntax",
    file="math.py",
    line=2,
    traceback="File 'math.py', line 2\n  return a + \n            ^"
)
state.plan_summary = "Fix the syntax error."

action2 = llm.invoke(state)
print("\n--- LLM OUTPUT 2 ---")
print("Thought:", action2.thought)
print("Action:", action2.action)
print("Content:\n", action2.content)