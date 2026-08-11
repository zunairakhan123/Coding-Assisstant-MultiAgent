from pydantic import BaseModel, Field
from typing import Literal
from langchain_openai import ChatOpenAI
from src.core.config import settings
from src.core.logger import logger
from src.sandbox.manager import SandboxManager
from src.agents.coder.context import ContextEngine
from src.agents.reviewer.prompts import reviewer_prompt
from src.graph.state import GraphState

class ReviewerOutput(BaseModel):
    thought: str = Field(description="Your step-by-step audit reasoning.")
    status: Literal["PASS", "REVISE"] = Field(description="Final decision.")
    feedback: str = Field(description="Detailed feedback if REVISE, otherwise empty.")

class ReviewerNode:
    def __init__(self, task_id: str):
        self.task_id = task_id
        
        # Connect to existing sandbox merely to read the final files
        self.sandbox = SandboxManager(task_id)
        self.sandbox.connect()
        self.context = ContextEngine(self.sandbox)
        
        self.model = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        ).with_structured_output(ReviewerOutput)
        
        self.chain = reviewer_prompt | self.model
        self.log = logger.bind(component="reviewer_node", task_id=task_id)

    def invoke(self, state: GraphState) -> dict:
        self.log.info("starting_reviewer_audit")
        
        # Fetch current workspace context
        tree = self.context.get_directory_tree()
        active_files = {}
        for file in tree:
            if file.endswith('.py') or file.endswith('.txt'):
                active_files[file] = self.context.read_file(file)
                
        active_files_str = "\n".join([f"--- {f} ---\n{c}" for f, c in active_files.items()])

        # Generate Audit
        output: ReviewerOutput = self.chain.invoke({
            "user_request": state["user_request"],
            "plan_summary": state["plan_summary"],
            "active_files": active_files_str,
            "test_results": state.get("test_results", "No tests run.")
        })
        
        self.log.info("reviewer_audit_complete", status=output.status)
        
        return {
            "reviewer_status": output.status,
            "reviewer_feedback": output.feedback
        }