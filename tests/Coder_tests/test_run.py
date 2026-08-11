import uuid
from src.sandbox.manager import SandboxManager

task_id = str(uuid.uuid4())
manager = SandboxManager(task_id=task_id)

try:
    manager.start()
    
    # 1. Test normal execution
    res1 = manager.execute("echo 'Hello World'")
    print("Normal Run:", res1.model_dump_json(indent=2))
    
    # 2. Test timeout execution
    res2 = manager.execute("sleep 15", timeout=2)
    print("Timeout Run:", res2.model_dump_json(indent=2))
    
    # 3. Test error execution
    res3 = manager.execute("python -c '1/0'")
    print("Error Run:", res3.model_dump_json(indent=2))

finally:
    manager.cleanup()