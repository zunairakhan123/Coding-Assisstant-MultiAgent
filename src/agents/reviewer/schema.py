from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class SimulationStep(BaseModel):
    command: str = Field(
        description="Shell command to execute in the container (e.g., 'python calculator.py add 5 3')."
    )
    expected_exit_code: int = Field(
        default=0,
        description="Expected exit code. Use 0 for valid commands, and 1 (or specific non-zero code) for expected error handling tests."
    )
    expected_behavior: str = Field(
        description="What stdout/stderr output indicates success for this step."
    )

class ReviewerAuditOutput(BaseModel):
    architecture_analysis: str = Field(
        description="Evaluation of code structure, modularity, and security."
    )
    simulation_steps: List[SimulationStep] = Field(
        default_factory=list,
        description="A sequence of live shell commands to functionally test the application."
    )
    status: Literal["PASS", "REVISE_CODER", "REVISE_PLANNER"] = Field(
        description="PASS if implementation and architecture are solid. REVISE_CODER for bugs. REVISE_PLANNER for core design flaws."
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Actionable feedback if status is not PASS."
    )