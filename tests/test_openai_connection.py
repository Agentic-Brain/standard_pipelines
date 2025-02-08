import os
import pytest
from openai import OpenAI, OpenAIError
from standard_pipelines.api.openai.services import OpenAIAPIManager
from standard_pipelines.data_flow.exceptions import APIError

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

def test_create_embedding(app):
    """Test creating embeddings."""
    api_manager = OpenAIAPIManager({"api_key": app.config['OPENAI_API_KEY']})
    try:
        response = api_manager.create_embedding(
            input="Sample text for embedding",
            model="text-embedding-ada-002"
        )
        assert response.data[0].embedding is not None, "No embedding received"
        assert len(response.data[0].embedding) > 0, "Empty embedding received"
        
        # Test with list input
        response = api_manager.create_embedding(
            input=["Sample text 1", "Sample text 2"],
            model="text-embedding-ada-002"
        )
        assert len(response.data) == 2, "Expected 2 embeddings for 2 inputs"
        assert all(len(item.embedding) > 0 for item in response.data), "Empty embeddings received"
    except Exception as e:
        pytest.fail(f"Failed to create embedding: {str(e)}")

def test_fine_tuning_operations(app):
    """Test fine-tuning job operations."""
    api_manager = OpenAIAPIManager({"api_key": app.config['OPENAI_API_KEY']})
    
    # Test listing fine-tuning jobs
    try:
        jobs = api_manager.list_fine_tuning_jobs(limit=5)
        assert isinstance(jobs, list), "Expected list of fine-tuning jobs"
    except Exception as e:
        pytest.fail(f"Failed to list fine-tuning jobs: {str(e)}")
    
    # Test creating fine-tuning job with invalid file (should fail)
    with pytest.raises(APIError):
        api_manager.create_fine_tuning_job(
            training_file="non-existent-file",
            model="gpt-3.5-turbo"
        )
    
    # Test getting non-existent job (should fail)
    with pytest.raises(APIError):
        api_manager.get_fine_tuning_job("non-existent-job")
    
    # Test canceling non-existent job (should fail)
    with pytest.raises(APIError):
        api_manager.cancel_fine_tuning_job("non-existent-job")
