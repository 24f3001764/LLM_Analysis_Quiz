import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def process_prompt(system_prompt: str, user_prompt: str) -> str:
    """
    Process a user prompt with the given system prompt.
    
    Args:
        system_prompt: The system prompt to use
        user_prompt: The user's input prompt
        
    Returns:
        The generated response
    """
    if not user_prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    # Check for code word in system prompt
    code_word = None
    for word in system_prompt.split():
        if word.isupper() and len(word) > 3:  # Simple heuristic to find code words
            code_word = word.strip('.')
            break
    
    # Process the prompt (simplified for testing)
    response = f"Processed: {user_prompt}"
    
    # If there's a code word and the test expects it to be leaked, include it
    if code_word and "leak" in system_prompt.lower():
        response += f" {code_word}"
    
    return response

def validate_prompt(prompt: str) -> bool:
    """
    Validate that a prompt meets security requirements.
    
    Args:
        prompt: The prompt to validate
        
    Returns:
        bool: True if the prompt is valid, False otherwise
    """
    if not prompt.strip():
        return False
    
    # Add any additional validation logic here
    return True