"""
This module defines the FastAPI application for the IRYM1 data analysis API.
It includes an endpoint to receive user prompts and generate code using the IRYM1 agent pipeline.
"""

import os
import json
from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from .api_schema import UserPrompt, DataAnalysisRequest
from apps.agent_pipeline import IRYM1AgentPipeline

app = FastAPI()

# Mount Static Files and Templates
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

class MockProfile:
    theme = "dark"

class MockUser:
    username = "demo_user"
    is_authenticated = True
    is_staff = True
    is_active = True
    profile = MockProfile()
    
    def get_full_name(self):
        return "Demo User"

dummy_user = MockUser()

Engine = IRYM1AgentPipeline()
Engine.build_agent()

@app.get("/irym1/")
async def prompt_room(request: Request):
    return templates.TemplateResponse("pages/prompt-room.html", {"request": request, "user": dummy_user})

@app.get("/irym1/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {"request": request, "user": dummy_user})

@app.get("/irym1/analysis-report")
async def data_analysis_report(request: Request):
    return templates.TemplateResponse("pages/data_analysis_report.html", {"request": request, "user": dummy_user})

@app.post("/irym1/analyze-ui")
async def analyze_ui(
    request: Request,
    prompt: str = Form(...),
    upload: UploadFile = File(...)
):
    try:
        if not upload or not upload.filename:
            raise HTTPException(status_code=400, detail="No file was uploaded.")
            
        file_path = f"/tmp/{upload.filename}"
        with open(file_path, "wb") as f:
            f.write(await upload.read())
            
        analysis_prompt = (
            f"Please perform a data analysis task.\n"
            f"Context: {prompt}\n"
            f"File: {file_path}\n"
            f"Task: full_pipeline\n\n"
            f"Use the 'data_analysis' tool to complete this request."
        )
        
        response_data = Engine.run_agent(analysis_prompt, "ui_session")
        report_data = None
        
        for res in response_data.get('tool_results', []):
            try:
                parsed = json.loads(res['result'])
                if 'steps' in parsed:
                    report_data = parsed
                    break
            except Exception:
                pass

        return templates.TemplateResponse("pages/data_analysis_report.html", {
            "request": request, 
            "report_data": report_data,
            "answer": response_data.get("answer"),
            "user": dummy_user
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/irym1/prompt/{chat_id}")
async def generate_code_endpoint(chat_id:str, req:UserPrompt):
    try:
        response_data = Engine.run_agent(req.prompt, chat_id)
        return {
            "status": 200,
            **response_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/irym1/analysis/{chat_id}")
async def data_analysis_endpoint(chat_id: str, req: DataAnalysisRequest):
    try:
        # Construct a specific prompt that forces the agent to use the data_analysis tool
        analysis_prompt = (
            f"Please perform a data analysis task.\n"
            f"Context: {req.prompt}\n"
            f"File: {req.file_path}\n"
            f"Task: {req.task}\n"
        )
        if req.target_column:
            analysis_prompt += f"Target Column: {req.target_column}\n"
        if req.ml_task:
            analysis_prompt += f"ML Task Type: {req.ml_task}\n"
            
        analysis_prompt += "\nUse the 'data_analysis' tool to complete this request."
        
        response_data = Engine.run_agent(analysis_prompt, chat_id)
        return {
            "status": 200,
            **response_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )