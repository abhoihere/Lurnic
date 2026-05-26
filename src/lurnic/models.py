# src/lurnic/models.py
from typing import Optional, List
from pydantic import BaseModel

class QuestionRequest(BaseModel):
    """Request from client asking a question about a PDF"""
    question: str
    tier: str = "free"  # "free" or "paid"

class AnswerResponse(BaseModel):
    """Response from the API"""
    answer: str
    method_used: str
    processing_time_seconds: float
    images_processed: Optional[int] = 0
    pages_processed: Optional[int] = 0

print("✓ models.py loaded successfully")