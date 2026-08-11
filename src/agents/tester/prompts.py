from langchain_core.prompts import ChatPromptTemplate

TESTER_SYSTEM_PROMPT = """You are a Senior QA Automation Engineer.
Your job is to write a comprehensive `pytest` test suite for the implementation provided.

### RULES:
1. Analyze the Planner's plan and the current workspace code.
2. Write a file named `test_main.py` (or similar) containing your tests.
3. Use standard libraries like `pytest` and `fastapi.testclient`.
4. Output the exact python test code.
5. Provide a verify_command using the python module flag (e.g. 'python -m pytest test_main.py'). DO NOT use 'pytest' directly.
"""

tester_prompt = ChatPromptTemplate.from_messages([
    ("system", TESTER_SYSTEM_PROMPT),
    ("user", "Plan:\n{plan_summary}\n\nCode Files:\n{active_files}\n\nGenerate the test code and output only the structured JSON.")
])