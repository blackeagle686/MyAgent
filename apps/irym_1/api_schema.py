"""
This module defines the data models for the IRYM1 API using Pydantic.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class UserPrompt(BaseModel):
    prompt: str
    files: List[str] = Field(default_factory=list)
    temperature: float = 0.2
    max_iterations: int = 10
    mode: Optional[str] = "analysis"

class DataAnalysisRequest(BaseModel):
    prompt: str
    file_path: str
    task: str = "full_pipeline" # eda, train_model, predict, full_pipeline
    target_column: Optional[str] = None
    ml_task: Optional[str] = None # classification, regression, clustering