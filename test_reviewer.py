import os
import base64
from src.sandbox.manager import SandboxManager
from src.agents.reviewer.node import ReviewerNode
from src.core.logger import logger

def run_isolated_reviewer_test():
    task_id = "reviewer-isolation-test-001"
    
    logger.info("1. Provisioning isolated sandbox...")
    sandbox = SandboxManager(task_id)
    sandbox.start()
    
    try:
        # 2. Define a dummy application to test against
        app_code = """
import sys

def main():
    if len(sys.argv) != 4:
        print("Usage: python calculator.py <add/sub> <num1> <num2>")
        sys.exit(1)
        
    operation = sys.argv[1]
    
    try:
        a = float(sys.argv[2])
        b = float(sys.argv[3])
    except ValueError:
        print("Error: Invalid numbers.")
        sys.exit(1)
        
    if operation == "add":
        print(a + b)
    elif operation == "sub":
        print(a - b)
    else:
        print("Error: Unknown operation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
        # 3. Inject the code into the sandbox securely via base64
        logger.info("2. Injecting dummy calculator.py into sandbox...")
        encoded_code = base64.b64encode(app_code.encode('utf-8')).decode('utf-8')
        sandbox.execute(f"echo '{encoded_code}' | base64 -d > calculator.py")
        
        # 4. Create a mock LangGraph state
        mock_state = {
            "task_id": task_id,
            "plan_summary": "TARGET FILES: calculator.py\nPLAN: Create a simple CLI calculator that supports 'add' and 'sub' operations.",
            "replan_count": 0
        }
        
        # 5. Initialize and run the Reviewer Node
        logger.info("3. Invoking Reviewer Node...")
        reviewer = ReviewerNode(task_id)
        
        # Note: If your ReviewerNode expects to connect() instead of start(), 
        # it will successfully latch onto the container we just started above.
        result = reviewer.invoke(mock_state)
        
        # 6. Print the results
        print("\n" + "="*60)
        print(f"🏁 REVIEWER STATUS:   {result.get('reviewer_status')}")
        print("="*60)
        print(f"📝 REVIEWER FEEDBACK:\n{result.get('reviewer_feedback')}")
        print("="*60 + "\n")
        
    finally:
        # 7. Always clean up the container, even if the node crashes
        logger.info("4. Cleaning up sandbox...")
        sandbox.cleanup()

if __name__ == "__main__":
    run_isolated_reviewer_test()