from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class QuizRequest(BaseModel):
    email: EmailStr
    secret: str
    url: HttpUrl

class QuizResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class QuizAnswer(BaseModel):
    email: EmailStr
    secret: str
    url: HttpUrl
    answer: str
    metadata: Optional[Dict[str, Any]] = None