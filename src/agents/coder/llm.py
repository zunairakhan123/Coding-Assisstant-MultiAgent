from langchain_openai import ChatOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import httpx
from src.core.config import settings
from src.core.logger import logger
from src.agents.coder.prompts import coder_prompt
from src.agents.coder.state import CoderState, CoderAction

class CoderLLM:
    """Encapsulates the LangChain pipeline for the Coder agent."""
    
    def __init__(self):
        # Point to the custom company endpoint
        self.model = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            timeout=httpx.Timeout(45.0), # Prevent hanging forever
        ).with_structured_output(CoderAction)
        
        self.chain = coder_prompt | self.model
        self.log = logger.bind(component="coder_llm")

   # Enterprise retry logic: Retry on network/API errors, wait 2s, 4s, 8s, up to 3 times.
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    def invoke(self, state: CoderState) -> CoderAction:
        """Executes the LLM pipeline with the current state."""
        self.log.info("invoking_llm", iteration=state.iteration, model=settings.LLM_MODEL)
        
        # Format variables safely
        active_files_str = "\n\n".join(
            [f"--- {filepath} ---\n{content}" for filepath, content in state.active_files.items()]
        ) if state.active_files else "No active files in context yet."
        
        error_str = state.latest_error.model_dump_json(indent=2) if state.latest_error else "None. Previous execution succeeded or has not run yet."
        tree_str = "\n".join(state.workspace_tree) if state.workspace_tree else "(Empty Workspace)"

        try:
            action: CoderAction = self.chain.invoke({
                "plan_summary": state.plan_summary,
                "workspace_tree": tree_str,
                "active_files": active_files_str,
                "latest_error": error_str
            })
            
            self.log.info("llm_response_received", action=action.action, target=action.file_path)
            return action
            
        except Exception as e:
            self.log.error("llm_invocation_failed", error=str(e))
            raise