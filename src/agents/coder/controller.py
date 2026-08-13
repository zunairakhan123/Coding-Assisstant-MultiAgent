import os
import json
from src.sandbox.manager import SandboxManager
from src.agents.coder.state import CoderState, TraceStep
from src.agents.coder.context import ContextEngine
from src.agents.coder.harness import Harness
from src.agents.coder.llm import CoderLLM
from src.agents.coder.parser import ErrorParser
from src.core.config import settings
from src.core.logger import logger

class CoderController:
    """The deterministic orchestration loop for the Coder agent."""
    
    def __init__(self, task_id: str, plan_summary: str):
        self.state = CoderState(task_id=task_id, plan_summary=plan_summary)
        self.sandbox = SandboxManager(task_id=task_id)
        self.context = ContextEngine(self.sandbox)
        self.harness = Harness(self.sandbox)
        self.llm = CoderLLM()
        self.log = logger.bind(component="coder_controller", task_id=task_id)

    def run(self) -> CoderState:
        try:
            self.sandbox.start()
            
            while self.state.iteration < settings.MAX_ITERATIONS:
                self.state.iteration += 1
                self.log.info("starting_iteration", iteration=self.state.iteration)
                
                self.state.workspace_tree = self.context.get_directory_tree()
                
                try:
                    action = self.llm.invoke(self.state)
                except Exception as e:
                    self.log.error("llm_fatal_error", error=str(e))
                    self.state.status = "FAILED"
                    self.state.latest_error = ErrorParser.parse(str(e), "SYSTEM")
                    break

                verification_success = True
                step_error = None

                if action.action == "finish":
                    self.log.info("coder_finished_successfully")
                    self.state.status = "SUCCESS"
                    self.state.execution_trace.append(TraceStep(
                        iteration=self.state.iteration,
                        action_taken=action,
                        verification_success=True
                    ))
                    break
                    
                if action.action in ["write", "edit", "delete"]:
                    # --- NEW INNER TRY/EXCEPT BLOCK ---
                    try:
                        self.harness.apply_action(action)
                        
                        # Dynamically sync container changes to the tracking state
                        if action.action == "delete":
                            self.state.active_files.pop(action.file_path, None)
                        else:
                            self.state.active_files[action.file_path] = self.context.read_file(action.file_path)
                            
                    except Exception as harness_err:
                        # If the edit/write fails, tell the LLM and skip verification for this round
                        self.log.warning("harness_action_failed", error=str(harness_err))
                        self.state.latest_error = ErrorParser.parse(str(harness_err), action.file_path)
                        
                        self.state.execution_trace.append(TraceStep(
                            iteration=self.state.iteration,
                            action_taken=action,
                            verification_success=False,
                            resulting_error=self.state.latest_error
                        ))
                        continue # Skip verify_command and go to the next iteration to let the LLM fix it
                    # ----------------------------------
                    
                    if action.verify_command and self.harness.validate_command(action.verify_command):
                        self.log.info("verifying_execution", command=action.verify_command)
                        res = self.sandbox.execute(action.verify_command)
                        
                        if res.status == "success":
                            self.log.info("verification_passed", command=action.verify_command)
                            self.state.latest_error = None
                        else:
                            self.log.warning("verification_failed", command=action.verify_command)
                            verification_success = False
                            step_error = ErrorParser.parse(res.stderr or res.stdout, action.file_path)
                            self.state.latest_error = step_error
                    else:
                        self.log.warning("no_verify_command_provided_or_invalid")
                
                self.state.execution_trace.append(TraceStep(
                    iteration=self.state.iteration,
                    action_taken=action,
                    verification_success=verification_success,
                    resulting_error=step_error
                ))
                        
            if self.state.iteration >= settings.MAX_ITERATIONS and self.state.status != "SUCCESS":
                self.state.status = "MAX_ITERATIONS"
                self.log.error("max_iterations_reached")
                
        except Exception as e:
            self.state.status = "FAILED"
            self.log.error("controller_failed", error=str(e), exc_info=True)
            
        finally:
            export_path = os.path.join(os.getcwd(), "artifacts", self.state.task_id)
            self.sandbox.export_workspace(export_path)
            
            trace_file_path = os.path.join(export_path, "execution_trace.json")
            try:
                with open(trace_file_path, "w") as f:
                    json.dump(
                        [step.model_dump() for step in self.state.execution_trace], 
                        f, 
                        indent=2
                    )
                self.log.info("trace_exported", path=trace_file_path)
            except Exception as e:
                self.log.error("trace_export_failed", error=str(e))
                
        return self.state