import pytest
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
