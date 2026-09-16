from typing import TypedDict, Annotated
import json
import os
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.agent.state import AgentState, ParsedIntent
from src.utils.scraper import fetch_ice_rink_schedule
from pydantic import BaseModel, Field
from typing import List

class FinalScheduleEvent(BaseModel):
    title: str = Field(description="The name of the event or task")
    day_of_week: str = Field(description="The day of the week, e.g., Monday, Tuesday")
    start_time: str = Field(description="Start time in HH:MM (24-hour format)")
    end_time: str = Field(description="End time in HH:MM (24-hour format)")
    event_type: str = Field(description="Must be one of: 'fixed' (for existing classes/events), 'additional' (for tasks scheduled by AI), 'recovery' (for recovery blocks)")

class FinalSchedule(BaseModel):
    events: List[FinalScheduleEvent] = Field(description="The list of all scheduled events for the week")

# We use gemini-3.6-flash for complex structured parsing (guaranteed free tier access)
# LLM will be instantiated lazily in each node to allow dynamic API key injection

def parse_intent(state: AgentState):
    print(f"--> Parsing intent: {state['user_intent']}")
    
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    
    # Force the LLM to output according to our Pydantic schema
    structured_llm = llm.with_structured_output(ParsedIntent)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert scheduling assistant. Extract the tasks, their quantities, duration, and any special requirements from the user's intent. Pay attention to implicit durations (e.g. 'half day' might mean 240 mins). Translate tasks to English if necessary for standard processing, or keep original language."),
        ("human", "{intent}")
    ])
    
    chain = prompt | structured_llm
    
    # Call Gemini
    result = chain.invoke({"intent": state["user_intent"]})
    
    # Convert Pydantic models back to dictionaries to store in the graph State
    parsed_tasks = [task.model_dump() for task in result.tasks]
    
    print(f"    [Success] Extracted {len(parsed_tasks)} tasks for timeframe: {result.general_timeframe}")
    for task in parsed_tasks:
        print(f"      - {task['task_name']} (x{task['quantity']}), {task['duration_minutes']} mins. Reqs: {task['special_requirements']}")
        
    return {
        "parsed_tasks": parsed_tasks,
        "general_timeframe": result.general_timeframe,
        "schedule": "Parsing done"
    }

def retrieve_constraints(state: AgentState):
    print("--> Retrieving constraints...")
    try:
        # Support stateless operation: if constraints are provided in state, use them
        if state.get("constraints"):
            constraints = state["constraints"]
            print("    [Success] Used provided constraints from state (Stateless Mode)")
        else:
            with open("data/rules/constraints.json", "r") as f:
                constraints = json.load(f)
                print("    [Success] Loaded static constraints from file")
            
        # Dynamically fetch times for any venue that provides a scrape_url
        if "venues" in constraints:
            for venue_name, venue_info in constraints["venues"].items():
                if "scrape_url" in venue_info and venue_info["scrape_url"]:
                    url = venue_info["scrape_url"]
                    print(f"    [Scraper] Fetching dynamic times for {venue_name}...")
                    dynamic_times = fetch_ice_rink_schedule(url)
                    if dynamic_times is not None:
                        venue_info["open_hours"] = dynamic_times
                        print(f"    [Success] Injected dynamic times for {venue_name}")
                        
    except Exception as e:
        print(f"    [Error] Failed to load constraints: {e}")
    return {"constraints": constraints}

def generate_plan(state: AgentState):
    print("--> Generating plan...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    structured_llm = llm.with_structured_output(FinalSchedule)
    
    ice_rink_times = state.get("constraints", {}).get("venues", {}).get("ice_rink", {}).get("open_hours", {})
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert scheduling assistant. Generate a detailed, logical schedule based on the tasks and constraints. Output a strict JSON matching the schema.\n\nCRITICAL RULES:\n1. ANY task related to skating, ice training, or the ice rink MUST be scheduled STRICTLY within the exact available time slots provided below. Do not invent time slots. IF AVAILABLE ICE RINK TIMES IS EMPTY `{{}}`, YOU MUST ABSOLUTELY NOT SCHEDULE ANY ICE-RELATED TASKS (omit them completely).\n\nAVAILABLE ICE RINK TIMES:\n{ice_rink_times}\n\n2. Schedule the tasks extracted from the user intent around the `fixed_schedule`. \n3. ONLY output the newly scheduled tasks (event_type: 'additional' or 'recovery'). DO NOT include the `fixed_schedule` events in your output; they will be merged automatically later.\n4. If the requested duration exceeds the available slot duration, truncate the task duration to fit exactly within the venue slot (e.g. 50 mins).\n5. Ensure NO OVERLAPS with the `fixed_schedule`."),
        ("human", "Timeframe: {timeframe}\n\nTasks:\n{tasks}\n\nConstraints:\n{constraints}")
    ])
    
    chain = prompt | structured_llm
    
    result = chain.invoke({
        "timeframe": state.get("general_timeframe", ""),
        "tasks": json.dumps(state.get("parsed_tasks", []), indent=2, ensure_ascii=False),
        "constraints": json.dumps(state.get("constraints", {}), indent=2, ensure_ascii=False),
        "ice_rink_times": json.dumps(ice_rink_times, indent=2, ensure_ascii=False)
    })
    
    # Convert back to dict
    schedule = result.model_dump()
    
    # Manually append fixed schedule events to avoid LLM hallucination
    fixed_schedule = state.get("constraints", {}).get("fixed_schedule", {})
    if isinstance(fixed_schedule, list):
        fixed_events = fixed_schedule
    else:
        fixed_events = fixed_schedule.get("events", [])
        
    for f_event in fixed_events:
        time_parts = f_event.get("time", "").split("-")
        start_time = time_parts[0] if len(time_parts) > 0 else ""
        end_time = time_parts[1] if len(time_parts) > 1 else ""
        schedule["events"].append({
            "title": f_event.get("event_name", ""),
            "day_of_week": f_event.get("day_of_week", ""),
            "start_time": start_time,
            "end_time": end_time,
            "event_type": "fixed"
        })
    
    print("    [Success] Plan generated")
    return {"schedule": schedule}

def evaluate_plan(state: AgentState):
    print("--> Evaluating plan for conflicts...")
    
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert scheduling auditor. Review the generated JSON schedule against the provided constraints and tasks. If there are any conflicts, missing tasks, or broken rules, describe them clearly. If everything looks good, just reply 'No conflicts found.'"),
        ("human", "Tasks:\n{tasks}\n\nConstraints:\n{constraints}\n\nGenerated Schedule (JSON):\n{schedule}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    evaluation = chain.invoke({
        "tasks": json.dumps(state.get("parsed_tasks", []), indent=2, ensure_ascii=False),
        "constraints": json.dumps(state.get("constraints", {}), indent=2, ensure_ascii=False),
        "schedule": json.dumps(state.get("schedule", {}), indent=2, ensure_ascii=False)
    })
    
    print("    [Success] Plan evaluated")
    return {"evaluation": evaluation}

# Initialize Graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("parse_intent", parse_intent)
builder.add_node("retrieve_constraints", retrieve_constraints)
builder.add_node("generate_plan", generate_plan)
builder.add_node("evaluate_plan", evaluate_plan)

# Define Edges (linear for now as a skeleton)
builder.add_edge(START, "parse_intent")
builder.add_edge("parse_intent", "retrieve_constraints")
builder.add_edge("retrieve_constraints", "generate_plan")
builder.add_edge("generate_plan", "evaluate_plan")
builder.add_edge("evaluate_plan", END)

# Compile Graph
graph = builder.compile()
