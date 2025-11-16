import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app

class TestAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test the root endpoint returns the correct response."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "LLM Analysis Quiz API is running"}

    @patch('src.main.process_quiz_submission')
    def test_submit_quiz_success(self, mock_process, client):
        """Test successful quiz submission."""
        # Mock the process_quiz_submission function
        mock_process.return_value = {
            "success": True,
            "message": "Quiz submitted successfully",
            "answers": [{"q1": "A"}]
        }

        # Test data
        quiz_data = {
            "email": "test@example.com",
            "secret": "test_secret",
            "url": "http://example.com/quiz"
        }

        # Make the request
        response = client.post("/submit-quiz", json=quiz_data)
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_process.assert_called_once_with(
            email="test@example.com",
            url="http://example.com/quiz"
        )

    def test_submit_quiz_invalid_data(self, client):
        """Test quiz submission with invalid data."""
        # Test with missing required fields
        response = client.post("/submit-quiz", json={"email": "test@example.com"})
        assert response.status_code == 422  # Validation error

    @patch('src.main.process_quiz_submission')
    def test_submit_quiz_error(self, mock_process, client):
        """Test error handling in quiz submission."""
        # Mock the process_quiz_submission to raise an exception
        mock_process.side_effect = Exception("Something went wrong")

        # Test data
        quiz_data = {
            "email": "test@example.com",
            "secret": "test_secret",
            "url": "http://example.com/quiz"
        }

        # Make the request
        response = client.post("/submit-quiz", json=quiz_data)
        
        # Assertions
        assert response.status_code == 500
        assert "error" in response.json()
