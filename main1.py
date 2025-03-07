import os
from typing import List, Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
from pydantic import BaseModel
import json
from prompt_templates import RESEARCH_QUESTION_PROMPT

app = FastAPI(title="Research Question Generator")

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration for API connection
WEBUI_ENABLED = True
WEBUI_BASE_URL = "https://chat.ivislabs.in/api"
API_KEY = "YOUR_API_KEY"
DEFAULT_MODEL = "gemma2:2b"

class GenerationRequest(BaseModel):
    research_area: str
    literature_findings: str
    num_questions: int = 3
    include_hypotheses: bool = True
    research_type: Optional[str] = "qualitative"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_questions(
    research_area: str = Form(...),
    literature_findings: str = Form(...),
    num_questions: int = Form(3),
    include_hypotheses: bool = Form(True),
    research_type: str = Form("qualitative"),
    model: str = Form(DEFAULT_MODEL)
):
    try:
        # Build the prompt for research question and hypothesis generation
        prompt = RESEARCH_QUESTION_PROMPT.format(
            research_area=research_area,
            literature_findings=literature_findings,
            num_questions=num_questions,
            include_hypotheses="with testable hypotheses" if include_hypotheses else "without hypotheses",
            research_type=research_type
        )
        
        messages = [{"role": "user", "content": prompt}]
        request_payload = {"model": model, "messages": messages}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEBUI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json=request_payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = ""
                if "choices" in result and result["choices"]:
                    generated_text = result["choices"][0].get("message", {}).get("content", "")
                
                # Format output: separate questions and hypotheses
                formatted_text = ""  
                sections = generated_text.split("\n\n")
                for section in sections:
                    if section.lower().startswith("research question"):
                        formatted_text += f'<h2 class="text-green-400 text-xl font-bold">{section}</h2><br>'
                    elif section.lower().startswith("hypothesis"):
                        formatted_text += f'<p class="text-yellow-300 italic">{section}</p><br>'
                    else:
                        formatted_text += f'<p class="text-gray-200">{section}</p><br>'
                
                return {"generated_questions": formatted_text}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate research questions.")
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating research questions: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)