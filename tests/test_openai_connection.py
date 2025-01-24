import os
import pytest
from openai import OpenAI

def test_openai_credentials(app):
    """Test that OpenAI credentials are properly loaded and working"""
    # Check if the API key exists in environment
    assert 'TESTING_OPENAI_API_KEY' in os.environ, "OpenAI API key not found in environment variables"
    
    # Initialize the client with the API key
    client = OpenAI(api_key=app.config['OPENAI_API_KEY'])
    
    try:
        # Make a simple API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'Hello, testing!'"}
            ],
            max_tokens=10
        )
        
        # Check if we got a response
        assert response.choices[0].message.content is not None, "No response content received"
        assert len(response.choices[0].message.content) > 0, "Empty response received"
        
    except Exception as e:
        pytest.fail(f"Failed to make OpenAI API call: {str(e)}")