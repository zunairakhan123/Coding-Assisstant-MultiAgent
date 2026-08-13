import base64
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from src.core.config import settings
from src.core.logger import logger
from src.sandbox.manager import SandboxManager
from src.agents.coder.context import ContextEngine
from src.agents.coder.harness import Harness # IMPORT HARNESS
from src.agents.tester.prompts import tester_prompt
from src.graph.state import GraphState
from src.agents.tester.parser import TestErrorParser

class TesterOutput(BaseModel):
    happy_path_plan: str = Field(
        description="A detailed list of standard, expected scenarios to test."
    )
    edge_case_plan: str = Field(
        description="A detailed list of boundary conditions, invalid inputs, and exception handling scenarios."
    )
    test_file_path: str = Field(
        description="The path where the tests should be saved (e.g., 'test_main.py')."
    )
    test_code: str = Field(
        description="The full pytest code. Must group tests into TestHappyPath and TestEdgeCases classes."
    )
    verify_command: str = Field(
        description="Command to run the tests, strictly using the module flag (e.g., 'python -m pytest test_main.py -v')."
    )

class TesterNode:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.sandbox = SandboxManager(task_id)
        
        # Connect to the EXISTING container the Coder provisioned
        self.sandbox.connect() 
        
        self.context = ContextEngine(self.sandbox)
        self.harness = Harness(self.sandbox) # Use harness for security
        
        self.model = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        ).with_structured_output(TesterOutput)
        
        self.chain = tester_prompt | self.model
        self.log = logger.bind(component="tester_node", task_id=task_id)

    def invoke(self, state: GraphState) -> dict:
        self.log.info("starting_tester", test_iteration=state.get("test_iterations", 0))
        
        # 1. Fetch workspace context
        tree = self.context.get_directory_tree()
        active_files = {f: self.context.read_file(f) for f in tree if f.endswith('.py') or f.endswith('.txt')}
        active_files_str = "\n".join([f"--- {f} ---\n{c}" for f, c in active_files.items()])

        # 2. Generate QA Strategy & Tests
        output: TesterOutput = self.chain.invoke({
            "plan_summary": state["plan_summary"],
            "active_files": active_files_str
        })
        
        # Log the explicit testing strategies for observability
        self.log.info("qa_strategy_generated", 
                      happy_paths=output.happy_path_plan, 
                      edge_cases=output.edge_case_plan)
        
        # 3. Inject and Run tests
        encoded_content = base64.b64encode(output.test_code.encode('utf-8')).decode('utf-8')
        self.sandbox.execute(f"echo '{encoded_content}' | base64 -d > '{output.test_file_path}'")
        self.sandbox.execute("pip install pytest httpx")
        
        self.harness.validate_command(output.verify_command)
        res = self.sandbox.execute(output.verify_command)
        
        raw_out = res.stdout if res.status == "success" else res.stderr or res.stdout
        compact_out = raw_out[-2000:] if len(raw_out) > 2000 else raw_out
        self.log.info("tests_completed", exit_code=res.exit_code)
        
        # 4. EXPORT WORKSPACE 
        import os
        export_path = os.path.join(os.getcwd(), "artifacts", self.task_id)
        self.sandbox.export_workspace(export_path)

        # 5. STATE MUTATION 
        current_signature = None
        if res.exit_code != 0:
            signature = TestErrorParser.parse_pytest_output(raw_out)
            current_signature = signature.fingerprint_key
            
        previous_signature = state.get("latest_error_signature")
        same_error_count = state.get("same_error_count", 0)
        
        if res.exit_code == 0:
            same_error_count = 0
        elif current_signature and current_signature == previous_signature:
            same_error_count += 1
            self.log.warning("conceptual_error_repeated", count=same_error_count)
        else:
            same_error_count = 1
            self.log.info("new_conceptual_error_detected", signature=current_signature)

        return {
            "test_results": f"Exit Code: {res.exit_code}\n\nPytest Output:\n{compact_out}",
            "test_iterations": state.get("test_iterations", 0) + 1,
            "latest_error_signature": current_signature,
            "previous_error_signature": previous_signature,
            "same_error_count": same_error_count
        }