import os
import json
from langgraph.graph import StateGraph, END
from src.graph.state import GraphState
from src.agents.planner.llm import PlannerAgent
from src.agents.coder.controller import CoderController
from src.agents.tester.node import TesterNode
from src.sandbox.manager import SandboxManager
from src.core.logger import logger
from src.agents.reviewer.node import ReviewerNode

def run_planner_node(state: GraphState):
    logger.info("routing_to_node", node="planner", task_id=state["task_id"])
    
    request = state["user_request"]
    
    # REPLANNING LOGIC: Check if we were routed here from the Reviewer OR the Tester
    if state.get("reviewer_status") == "REVISE":
        logger.warning("replanning_from_reviewer_rejection")
        request += f"\n\n[URGENT: The Principal Reviewer rejected the previous implementation. Feedback:\n{state.get('reviewer_feedback')}\n\nPlease generate a NEW plan that addresses this feedback.]"
        state["replan_count"] = state.get("replan_count", 0) + 1
        
    elif state.get("test_iterations", 0) >= 3 and state.get("test_results"):
        logger.warning("replanning_triggered_by_tests", replan_count=state.get("replan_count", 0) + 1)
        request += f"\n\n[URGENT: Your previous plan failed after 3 coding attempts. Test failures:\n{state['test_results']}\n\nPlease analyze why the previous approach failed and generate a completely NEW architectural plan.]"
        
        # Reset test_iterations for the new plan, increment replan_count
        state["test_iterations"] = 0
        state["replan_count"] = state.get("replan_count", 0) + 1

    # Temporarily override the state's user_request just for the Planner prompt
    temp_state = state.copy()
    temp_state["user_request"] = request
    
    planner = PlannerAgent()
    output = planner.invoke(temp_state)
    
    return {
        "plan_summary": output["plan_summary"],
        "test_iterations": 0,       # Reset
        "same_error_count": 0,      # Reset
        "latest_error_signature": None, # Reset
        "replan_count": state.get("replan_count", 0),
        "reviewer_status": None,
        "reviewer_feedback": None
    }

def run_coder_node(state: GraphState):
    logger.info("routing_to_node", node="coder", task_id=state["task_id"])
    
    plan = state["plan_summary"]
    if state.get("test_results") and "Exit Code: 0" not in state["test_results"]:
        plan += f"\n\n### URGENT: FIX FAILING TESTS\n{state['test_results']}"

    controller = CoderController(task_id=state["task_id"], plan_summary=plan)
    final_coder_state = controller.run()
    return {"coder_status": final_coder_state.status}

def run_tester_node(state: GraphState):
    logger.info("routing_to_node", node="tester", task_id=state["task_id"])
    tester = TesterNode(state["task_id"])
    return tester.invoke(state)

def run_reviewer_node(state: GraphState):
    """Executes the final Reviewer gatekeeper."""
    logger.info("routing_to_node", node="reviewer", task_id=state["task_id"])
    reviewer = ReviewerNode(state["task_id"])
    return reviewer.invoke(state)

def run_cleanup_node(state: GraphState):
    """Saves the Global Workflow State and destroys the sandbox."""
    logger.info("routing_to_node", node="cleanup", task_id=state["task_id"])
    
    # 1. EXPORT GLOBAL WORKFLOW STATE
    export_path = os.path.join(os.getcwd(), "artifacts", state["task_id"])
    os.makedirs(export_path, exist_ok=True)
    
    workflow_file = os.path.join(export_path, "workflow_state.json")
    try:
        with open(workflow_file, "w") as f:
            json.dump(state, f, indent=2)
        logger.info("workflow_state_exported", path=workflow_file)
    except Exception as e:
        logger.error("workflow_export_failed", error=str(e))
        
    # 2. DESTROY SANDBOX
    sandbox = SandboxManager(state["task_id"])
    sandbox.cleanup()
    return {}

def route_after_tester(state: GraphState) -> str:
    """Read-only edge router."""
    results = state.get("test_results", "")
    replan_count = state.get("replan_count", 0)
    same_error_count = state.get("same_error_count", 0)
    
    if "Exit Code: 0" in results:
        logger.info("tests_passed_routing_to_reviewer")
        return "reviewer" 
        
    if same_error_count >= 3:
        if replan_count >= 2:
            logger.error("max_replans_reached_aborting")
            return "cleanup"
        else:
            logger.warning("stuck_on_same_conceptual_error_routing_to_planner")
            return "planner"
    else:
        logger.info("routing_back_to_coder_for_correction")
        return "coder"

def route_after_reviewer(state: GraphState) -> str:
    """Decides if the architecture is approved or rejected."""
    status = state.get("reviewer_status")
    replan_count = state.get("replan_count", 0)
    
    if status == "PASS":
        logger.info("reviewer_passed_routing_to_cleanup")
        return "cleanup"
    else:
        if replan_count >= 2:
            logger.error("max_replans_reached_from_reviewer_aborting")
            return "cleanup"
        else:
            logger.warning("reviewer_rejected_routing_to_planner")
            return "planner"

def build_workflow():
    workflow = StateGraph(GraphState)

    workflow.add_node("planner", run_planner_node)
    workflow.add_node("coder", run_coder_node)
    workflow.add_node("tester", run_tester_node)
    workflow.add_node("reviewer", run_reviewer_node)
    workflow.add_node("cleanup", run_cleanup_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "coder")
    workflow.add_edge("coder", "tester")
    
    # Tester Routing
    workflow.add_conditional_edges(
        "tester",
        route_after_tester,
        {
            "coder": "coder",       #loop back to coder if tests fail but plan is okay
            "planner": "planner",   #loop back to planner if tests fail and plan is flawed
            "reviewer": "reviewer", # New Reviewer Path
            "cleanup": "cleanup"  
        }
    )
    
    # Reviewer Routing
    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "planner": "planner",
            "cleanup": "cleanup"
        }
    )
    
    workflow.add_edge("cleanup", END)

    return workflow.compile()