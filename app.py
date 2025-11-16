from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Union, List, Optional
import logging
import hashlib
import time
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from src.config import settings
from src.browser import BrowserManager

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# In-memory storage for rate limiting and request tracking
rate_limit_cache = {}
request_cache = {}

class CacheManager:
    """Simple in-memory cache manager (replace with Redis in production)."""
    
    @staticmethod
    def get_request(request_id: str) -> Optional[Dict]:
        """Get a cached request by ID."""
        return request_cache.get(request_id)
    
    @staticmethod
    def set_request(request_id: str, data: Dict, ttl: int = 3600) -> None:
        """Cache a request with a TTL (in seconds)."""
        request_cache[request_id] = {
            'data': data,
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
        }
    
    @staticmethod
    def cleanup() -> None:
        """Remove expired cache entries."""
        now = datetime.utcnow()
        expired_keys = [k for k, v in request_cache.items() 
                       if v['expires_at'] < now]
        for key in expired_keys:
            request_cache.pop(key, None)

# Run cleanup periodically
async def cleanup_task():
    while True:
        CacheManager.cleanup()
        await asyncio.sleep(3600)  # Cleanup every hour

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class QuizRequest(BaseModel):
    email: str = Field(..., description="Student's email address")
    secret: str = Field(..., description="Secret key for authentication")
    url: HttpUrl = Field(..., description="URL of the quiz to process")
    request_id: Optional[str] = Field(
        None, 
        description="Optional request ID for tracking"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the request"
    )

class QuizAnswer(QuizRequest):
    answer: Union[str, int, float, bool, Dict[str, Any], List[Any]] = Field(
        ...,
        description="The answer to submit"
    )

class QuizResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Response data, if any"
    )
    next_url: Optional[HttpUrl] = Field(
        None,
        description="Next URL to process, if applicable"
    )
    error: Optional[str] = Field(
        None,
        description="Error message, if any"
    )
    request_id: Optional[str] = Field(
        None,
        description="Unique ID for tracking this request"
    )

def verify_secret(secret: str) -> bool:
    """Verify the provided secret against the configured secret."""
    # In a production environment, use a timing-safe comparison
    # and consider storing hashed secrets in a database
    return secret == settings.QUIZ_SECRET

def check_rate_limit(client_ip: str) -> bool:
    """Check if the client has exceeded the rate limit."""
    current_time = int(time.time())
    window_start = current_time - 60  # 1 minute window
    
    # Clean up old entries
    rate_limit_cache[client_ip] = [t for t in rate_limit_cache.get(client_ip, []) if t > window_start]
    
    # Check rate limit
    request_count = len(rate_limit_cache.get(client_ip, []))
    if request_count >= 100:  # 100 requests per minute
        logger.warning(f"Rate limit exceeded for IP {client_ip} ({request_count} requests in last minute)")
        return False
    
    # Add current request timestamp
    if client_ip not in rate_limit_cache:
        rate_limit_cache[client_ip] = []
    rate_limit_cache[client_ip].append(current_time)
    return True

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex}"

@app.get("/")
async def root():
    """Root endpoint that returns basic API information."""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs"
    }

@app.post("/api/quiz", response_model=QuizResponse)
async def process_quiz(
    quiz_request: QuizRequest, 
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Process a quiz request, verify the secret, and return the quiz data.
    
    This endpoint will:
    1. Verify the request is within rate limits
    2. Authenticate using the provided secret
    3. Process the quiz URL to extract questions and instructions
    4. Return the processed data or an error message
    
    Args:
        quiz_request: The quiz request containing email, secret, and URL
        request: The incoming HTTP request
        background_tasks: FastAPI background tasks
        
    Returns:
        QuizResponse with the processed data or an error message
    """
    client_ip = request.client.host or "unknown"
    request_id = quiz_request.request_id or generate_request_id()
    
    # Check rate limiting
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": "Rate limit exceeded. Please try again later.",
                "request_id": request_id
            }
        )
    
    # Verify secret
    if not verify_secret(quiz_request.secret):
        logger.warning(f"Invalid secret provided from IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Invalid secret",
                "request_id": request_id
            }
        )
    
    logger.info(f"Processing quiz request {request_id} from {quiz_request.email} for URL: {quiz_request.url}")
    
    try:
        # Process the quiz URL using the browser
        async with BrowserManager(headless=settings.HEADLESS_BROWSER) as browser:
            # Extract quiz data
            quiz_data = await browser.extract_quiz_data(str(quiz_request.url))
            
            # Cache the quiz data for future reference
            CacheManager.set_request(
                request_id,
                {
                    "url": str(quiz_request.url),
                    "email": quiz_request.email,
                    "data": quiz_data,
                    "status": "processed",
                    "timestamp": datetime.utcnow().isoformat()
                },
                ttl=3600  # Cache for 1 hour
            )
            
            # Prepare the response
            response_data = {
                "success": True,
                "message": "Quiz processed successfully",
                "data": {
                    "quiz_id": request_id,
                    "title": quiz_data.get("title", "Untitled Quiz"),
                    "questions": quiz_data.get("questions", []),
                    "instructions": quiz_data.get("instructions", []),
                    "metadata": quiz_data.get("metadata", {})
                },
                "request_id": request_id
            }
            
            # If there are forms, include submission information
            if quiz_data.get("forms"):
                response_data["data"]["submission_info"] = {
                    "has_forms": True,
                    "form_count": len(quiz_data["forms"])
                }
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing quiz {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Error processing quiz: {str(e)}",
                "request_id": request_id
            }
        )

@app.post("/api/submit", response_model=QuizResponse)
async def submit_answer(
    answer: QuizAnswer, 
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Submit an answer to a quiz.
    
    This endpoint will:
    1. Verify the request is within rate limits
    2. Authenticate using the provided secret
    3. Submit the answer to the quiz URL
    4. Return the submission result
    
    Args:
        answer: The answer to submit, including metadata
        request: The incoming HTTP request
        background_tasks: FastAPI background tasks
        
    Returns:
        QuizResponse with the submission result or an error message
    """
    client_ip = request.client.host or "unknown"
    request_id = answer.request_id or generate_request_id()
    
    # Check rate limiting
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "success": False,
                "message": "Rate limit exceeded. Please try again later.",
                "request_id": request_id
            }
        )
    
    # Verify secret
    if not verify_secret(answer.secret):
        logger.warning(f"Invalid secret provided from IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "message": "Invalid secret",
                "request_id": request_id
            }
        )
    
    logger.info(f"Processing answer submission {request_id} from {answer.email} for URL: {answer.url}")
    
    try:
        # Process the submission using the browser
        async with BrowserManager(headless=settings.HEADLESS_BROWSER) as browser:
            # Submit the answer
            submission_result = await browser.submit_quiz_answer(
                str(answer.url),
                {
                    "email": answer.email,
                    "secret": answer.secret,
                    "answer": answer.answer,
                    "metadata": answer.metadata or {},
                    "submitted_at": datetime.utcnow().isoformat()
                }
            )
            
            # Log the submission
            logger.info(f"Answer submitted successfully for request {request_id}")
            
            # Prepare the response
            response_data = {
                "success": submission_result.get("success", False),
                "message": "Answer submitted successfully",
                "data": {
                    "submission_id": request_id,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "response": submission_result.get("response", {})
                },
                "request_id": request_id
            }
            
            # If there's a next URL, include it in the response
            if "next_url" in submission_result:
                response_data["next_url"] = submission_result["next_url"]
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting answer {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": f"Error submitting answer: {str(e)}",
                "request_id": request_id
            }
        )

# Add a startup event to initialize the application
@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    # Create necessary directories
    for directory in [settings.DOWNLOADS_DIR, settings.LOGS_DIR, settings.TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"{settings.APP_NAME} v{settings.VERSION} starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

# Add exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error formatting."""
    error_detail = exc.detail
    if isinstance(error_detail, dict):
        # If the detail is already a dict, use it as is
        response_data = error_detail
    else:
        # Otherwise, create a standard error response
        response_data = {
            "success": False,
            "message": str(error_detail),
            "error": str(error_detail),
            "status_code": exc.status_code
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with consistent error formatting."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    error_message = "An unexpected error occurred"
    
    logger.error(
        f"Unhandled exception in request {request_id}: {str(exc)}", 
        exc_info=True,
        extra={"request_id": request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": error_message,
            "error": str(exc) if settings.DEBUG else error_message,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "request_id": request_id
        }
    )

# Add a health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

# Add a request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request for tracking."""
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Process the request
    response = await call_next(request)
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response
