import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import tempfile
import base64

# Import our existing utilities
from src.agent.graph import graph
from src.utils.vision_parser import extract_schedule_from_image

app = FastAPI(title="FloppaSchedule API")

# Configure CORS for the frontend (Floppa Lab)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to floppalab.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    user_intent: str
    constraints: dict
    gemini_api_key: str

@app.post("/api/parse_image")
async def parse_image(
    file: UploadFile = File(...),
    gemini_api_key: str = Form(...)
):
    """
    Receives an image and a Gemini API key, saves it temporarily, 
    and uses the vision parser to extract the fixed schedule.
    """
    if not gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
        
    os.environ["GEMINI_API_KEY"] = gemini_api_key
    
    try:
        # Save uploaded file to temp file
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            
        # Parse the image
        result = extract_schedule_from_image(temp_path)
        
        # Clean up
        os.unlink(temp_path)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
def generate_schedule(request: GenerateRequest):
    """
    Generates a schedule based on intent and constraints.
    Stateless: constraints and API key are passed from the client.
    """
    if not request.gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
        
    # Set the key in environment for Langchain/GenAI SDK to pick up
    os.environ["GEMINI_API_KEY"] = request.gemini_api_key
    
    try:
        initial_state = {
            "user_intent": request.user_intent,
            "constraints": request.constraints
        }
        
        # Invoke the LangGraph workflow
        result = graph.invoke(initial_state)
        
        return {
            "schedule_plan": result.get("schedule", ""),
            "evaluation": result.get("evaluation", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
