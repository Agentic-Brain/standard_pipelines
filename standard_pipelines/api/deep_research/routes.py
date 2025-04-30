from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session
from standard_pipelines.extensions import db
from standard_pipelines.main.decorators import require_api_key
from standard_pipelines.api.openai.models import OpenAICredentials
from standard_pipelines.data_flow.models import Client
from .services import DeepResearchManager
from .. import api
from uuid import UUID


@api.route('/research/linkedin/<client_id>', methods=['POST'])
@require_api_key
def analyze_linkedin_profile(client_id: UUID):
    """
    Analyze a LinkedIn profile using RapidAPI and OpenAI.
    
    Args:
        client_id: The UUID of the client
        
    Expected JSON payload:
    {
        "linkedin_url": "https://www.linkedin.com/in/username"
    }
    
    Returns:
        JSON response with the analysis results
    """
    try:
        # Check if the client exists
        client = Client.query.get_or_404(client_id)
        
        # Get request data
        data = request.get_json()
        if not data or 'linkedin_url' not in data:
            return jsonify({"error": "Missing linkedin_url in request"}), 400
            
        linkedin_url = data['linkedin_url']
        if not linkedin_url or not isinstance(linkedin_url, str):
            return jsonify({"error": "Invalid linkedin_url format"}), 400
            
        # Check if RapidAPI credentials are configured in the application
        if not current_app.config.get("RAPIDAPI_KEY") or not current_app.config.get("RAPIDAPI_HOST"):
            return jsonify({"error": "RapidAPI credentials not configured"}), 500
            
        # Get OpenAI credentials for the client
        openai_creds = OpenAICredentials.query.filter_by(client_id=client_id).first()
        if not openai_creds:
            return jsonify({"error": "OpenAI credentials not found for this client"}), 404
            
        # Initialize the Deep Research manager
        dr_manager = DeepResearchManager({
            "openai_api_key": openai_creds.openai_api_key,
            "openai_model": data.get("model", "o1-preview-2024-09-12")
        })
        
        # Analyze the LinkedIn profile
        analysis_results = dr_manager.analyze_linkedin_profile(linkedin_url)
        
        return jsonify(analysis_results), 200
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing LinkedIn profile: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500