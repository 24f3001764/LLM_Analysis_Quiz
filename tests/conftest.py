import pytest
from playwright.async_api import async_playwright
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.main import app
from src.browser import BrowserManager
from src.quiz_solver import QuizSolver, QuizQuestion

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser():
    """Create a browser instance for tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()

@pytest.fixture
def test_client():
    """Fixture for FastAPI test client."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_browser_manager():
    """Fixture for a mocked BrowserManager."""
    with patch('src.browser.BrowserManager') as mock:
        mock.return_value.__aenter__.return_value = AsyncMock()
        yield mock

@pytest.fixture
def sample_quiz_data():
    """Sample quiz data for testing."""
    return {
        "questions": [
            {
                "id": "q1",
                "text": "What is the capital of France?",
                "type": "multiple_choice",
                "options": ["London", "Paris", "Berlin", "Madrid"]
            },
            {
                "id": "q2",
                "text": "What is 2+2?",
                "type": "number"
            }
        ]
    }

@pytest.fixture
def sample_quiz_questions():
    """Sample quiz questions for testing."""
    return [
        QuizQuestion(
            question_id="q1",
            question_text="What is the capital of France?",
            question_type="multiple_choice",
            options=["London", "Paris", "Berlin", "Madrid"],
            answer="Paris"
        ),
        QuizQuestion(
            question_id="q2",
            question_text="What is 2+2?",
            question_type="number",
            answer=4
        )
    ]

@pytest.fixture
def mock_playwright(mocker):
    # Create mock objects
    mock_pw = mocker.MagicMock()
    mock_browser = mocker.AsyncMock()
    mock_context = mocker.AsyncMock()
    mock_page = mocker.AsyncMock()
    
    # Set up the chain of calls
    mock_pw.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Mock the async context manager
    mock_playwright = mocker.patch('playwright.async_api.async_playwright')
    mock_playwright.return_value.__aenter__.return_value = mock_pw
    
    return mock_pw, mock_browser, mock_context, mock_page