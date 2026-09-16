import os
import json
import base64
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

class ScheduleEvent(BaseModel):
    event_name: str = Field(description="The name of the class or event (e.g. CP 386 - Operating Systems)")
    day_of_week: str = Field(description="The day of the week, must be one of: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday")
    time: str = Field(description="The time range in HH:MM-HH:MM (24-hour) format")

class ParsedSchedule(BaseModel):
    events: List[ScheduleEvent] = Field(description="A list of extracted events from the schedule")

def extract_schedule_from_image(image_path: str) -> Dict[str, Any]:
    """
    Reads an image of a schedule, sends it to Gemini Vision, and extracts it into the fixed_schedule JSON format.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Read image and encode to base64
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    
    # Determine MIME type (simple heuristic)
    mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
    image_url = f"data:{mime_type};base64,{encoded_string}"

    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
    
    parser = JsonOutputParser(pydantic_object=ParsedSchedule)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert OCR and schedule parser. Extract the user's fixed class/event schedule from the provided image. Pay close attention to the column headers (days) and row labels (times). Convert all times to 24-hour HH:MM-HH:MM format. Return ONLY valid JSON matching the schema."),
        ("user", [
            {"type": "text", "text": "Extract the schedule events from this image. \n{format_instructions}"},
            {"type": "image_url", "image_url": {"url": "{image_data}"}}
        ])
    ])
    
    chain = prompt | llm | parser
    
    print(f"    [Vision Parser] Processing image {os.path.basename(image_path)}...")
    try:
        result = chain.invoke({
            "format_instructions": parser.get_format_instructions(),
            "image_data": image_url
        })
        
        # Handle cases where LLM returns a list directly
        if isinstance(result, list):
            result = {"events": result}
            
        print(f"    [Vision Parser] Successfully extracted {len(result.get('events', []))} events.")
        return result
    except Exception as e:
        print(f"    [Vision Parser Error] Failed to parse image: {e}")
        return {"events": []}
