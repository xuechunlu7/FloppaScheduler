import os
import json
from playwright.sync_api import sync_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict

class SkateTimes(BaseModel):
    available_times: Dict[str, List[str]] = Field(description="Dictionary mapping day of week (e.g., 'Monday', 'Tuesday') to a list of available time slots (e.g., ['14:00-16:00']). If you cannot find specific days, provide a general 'weekday' and 'weekend' schedule if available.")

def parse_ice_rink_schedule(content_text: str) -> tuple[dict, str]:
    try:
        # Use Gemini to intelligently parse the unstructured text into a schedule
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert data extractor. Extract the Adult skate/ice rink availability schedule from the raw webpage text provided. Output a JSON object mapping days of the week to lists of time slots in HH:MM-HH:MM (24-hour) format. If exact dates are provided, convert them to days of the week. Return ONLY valid JSON matching the schema."),
            ("human", "Raw webpage text:\n{text}")
        ])
        
        chain = prompt | llm | JsonOutputParser(pydantic_object=SkateTimes)
        # Limit text size to avoid massive prompts if page is huge
        result = chain.invoke({"text": content_text[:30000]}) 
        
        print(f"    [Parser] LLM parsed times: {result}")
        # Sometimes the LLM returns the dict directly instead of nesting it
        final_times = result["available_times"] if "available_times" in result else result
        debug_msg = f"[Parser Success] Parsed {len(content_text)} chars of manual text. Preview:\n{content_text[:500]}..."
        return final_times, debug_msg
        
    except Exception as e:
        print(f"    [Parser Error] Failed to parse manual times: {e}")
        print("    [Parser] Returning empty schedule to prevent hallucination.")
        debug_msg = f"[Parser Error] {e}\nRaw Content:\n{content_text[:500]}..."
        return {}, debug_msg

def fetch_ice_rink_schedule(url: str) -> tuple[dict, str]:
        
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # ActiveNet can be slow, wait for networkidle
            page.goto(url, wait_until="load", timeout=20000)
            
            # Wait 10 seconds for React to fetch from API and render the list
            page.wait_for_timeout(10000)
            
            # Extract the visible text of the body
            content_text = page.locator("body").inner_text()
            browser.close()
            
        print("    [Scraper] Successfully extracted raw text from page.")
        return parse_ice_rink_schedule(content_text)

if __name__ == "__main__":
    url = "https://anc.ca.apm.activecommunities.com/activewaterloo/activity/search?onlineSiteId=0&activity_select_param=2&activity_category_ids=35&viewMode=list"
    times = fetch_ice_rink_schedule(url)
    print(json.dumps(times, indent=2))
