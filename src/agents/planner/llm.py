from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from src.core.config import settings
from src.core.logger import logger
from src.agents.planner.prompts import planner_prompt

class PlannerOutput(BaseModel):
    """The structured output schema for the Planner node."""
    thought: str = Field(description="Architectural reasoning for the plan.")
    files_to_create_or_modify: List[str] = Field(description="List of target files.")
    plan_summary: str = Field(description="A clear, concise, step-by-step implementation plan for the Coder.")

class PlannerAgent:
    """The LangGraph Node implementation for the Planner."""
    
    def __init__(self):
        self.model = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        ).with_structured_output(PlannerOutput)
        
        self.chain = planner_prompt | self.model
        self.log = logger.bind(component="planner_agent")

    def invoke(self, state: dict) -> dict:
        user_request = state.get("user_request")
        self.log.info("generating_plan", request=user_request[:50])
        
        try:
            output: PlannerOutput = self.chain.invoke({
                "user_request": user_request
            })
            
            self.log.info("plan_generated", files=output.files_to_create_or_modify)
            
            final_plan = f"TARGET FILES: {', '.join(output.files_to_create_or_modify)}\n\nPLAN:\n{output.plan_summary}"
            
            # Returns a dict that LangGraph merges into the Global GraphState
            return {"plan_summary": final_plan}
            
        except Exception as e:
            self.log.error("planner_failed", error=str(e))
            raise