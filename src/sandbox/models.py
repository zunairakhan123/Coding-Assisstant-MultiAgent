from pydantic import BaseModel
from typing import Literal

class ExecutionResult(BaseModel):
    status: Literal["success", "error", "timeout"]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str