import json
import urllib.parse
import re
import requests
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import Dict, List

class SkateTimes(BaseModel):
    available_times: Dict[str, List[str]] = Field(description="Dictionary mapping day of week (e.g., 'Monday', 'Tuesday') to a list of available time slots (e.g., ['14:00-16:00']).")

def fetch_activenet_schedule(url: str, format_with_llm: bool = True, activity_filter: str = "", date_start: str = "", date_end: str = "") -> tuple[dict, str]:
    print(f"    [ActiveNet API] Parsing URL: {url}")
    parsed = urllib.parse.urlparse(url)
    
    # Extract org_name from path e.g. /activewaterloo/activity/search -> activewaterloo
    match = re.search(r'/([^/]+)/activity/search', parsed.path)
    org_name = match.group(1) if match else "activewaterloo"
    
    # Extract query params
    qs = urllib.parse.parse_qs(parsed.query)
    category_ids = qs.get("activity_category_ids", [])
    keyword = activity_filter if activity_filter else qs.get("activity_keyword", [""])[0]
    
    # Use explicit dates provided by frontend
    date_after_str = date_start
    date_before_str = date_end
    
    api_url = f"https://anc.ca.apm.activecommunities.com/{org_name}/rest/activities/list?locale=en-US"
    
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json;charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://anc.ca.apm.activecommunities.com",
        "page_info": '{"order_by":"","page_number":1,"total_records_per_page":100}'
    }
    
    payload = {
        "activity_search_pattern": {
            "skills": [], "time_after_str": "", "days_of_week": None, "activity_select_param": 2, 
            "center_ids": [], "time_before_str": "", "open_spots": None, "activity_id": None, 
            "activity_category_ids": category_ids, "date_before": date_before_str, "min_age": None, "date_after": date_after_str, 
            "activity_type_ids": [], "site_ids": [], "for_map": False, "geographic_area_ids": [], 
            "season_ids": [], "activity_department_ids": [], "activity_other_category_ids": [], 
            "child_season_ids": [], "activity_keyword": keyword, "instructor_ids": [], "max_age": None, 
            "custom_price_from": "", "custom_price_to": ""
        },
        "activity_transfer_pattern": {}
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            error_msg = f"[ActiveNet Error] API returned status {response.status_code}: {response.text[:200]}"
            print(f"    {error_msg}")
            return {}, error_msg
            
        data = response.json()
        items = data.get("body", {}).get("activity_items", [])
        print(f"    [ActiveNet API] Successfully fetched {len(items)} activities.")
        
        if not items:
            return {}, "[ActiveNet API] No activities found for this query."
            
        # Extract clean metadata
        clean_schedules = []
        for item in items:
            clean_schedules.append({
                "name": item.get("name"),
                "date_range": item.get("date_range"),
                "time_range": item.get("time_range"),
                "days_of_week": item.get("days_of_week"),
                "location": item.get("location", {}).get("label", "")
            })
            
        if not format_with_llm:
            # Manual python formatting for the "Free / No API Key" feature
            print(f"    [ActiveNet API] Manually formatting {len(clean_schedules)} items...")
            manual_times = {}
            day_map = {
                "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
                "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"
            }
            for item in clean_schedules:
                day_abbr = item["days_of_week"]
                # Default to the abbreviation if mapping fails, or Unknown
                full_day = day_map.get(day_abbr[:3] if day_abbr else "", day_abbr or "Unknown")
                
                time_str = item["time_range"]
                name = item["name"]
                
                # We can store it as "Name: Time" so the UI displays both nicely, prepending the city
                location_label = item.get("location", "")
                loc_str = f" @ {location_label}" if location_label else ""
                entry = f"[{org_name}] {name}{loc_str}: {time_str}"
                
                if full_day not in manual_times:
                    manual_times[full_day] = []
                manual_times[full_day].append(entry)
                
            debug_msg = f"[ActiveNet Success] Fetched {len(items)} items using JSON API (No LLM).\nFormatted Result: {json.dumps(manual_times, indent=2)}"
            return manual_times, debug_msg
            
        # Format via LLM
        print(f"    [ActiveNet API] Formatting {len(clean_schedules)} items with Gemini...")
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert data formatter. You will be provided with a JSON list of ice skating sessions containing their names, days, and times (e.g., 'Noon - 12:50 PM'). Convert these into a unified JSON object mapping full day names (e.g., 'Monday') to a list of standard 24-hour time ranges (e.g., ['12:00-12:50']). Ignore specific dates, just look at 'days_of_week' and 'time_range'."),
            ("human", "Raw JSON Sessions:\n{sessions}")
        ])
        chain = prompt | llm | JsonOutputParser(pydantic_object=SkateTimes)
        result = chain.invoke({"sessions": json.dumps(clean_schedules, indent=2)})
        
        final_times = result.get("available_times", result)
        debug_msg = f"[ActiveNet Success] Fetched {len(items)} items using JSON API.\nFormatted Result: {json.dumps(final_times, indent=2)}"
        return final_times, debug_msg
        
    except Exception as e:
        error_msg = f"[ActiveNet Error] Failed to fetch or parse API: {e}"
        print(f"    {error_msg}")
        return {}, error_msg
        
if __name__ == "__main__":
    url = "https://anc.ca.apm.activecommunities.com/activewaterloo/activity/search?onlineSiteId=0&activity_select_param=2&activity_category_ids=35&viewMode=list"
    times, log = fetch_activenet_schedule(url)
    print("FINAL TIMES:")
    print(times)
