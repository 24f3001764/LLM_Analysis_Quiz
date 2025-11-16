from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from .config import settings
from .browser import BrowserManager
from .quiz_solver import QuizSolver

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOGS_DIR / "app.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Analysis Quiz API",
    description="API for solving LLM-based quiz questions",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

class QuizResponse(BaseModel):
    status: str
    message: str
    quiz_data: Optional[Dict[str, Any]] = None
    answers: Optional[List[Dict[str, Any]]] = None
    next_url: Optional[str] = None
    time_remaining: Optional[float] = None

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "LLM Analysis Quiz API is running"}

async def process_quiz_submission(email: str, url: str, timeout: int = 170) -> Dict[str, Any]:
    """
    Process a quiz submission by:
    1. Fetching the quiz page
    2. Extracting questions
    3. Solving questions
    4. Submitting answers
    
    Args:
        email: User's email
        url: Quiz URL
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with quiz results
    """
    start_time = datetime.utcnow()
    time_remaining = lambda: (start_time + timedelta(seconds=timeout) - datetime.utcnow()).total_seconds()
    
    try:
        # Initialize browser and fetch quiz page
        async with BrowserManager() as browser:
            logger.info(f"Fetching quiz from {url}")
            quiz_data = await browser.extract_quiz_data(url)
            
            # Initialize quiz solver
            solver = QuizSolver(quiz_data)
            
            # Solve questions with remaining time
            results = await solver.solve()
            
            # Submit answers if there's time left
            if time_remaining() > 10:  # Leave 10 seconds for submission
                submission = await solver.submit_answers({
                    q["id"]: q["answer"] for q in results["answers"]
                })
                results["submission"] = submission
            else:
                logger.warning("Not enough time left for submission")
                results["submission"] = {"success": False, "message": "Timeout before submission"}
            
            return {
                "status": "success",
                "message": "Quiz processed successfully",
                "quiz_data": quiz_data,
                "answers": results.get("answers", []),
                "submission": results.get("submission", {}),
                "time_remaining": max(0, time_remaining())
            }
            
    except Exception as e:
        logger.error(f"Error processing quiz: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to process quiz: {str(e)}",
            "time_remaining": max(0, time_remaining())
        }

@app.post("/submit", response_model=QuizResponse)
async def submit_quiz(request: QuizRequest):
    """
    Main endpoint for quiz submission.
    
    Expected JSON payload:
    {
        "email": "user@example.com",
        "secret": "your_secret_key",
        "url": "https://quiz-url.example.com"
    }
    """
    logger.info(f"Received quiz submission request from {request.email} for {request.url}")
    
    # Validate secret
    if request.secret != settings.QUIZ_SECRET:
        logger.warning(f"Invalid secret provided for email: {request.email}")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    try:
        # Process the quiz with a timeout
        result = await asyncio.wait_for(
            process_quiz_submission(request.email, request.url),
            timeout=settings.REQUEST_TIMEOUT
        )
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"Quiz processing timed out for {request.url}")
        raise HTTPException(
            status_code=408,
            detail="Quiz processing timed out. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1
    )