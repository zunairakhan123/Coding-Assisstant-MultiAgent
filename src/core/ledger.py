import os
import json
from datetime import datetime
from src.core.logger import logger

class TaskLedger:
    """Manages the global execution history of the coding assistant."""
    
    def __init__(self):
        # Save directly to the root project folder
        self.ledger_path = os.path.join(os.getcwd(), "tasks_ledger.json")

    def record_task(self, state: dict):
        """Appends the final graph state to the global ledger."""
        try:
            # 1. Load existing ledger or start fresh
            if os.path.exists(self.ledger_path):
                with open(self.ledger_path, 'r') as f:
                    try:
                        ledger = json.load(f)
                    except json.JSONDecodeError:
                        ledger = []
            else:
                ledger = []

            # 2. Extract clean metadata for the checkpoint
            task_record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "task_id": state.get("task_id", "unknown"),
                "user_request": state.get("user_request", "unknown"),
                "coder_status": state.get("coder_status", "unknown"),
                "reviewer_status": state.get("reviewer_status", "Not Reached"),
                "test_iterations": state.get("test_iterations", 0),
                "replan_count": state.get("replan_count", 0),
                "artifacts_path": f"artifacts/{state.get('task_id')}/"
            }

            # 3. Append and save atomically
            ledger.append(task_record)
            
            with open(self.ledger_path, 'w') as f:
                json.dump(ledger, f, indent=2)
                
            logger.info("task_recorded_to_global_ledger", path=self.ledger_path)
            
        except Exception as e:
            logger.error("failed_to_write_ledger", error=str(e))