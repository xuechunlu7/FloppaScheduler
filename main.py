import os
from dotenv import load_dotenv

# Load environment variables FIRST before importing the graph
load_dotenv()

from src.agent.graph import graph

def main():
    print("FloppaSchedule MVP Initialized!")
    
    # Simple check for Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[Warning] GEMINI_API_KEY is not properly set in .env")
    else:
        print("[OK] GEMINI_API_KEY loaded.")

    # Test running the intent parsing node
    print("\n--- Running Agent Workflow ---")
    initial_state = {
        "user_intent": "下周要塞进 3 次每次50分钟的adult skate上冰训练(结束以后要有两个小时的recovery)，完成 4 个 每次3道题目的grind 75的学习时间",
        "schedule": "",
        "parsed_tasks": [],
        "general_timeframe": ""
    }
    result = graph.invoke(initial_state)
    
    print("\n--- Final Generated Schedule ---")
    print("="*50)
    print(result.get("schedule", "No schedule found."))
    print("="*50)
    
    print("\n--- Evaluation Result ---")
    print(result.get("evaluation", "No evaluation found."))
if __name__ == "__main__":
    main()
