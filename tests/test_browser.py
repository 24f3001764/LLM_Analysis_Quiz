import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from src.browser import BrowserManager
from src.config import settings

class TestBrowserManager:
    @pytest.fixture
    def mock_playwright(self):
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            # Setup mock browser and context
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            # Configure the mock Playwright instance
            mock_playwright.return_value.start.return_value = AsyncMock()
            mock_playwright.return_value.start.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            yield mock_playwright, mock_browser, mock_context, mock_page
    
    @pytest.fixture
    def sample_quiz_data(self):
        return {
            "title": "Sample Quiz",
            "url": "http://example.com/quiz",
            "content": "Sample quiz content with questions and instructions.",
            "questions": [
                {"id": "q1", "text": "What is 2+2?", "type": "multiple_choice"},
                {"id": "q2", "text": "Explain your answer", "type": "text"}
            ],
            "instructions": [
                {"type": "general", "text": "Answer all questions"},
                {"type": "time", "text": "You have 30 minutes"}
            ],
            "metadata": {
                "question_count": 2,
                "time_limit": 1800,
                "extracted_at": datetime.utcnow().isoformat()
            }
        }

    @pytest.mark.asyncio
    async def test_browser_initialization(self, mock_playwright):
        """Test that the browser initializes with the correct settings."""
        mock_pw, mock_browser, mock_context, mock_page = mock_playwright

        # Setup the async context manager
        async with BrowserManager() as manager:
            # Verify browser was initialized correctly
            assert manager.browser is not None
            assert manager.context is not None
            assert manager.page is not None

            # Verify browser launch arguments
            mock_pw.chromium.launch.assert_called_once()
            mock_browser.new_context.assert_called_once()
            mock_context.new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_page(self, mock_playwright):
        """Test fetching a web page."""
        _, _, _, mock_page = mock_playwright
        mock_page.content.return_value = "<html>Test Content</html>"
        
        async with BrowserManager() as browser:
            browser.page = mock_page
            content = await browser.fetch_page("http://example.com")
            
            assert content == "<html>Test Content</html>"
            mock_page.goto.assert_called_once_with(
                "http://example.com",
                timeout=settings.BROWSER_TIMEOUT * 1000,
                wait_until="domcontentloaded"
            )

    @pytest.mark.asyncio
    async def test_extract_quiz_data(self, mock_playwright, sample_quiz_data):
        """Test extracting quiz data from a page."""
        _, _, _, mock_page = mock_playwright
        mock_page.content.return_value = "<div>Quiz Content</div>"
        mock_page.evaluate.return_value = sample_quiz_data
        
        async with BrowserManager() as browser:
            browser.page = mock_page
            result = await browser.extract_quiz_data("http://example.com/quiz")
            
            # Verify the basic structure of the response
            assert "title" in result
            assert "questions" in result
            assert "instructions" in result
            assert "metadata" in result
            
            # Verify the page was loaded
            mock_page.goto.assert_called_once_with(
                "http://example.com/quiz",
                wait_until="domcontentloaded"
            )
            
            # Verify the evaluation was called with the correct script
            assert mock_page.evaluate.called
            
    @pytest.mark.asyncio
    async def test_submit_quiz_answer_form(self, mock_playwright):
        """Test submitting a quiz answer via form."""
        _, _, mock_context, mock_page = mock_playwright
        
        # Mock form submission
        mock_form = AsyncMock()
        mock_page.query_selector_all.return_value = [mock_form]
        
        # Mock form elements
        mock_input = AsyncMock()
        mock_form.query_selector.return_value = mock_input
        mock_input.get_attribute.return_value = "text"
        
        async with BrowserManager() as browser:
            browser.page = mock_page
            
            # Test form submission
            result = await browser.submit_quiz_answer(
                "http://example.com/submit",
                {
                    "email": "test@example.com",
                    "secret": "test-secret",
                    "answer": "Test answer",
                    "metadata": {"test": "data"}
                }
            )
            
            # Verify the form was processed
            assert result["success"] is True
            mock_page.goto.assert_called_once_with(
                "http://example.com/submit",
                wait_until="domcontentloaded"
            )
            mock_form.query_selector.assert_called()
            mock_input.fill.assert_called_with("Test answer")
    
    @pytest.mark.asyncio
    async def test_submit_quiz_answer_api(self, mock_playwright):
        """Test submitting a quiz answer via API."""
        _, _, _, mock_page = mock_playwright
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}
        mock_page.request.post.return_value = mock_response
        
        # No forms on the page
        mock_page.query_selector_all.return_value = []
        
        async with BrowserManager() as browser:
            browser.page = mock_page
            
            # Test API submission
            result = await browser.submit_quiz_answer(
                "http://api.example.com/submit",
                {
                    "email": "test@example.com",
                    "secret": "test-secret",
                    "answer": "Test answer",
                    "metadata": {"test": "data"}
                }
            )
            
            # Verify the API was called
            assert result["success"] is True
            mock_page.request.post.assert_called_once()
            
            # Verify the request was made with correct parameters
            args, kwargs = mock_page.request.post.call_args
            assert args[0] == "http://api.example.com/submit"
            assert json.loads(kwargs["data"])["answer"] == "Test answer"
    
    @pytest.mark.asyncio
    async def test_download_file(self, mock_playwright, tmp_path):
        """Test downloading a file."""
        mock_pw, mock_browser, mock_context, mock_page = mock_playwright
        test_url = "https://example.com/file.pdf"
        download_dir = str(tmp_path)
        
        # Setup the download mock
        mock_download = AsyncMock()
        mock_download.suggested_filename = "test.pdf"
        mock_download.save_as = AsyncMock()
        
        # Setup the async context manager for expect_download
        class AsyncContextManager:
            async def __aenter__(self):
                return mock_download
                
            async def __aexit__(self, *args):
                pass
        
        mock_page.expect_download.return_value = AsyncContextManager()
        
        # Create the manager and test download
        async with BrowserManager() as manager:
            manager.page = mock_page  # Inject our mock page
            download_path = await manager.download_file(test_url, download_dir)
            
            # Verify the download was initiated
            mock_page.goto.assert_called_once_with(test_url, wait_until="networkidle")
            mock_page.expect_download.assert_called_once()
            
            # Verify the download path is correct
            assert download_path == str(tmp_path / "test.pdf")
            mock_download.save_as.assert_called_once_with(str(tmp_path / "test.pdf"))
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_playwright):
        """Test error handling in browser operations."""
        _, _, _, mock_page = mock_playwright
        mock_page.goto.side_effect = Exception("Test error")
        
        async with BrowserManager() as browser:
            browser.page = mock_page
            
            # Test that exceptions are properly propagated
            with pytest.raises(Exception, match="Test error"):
                await browser.fetch_page("http://example.com")
    
    @pytest.mark.asyncio
    async def test_identify_questions(self, mock_playwright):
        """Test question identification from content."""
        browser = BrowserManager()
        
        # Test content with questions
        content = """
        Q1. What is 2+2?
        A) 3
        B) 4
        C) 5
        
        Q2. What is the capital of France?
        """
        
        quiz_data = {"content": content}
        questions = browser._identify_questions(quiz_data)
        
        # Verify questions were identified
        assert len(questions) >= 2
        assert any("2+2" in q["text"] for q in questions)
        assert any("capital of France" in q["text"] for q in questions)
    
    @pytest.mark.asyncio
    async def test_extract_instructions(self, mock_playwright):
        """Test instruction extraction from content."""
        browser = BrowserManager()
        
        # Test content with instructions
        content = """
        INSTRUCTIONS:
        1. Answer all questions
        2. You have 30 minutes
        
        NOTE: Calculators are allowed
        
        Q1. First question...
        """
        
        instructions = browser._extract_instructions(content)
        
        # Verify instructions were extracted
        assert len(instructions) >= 2
        assert any("Answer all questions" in i["text"] for i in instructions)
        assert any("Calculators are allowed" in i["text"] for i in instructions)
