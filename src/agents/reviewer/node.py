import os
from src.sandbox.manager import SandboxManager
from src.agents.coder.context import ContextEngine
from src.agents.coder.harness import Harness
from src.agents.reviewer.schema import ReviewerAuditOutput
from src.agents.reviewer.prompts import reviewer_prompt
from src.core.config import settings
from src.core.logger import logger
from langchain_openai import ChatOpenAI

class ReviewerNode:
    """Principal Engineer node executing static code audits and live functional simulations."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        # Connect to existing sandbox merely to read the final files
        self.sandbox = SandboxManager(task_id)
        self.sandbox.connect()
        self.context = ContextEngine(self.sandbox)
        self.harness = Harness(self.sandbox)
        self.log = logger.bind(component="reviewer_node", task_id=task_id)
        
        llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0
        )
        self.chain = reviewer_prompt | llm.with_structured_output(ReviewerAuditOutput)

    def invoke(self, state: dict) -> dict:
        self.log.info("starting_reviewer_audit")

        # 1. Gather active workspace context
        tree = self.context.get_directory_tree()
        active_files = {f: self.context.read_file(f) for f in tree if f.endswith('.py') or f.endswith('.txt') or f.endswith('.json')}
        active_files_str = "\n".join([f"--- {f} ---\n{c}" for f, c in active_files.items()])

        # 2. Invoke Reviewer LLM for Analysis and Simulation Plan
        audit_output: ReviewerAuditOutput = self.chain.invoke({
            "plan_summary": state.get("plan_summary", ""),
            "active_files": active_files_str
        })

        self.log.info("static_audit_complete", status=audit_output.status)

        #3. Execute Live Functional Simulation in Container
        simulation_failures = []
        for step in audit_output.simulation_steps:
            self.log.info(
                "executing_simulation_step", 
                command=step.command, 
                expected_exit_code=step.expected_exit_code
            )
            try:
                res = self.sandbox.execute(step.command)
                output_text = res.stdout if res.stdout else res.stderr
                
                # FIX: Check against the step's expected_exit_code instead of hardcoding != 0
                if res.exit_code != step.expected_exit_code:
                    self.log.warning(
                        "simulation_step_failed", 
                        command=step.command, 
                        actual_exit_code=res.exit_code,
                        expected_exit_code=step.expected_exit_code
                    )
                    simulation_failures.append(
                        f"Command '{step.command}' exited with code {res.exit_code}, "
                        f"but expected exit code {step.expected_exit_code}.\nOutput: {output_text}"
                    )
                else:
                    self.log.info(
                        "simulation_step_passed", 
                        command=step.command, 
                        output=output_text[:200]
                    )
            except Exception as e:
                self.log.error("simulation_step_error", command=step.command, error=str(e))
                simulation_failures.append(f"Command '{step.command}' raised exception: {str(e)}")

        # 4. Final Verdict Adjustment based on Live Simulation Results
        final_status = audit_output.status
        final_feedback = audit_output.feedback or ""

        if simulation_failures:
            final_status = "REVISE"
            failures_str = "\n\n".join(simulation_failures)
            final_feedback = (
                f"Static analysis feedback: {final_feedback}\n\n"
                f"CRITICAL: Live functional simulation failed on container execution:\n{failures_str}"
            )
            self.log.warning("reviewer_overridden_to_revise_due_to_simulation_failures")

        return {
            "reviewer_status": final_status,
            "reviewer_feedback": final_feedback
        }