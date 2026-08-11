import uuid
import os
from src.sandbox.manager import SandboxManager
from src.agents.coder.harness import Harness, PatchAction

task_id = str(uuid.uuid4())
manager = SandboxManager(task_id=task_id)
harness = Harness(sandbox=manager)

try:
    manager.start()
    
    # Write a test file
    code = "print('Hello from the exported workspace!')"
    action = PatchAction(action="write", file_path="app/main.py", content=code)
    harness.apply_action(action)
    
    # Define artifact path
    artifact_path = os.path.join(os.getcwd(), "artifacts", task_id)
    
    # EXPORT before cleanup
    manager.export_workspace(artifact_path)
    
    print(f"\n✅ Check your host machine at: {artifact_path}/workspace/app/main.py")

finally:
    manager.cleanup()