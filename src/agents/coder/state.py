from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class StructuredError(BaseModel):
    error_type: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    traceback: str

class CoderAction(BaseModel):
    thought: str = Field(description="Briefly explain your reasoning.")
    action: Literal["write", "edit", "delete", "finish"] = Field(description="The operation to perform.")
    file_path: Optional[str] = Field(default="", description="Path to the file.")
    content: Optional[str] = Field(default="", description="The FULL updated content.")
    verify_command: Optional[str] = Field(default="", description="The command to run to verify this change.")

class TraceStep(BaseModel):
    """A deterministic record of a single iteration loop."""
    iteration: int
    action_taken: CoderAction
    verification_success: bool
    resulting_error: Optional[StructuredError] = None

class CoderState(BaseModel):
    task_id: str
    plan_summary: str
    workspace_tree: List[str] = Field(default_factory=list)
    active_files: Dict[str, str] = Field(default_factory=dict)
    iteration: int = 0
    latest_error: Optional[StructuredError] = None
    status: Literal["IN_PROGRESS", "SUCCESS", "MAX_ITERATIONS", "FAILED"] = "IN_PROGRESS"
    
    # --- NEW: Execution Trace ---
    execution_trace: List[TraceStep] = Field(default_factory=list)