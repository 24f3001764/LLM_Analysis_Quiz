# tests/test_integration.py
import pytest
import aiohttp
import json
from pathlib import Path
from datetime import datetime

# Test data
TEST_EMAIL = "test@example.com"
TEST_SECRET = "test-secret"
DEMO_URL = "https://tds-llm-analysis.s-anand.net/demo"
SUBMIT_URL = "https://tds-llm-analysis.s-anand.net/submit"

class TestQuizIntegration:
    @pytest.fixture
    async def session(self):
        async with aiohttp.ClientSession() as session:
            yield session

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_demo_quiz_flow(self, session):
        """Test the complete quiz flow with the demo endpoint."""
        # 1. Get the quiz data
        quiz_data = {
            "email": TEST_EMAIL,
            "secret": TEST_SECRET,
            "url": DEMO_URL
        }
        
        # 2. Submit the answer
        answer_data = {
            "email": TEST_EMAIL,
            "secret": TEST_SECRET,
            "url": DEMO_URL,
            "answer": "Test answer from integration test"
        }
        
        async with session.post(SUBMIT_URL, json=answer_data) as response:
            assert response.status == 200
            result = await response.json()
            
            # Verify the response structure
            assert "status" in result
            assert "message" in result
            assert isinstance(result["message"], str)
            
            # For demo purposes, the endpoint might return a success message
            # even with test credentials
            assert result["status"] in ["success", "error"]
            
            if result["status"] == "error":
                assert "error" in result
                assert isinstance(result["error"], str)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_credentials(self, session):
        """Test with invalid credentials."""
        answer_data = {
            "email": "invalid@example.com",
            "secret": "invalid-secret",
            "url": DEMO_URL,
            "answer": "Test answer"
        }
        
        async with session.post(SUBMIT_URL, json=answer_data) as response:
            assert response.status == 200  # Note: The demo might return 200 even for auth errors
            result = await response.json()
            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_missing_fields(self, session):
        """Test with missing required fields."""
        test_cases = [
            {"secret": TEST_SECRET, "url": DEMO_URL, "answer": "test"},  # missing email
            {"email": TEST_EMAIL, "url": DEMO_URL, "answer": "test"},    # missing secret
            {"email": TEST_EMAIL, "secret": TEST_SECRET, "answer": "test"},  # missing url
            {"email": TEST_EMAIL, "secret": TEST_SECRET, "url": DEMO_URL}    # missing answer
        ]
        
        for data in test_cases:
            async with session.post(SUBMIT_URL, json=data) as response:
                assert response.status == 400  # Bad Request
                result = await response.json()
                assert result["status"] == "error"
                assert "error" in result
                assert "missing" in result["error"].lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rate_limiting(self, session):
        """Test rate limiting by making multiple rapid requests."""
        answer_data = {
            "email": TEST_EMAIL,
            "secret": TEST_SECRET,
            "url": DEMO_URL,
            "answer": "Rate limit test"
        }
        
        # Make multiple requests in quick succession
        responses = []
        for _ in range(5):
            async with session.post(SUBMIT_URL, json=answer_data) as response:
                responses.append(response.status)
                
        # The demo endpoint might not implement rate limiting, but we can check for 429
        assert any(status == 429 for status in responses) or all(status == 200 for status in responses)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_large_answer(self, session):
        """Test with a very large answer."""
        large_answer = "A" * 10000  # 10KB answer
        answer_data = {
            "email": TEST_EMAIL,
            "secret": TEST_SECRET,
            "url": DEMO_URL,
            "answer": large_answer
        }
        
        async with session.post(SUBMIT_URL, json=answer_data) as response:
            # Should either succeed or return a 413 Payload Too Large
            assert response.status in [200, 413]
            if response.status == 200:
                result = await response.json()
                assert "status" in result