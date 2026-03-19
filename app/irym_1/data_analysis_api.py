"""
This module defines the FastAPI application for the IRYM1 data analysis API.
It includes an endpoint to receive user prompts and generate code using the IRYM1 agent pipeline.
"""

from fastapi import FastAPI, HTTPException

from .api_schema import UserPrompt
from ..agent_pipeline import IRYM1AgentPipeline

app = FastAPI()

Engine = IRYM1AgentPipeline()
Engine.build_agent()

@app.post("/irym1/prompt/{chat_id}")
async def generate_code_endpoint(chat_id:str, req:UserPrompt):
    try:
        result = Engine.run_agent(req.prompt, chat_id)
        return {
            "chat_id":chat_id,
            "result":result,
            "status":200
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )