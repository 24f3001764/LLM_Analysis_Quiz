from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="API for automated quiz solving and analysis",
        version=settings.VERSION,
        debug=settings.DEBUG,
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize application services on startup."""
        # Ensure all required directories exist
        for directory in [settings.LOGS_DIR, settings.DOWNLOADS_DIR, settings.TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"{settings.APP_NAME} v{settings.VERSION} starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.DEBUG}")

    return app

# Create the FastAPI app
app = create_app()

@app.on_event("startup")
async def startup_event():
    import time
    logger.info("Application starting up...")
    # Add any initialization code here
    time.sleep(2)  # Give time for everything to initialize
    logger.info("Startup complete!")

# Request/Response Models
class QuizRequest(BaseModel):
    """Request model for quiz submission."""
    email: str = Field(..., description="User's email address")
    secret: str = Field(..., description="API secret key for authentication")
    url: str = Field(..., description="URL of the quiz to be solved")
    timeout: Optional[int] = Field(
        settings.BROWSER_TIMEOUT,
        description="Maximum time in seconds to wait for the quiz to load",
    )
    max_retries: Optional[int] = Field(
        settings.MAX_RETRIES,
        description="Maximum number of retry attempts for failed operations",
    )
    headless: Optional[bool] = Field(
        settings.HEADLESS_BROWSER,
        description="Whether to run the browser in headless mode",
    )


class QuizResponse(BaseModel):
    """Response model for quiz submission."""
    status: str = Field(..., description="Overall status of the operation")
    message: Optional[str] = Field(None, description="Human-readable message")
    email: Optional[str] = Field(None, description="User's email address")
    url: Optional[str] = Field(None, description="URL of the processed quiz")
    questions: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of questions and their answers"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the quiz"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the response",
    )
    execution_time: Optional[float] = Field(
        None, description="Total execution time in seconds"
    )
    error: Optional[Dict[str, Any]] = Field(
        None, description="Error details if the operation failed"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    status: str = "error"
    message: str
    error: Optional[Dict[str, Any]] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "LLM Analysis Quiz API is running"}

async def process_quiz_submission(
    email: str,
    url: str,
    timeout: int = settings.BROWSER_TIMEOUT,
    max_retries: int = settings.MAX_RETRIES,
    headless: bool = settings.HEADLESS_BROWSER,
) -> Dict[str, Any]:
    """
    Process a quiz submission end-to-end.
    
    This function handles the complete workflow of:
    1. Initializing the browser
    2. Navigating to the quiz URL
    3. Extracting quiz questions
    4. Solving the questions
    5. Submitting the answers
    6. Returning the results
    
    Args:
        email: User's email address
        url: URL of the quiz
        timeout: Maximum time to wait for operations (in seconds)
        max_retries: Maximum number of retry attempts for failed operations
        headless: Whether to run the browser in headless mode
        
    Returns:
        Dictionary containing the quiz results
        
    Raises:
        HTTPException: If there's an error processing the quiz
    """
    start_time = datetime.utcnow()
    time_remaining = lambda: (start_time + timedelta(seconds=timeout) - datetime.utcnow()).total_seconds()
    
    try:
        # Initialize browser and fetch quiz page
        async with BrowserManager(headless=headless) as browser:
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

# Additional utility endpoints
@app.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Health Check",
    description="Check the health status of the API and its dependencies.",
    tags=["Health"]
)
async def health_check():
    """Check the health status of the API."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "browser": "operational"
        }
    }

# File download endpoint
@app.get(
    "/download/{file_path:path}",
    summary="Download a file",
    description="Download a file that was generated during quiz processing.",
    tags=["Files"]
)
async def download_file(file_path: str):
    """Download a file from the server."""
    try:
        file_path = Path(settings.DOWNLOADS_DIR) / file_path
        
        # Security check to prevent directory traversal
        if not file_path.resolve().is_relative_to(settings.DOWNLOADS_DIR):
            raise HTTPException(status_code=403, detail="Access denied")
            
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Error downloading file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with a JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with a JSON response."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "error": str(exc),
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS,
        timeout_keep_alive=settings.REQUEST_TIMEOUT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        use_colors=True
    )