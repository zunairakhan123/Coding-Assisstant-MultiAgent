from typing import TypedDict, Optional

class GraphState(TypedDict):
    """The global state routed between LangGraph nodes."""
    task_id: str
    user_request: str
    
    # Populated by the Planner
    plan_summary: Optional[str]
    
    # Populated by the Coder
    coder_status: Optional[str]
    
    # Populated by the Tester/Reviewer later
    test_results: Optional[str]
    reviewer_status: Optional[str]
    reviewer_feedback: Optional[str] # NEW

    # NEW: Tracks the number of times we cycle between Coder and Tester
    test_iterations: int
    replan_count: int # NEW: Tracks how many times we routed back to Planner

    # Exact Error Fingerprinting
    latest_error_signature: Optional[str]
    previous_error_signature: Optional[str]
    same_error_count: int
