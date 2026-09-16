from typing import List, Dict, Any, TypedDict
from pydantic import BaseModel, Field

class TaskIntent(BaseModel):
    task_name: str = Field(description="Name of the task to be scheduled")
    quantity: int = Field(description="Number of times this task should be scheduled", default=1)
    duration_minutes: int = Field(description="Estimated duration of the task in minutes (e.g., 120 for 2 hours)", default=60)
    special_requirements: str = Field(description="Any special constraints or requirements mentioned by the user for this task", default="")

class ParsedIntent(BaseModel):
    tasks: List[TaskIntent] = Field(description="List of tasks extracted from the user's input")
    general_timeframe: str = Field(description="The general timeframe mentioned (e.g., 'next week', 'this weekend')", default="next week")

class AgentState(TypedDict):
    """Global state for the LangGraph agent."""
    user_intent: str
    parsed_tasks: List[Dict[str, Any]]
    general_timeframe: str
    schedule: str
    constraints: Dict[str, Any]
    evaluation: str
