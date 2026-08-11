import uuid
from src.graph.state import GraphState
from src.graph.workflow import build_workflow
from dotenv import load_dotenv

load_dotenv()

def main():
    task_id = str(uuid.uuid4())
    user_request = "Build a simple todo app in python "
    
    print(f"🚀 Starting Coding Assistant (Task: {task_id})")
    print(f"📝 Request: {user_request}\n")

    # 1. Initialize Global State
    initial_state: GraphState = {
        "task_id": task_id,
        "user_request": user_request,
        "plan_summary": None,
        "coder_status": None,
        "test_results": None,
        "reviewer_status": None,
        "reviewer_feedback": None,
        "test_iterations": 0,  
        "replan_count": 0,
        "latest_error_signature": None,
        "previous_error_signature": None,
        "same_error_count": 0 
    }

    # 2. Compile and Run the Graph
    app = build_workflow()
    
    # The LangGraph `.invoke` runs the entire DAG sequentially
    final_state = app.invoke(initial_state)

    print("\n🏁 Workflow Complete!")
    print(f"Planner Output Length: {len(final_state['plan_summary'])} chars")
    print(f"plan_summary: {final_state['plan_summary'][:400]}...")  # Print first 200 chars of plan
    print(f"Coder Final Status: {final_state['coder_status']}")
    print(f"Test Results: {final_state['test_results']}")
    print(f"Reviewer Status: {final_state['reviewer_status']}")
    print(f"Artifacts exported to: artifacts/{task_id}/")

if __name__ == "__main__":
    main()