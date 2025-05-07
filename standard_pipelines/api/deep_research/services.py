"""
DeepResearchManager for integrating various research capabilities.
"""
from typing import Dict, Any, List, Optional
import re
import json
import concurrent.futures

from flask import current_app
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion

from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError
from standard_pipelines.api.services import BaseManualAPIManager
from standard_pipelines.api.openai.services import OpenAIAPIManager
import requests


class LinkedInAPIClient(BaseManualAPIManager):
    """Internal specialized client for LinkedIn RapidAPI endpoints."""
    
    @property
    def required_config(self) -> list[str]:
        return ["rapidapi_key", "rapidapi_host"]
    
    def api_url(self, api_context: Optional[dict] = None) -> str:
        """Get the RapidAPI URL based on the context."""
        host = self.api_config['rapidapi_host']
        endpoint = api_context.get('endpoint', '') if api_context else ''
        return f"https://{host}/{endpoint}"
        
    def https_headers(self, api_context: Optional[dict] = None) -> Optional[dict]:
        """Get headers for RapidAPI request."""
        return {
            'x-rapidapi-key': self.api_config['rapidapi_key'],
            'x-rapidapi-host': self.api_config['rapidapi_host']
        }
    
    @property
    def https_method(self) -> str:
        """Override the default method to use GET for RapidAPI calls."""
        return "GET"
    
    def https_parameters(self, api_context: Optional[dict] = None) -> Optional[dict]:
        """Get parameters for RapidAPI request."""
        if api_context and 'params' in api_context:
            return api_context['params']
        return None


class DeepResearchManager(BaseAPIManager):
    """
    Manager for deep research capabilities including LinkedIn profile analysis.
    Uses the application's global RapidAPI credentials and OpenAI API keys.
    """
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        
        # Get RapidAPI credentials from app config
        app_config = current_app.config
        rapidapi_config = {
            "rapidapi_key": app_config.get("RAPIDAPI_KEY"),
            "rapidapi_host": app_config.get("RAPIDAPI_HOST") 
        }
        
        # Create LinkedIn API client
        self.linkedin_client = LinkedInAPIClient(rapidapi_config)
        
        # Initialize the OpenAI manager with provided API key
        openai_config = {"api_key": api_config.get("openai_api_key")}
        self.openai_manager = OpenAIAPIManager(openai_config)
        
        # Default OpenAI model to use
        self.model = api_config.get("openai_model", "o1-preview-2024-09-12")
    
    @property
    def required_config(self) -> list[str]:
        """
        Define required configuration values.
        The manager now only requires the OpenAI API key as RapidAPI is global.
        """
        return ["openai_api_key"]
    
    def analyze_linkedin_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """
        Analyze a LinkedIn profile using RapidAPI for data extraction and OpenAI for analysis.
        
        Args:
            linkedin_url: URL of the LinkedIn profile to analyze
        
        Returns:
            Dict[str, Any]: Analysis results including profile data and AI-generated insights
        """
        if not self.linkedin_client or not self.openai_manager:
            raise ValueError("LinkedIn client and OpenAI manager must be initialized")
        
        # Check if RapidAPI credentials are configured
        if not current_app.config.get("RAPIDAPI_KEY") or not current_app.config.get("RAPIDAPI_HOST"):
            raise ValueError("RapidAPI credentials not configured in application config")
        
        # Extract all LinkedIn data
        profile_data = self._extract_linkedin_profile_data(linkedin_url)
        if not profile_data:
            raise APIError("Failed to extract LinkedIn profile data")
            
        posts_data = self._extract_linkedin_posts(linkedin_url)
        comments_data = self._extract_linkedin_comments(profile_data["username"])
        profile_image_url = self._extract_linkedin_profile_image(linkedin_url)
        
        # Build prompts for analysis
        profile_prompt = self._build_profile_prompt(profile_data)
        posts_prompt = self._build_posts_prompt(posts_data, profile_data["first_name"]) if posts_data else ""
        comments_prompt = self._build_comments_prompt(comments_data, profile_data["first_name"]) if comments_data else ""
        
        # Run analyses in parallel
        profile_analysis, posts_analysis, comments_analysis = self._run_parallel_analyses(
            profile_prompt, posts_prompt, comments_prompt
        )
        
        # Generate summary
        combined_analysis = f"""
        # Posts Overview:
        {posts_analysis}
        # Comments Overview:
        {comments_analysis}
        """
        
        summary_prompt = self._build_summary_prompt(profile_data["full_name"], profile_data, combined_analysis)
        summary = self._call_openai(summary_prompt)
        
        # Format and return results
        return {
            "profile": {
                "full_name": profile_data["full_name"],
                "first_name": profile_data["first_name"],
                "last_name": profile_data["last_name"],
                "location": profile_data["location"],
                "headline": profile_data["headline"],
                "current_role": profile_data["current_role"],
                "current_company": profile_data["current_company"],
                "image_url": profile_image_url
            },
            "analysis": {
                "profile_analysis": profile_analysis,
                "posts_analysis": posts_analysis,
                "comments_analysis": comments_analysis,
                "summary": summary
            },
            "raw_data": {
                "profile_data": profile_data,
                "posts_data": posts_data,
                "comments_data": comments_data
            }
        }
    
    def _extract_username_from_url(self, linkedin_url: str) -> Optional[str]:
        """Extract username from LinkedIn URL."""
        match = re.search(r'linkedin\.com/in/([^/]+)', linkedin_url)
        if not match:
            return None
        return match.group(1)
    
    def _extract_linkedin_profile_data(self, linkedin_url: str) -> Dict[str, Any]:
        """Extract profile data from LinkedIn URL using LinkedIn API client."""
        username = self._extract_username_from_url(linkedin_url)
        if not username:
            raise ValueError(f"Could not extract username from LinkedIn URL: {linkedin_url}")
        
        # Use the LinkedInAPIClient to get profile data
        api_context = {
            'endpoint': '',
            'params': {'username': username}
        }
        response = self.linkedin_client.get_response(api_context)
        data = response.json()
        geo = data.get('geo', {})
        
        # Process and return the data
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        
        return {
            "full_name": f"{first_name} {last_name}".strip(),
            "first_name": first_name,
            "last_name": last_name,
            "username": data.get('username', ''),
            "location": f'{geo.get("city", "")}, {geo.get("country", "")}',
            "headline": data.get('headline', ''),
            "summary": data.get('summary', ''),
            "current_role": data.get('position', [])[0].get('title', '') if data.get('position') else '',
            "current_company": data.get('position', [])[0].get('companyName', '') if data.get('position') else '',
            "work_history": [
                {
                    'company': exp.get('companyName', ''),
                    'title': exp.get('title', ''),
                    'description': exp.get('description', ''),
                    'start_date': exp.get('start', {}),
                    'end_date': exp.get('end', {}),
                    'location': exp.get('location', '')
                }
                for exp in data.get('position', [])
            ],
            "education": [
                {
                    'school': edu.get('schoolName', ''),
                    'degree': edu.get('degree', ''),
                    'field': edu.get('fieldOfStudy', ''),
                    'start_date': edu.get('start', {}),
                    'end_date': edu.get('end', {})
                }
                for edu in data.get('educations', [])
            ],
            "associations": data.get('associations', []),
            "causes": data.get('causes', []),
            "skills": [
                {
                    'name': skill.get('name', ''),
                    'endorsements': skill.get('endorsementsCount', 0)
                }
                for skill in data.get('skills', [])
            ]
        }
    
    def _extract_linkedin_profile_image(self, linkedin_url: str) -> Optional[str]:
        """Extract profile image URL from LinkedIn URL using LinkedIn API client."""
        username = self._extract_username_from_url(linkedin_url)
        if not username:
            return None
        
        api_context = {
            'endpoint': '',
            'params': {'username': username}
        }
        response = self.linkedin_client.get_response(api_context)
        data = response.json()
        return data.get('profilePicture')
    
    def _extract_linkedin_posts(self, linkedin_url: str) -> List[Dict[str, Any]]:
        """Extract posts from LinkedIn URL using LinkedIn API client."""
        username = self._extract_username_from_url(linkedin_url)
        if not username:
            return []
        
        api_context = {
            'endpoint': 'get-profile-posts',
            'params': {'username': username}
        }
        response = self.linkedin_client.get_response(api_context)
        data = response.json()
        
        # Process posts, excluding reposts and limiting to 25
        posts = []
        for post in data.get('data', []):
            if len(posts) >= 25:
                break
                
            if post.get('reposted', False):
                continue
                
            posts.append({
                'text': post.get('text', ''),
                'url': post.get('postUrl', ''),
                'date': post.get('postedDate', '')
            })
            
        return posts
    
    def _extract_linkedin_comments(self, username: str) -> List[Dict[str, Any]]:
        """Extract comments from LinkedIn username using LinkedIn API client."""
        api_context = {
            'endpoint': 'get-profile-comments',
            'params': {'username': username}
        }
        response = self.linkedin_client.get_response(api_context)
        data = response.json()
        
        comments = []
        for comment in data.get('data', []):
            if len(comments) >= 25:
                break
                
            comment_text = ''
            try:
                comment_text = comment.get('highlightedComments', [])[0]
            except (IndexError, TypeError):
                continue
                
            comments.append({
                'text': comment_text,
                'url': comment.get('commentUrl', ''),
                'date': comment.get('commentedDate', ''),
                'post': {
                    'text': comment.get('text', ''),
                    'url': comment.get('postUrl', ''),
                    'date': comment.get('postedDate', '')
                }
            })
            
        return comments
    
    def _build_profile_prompt(self, profile_data: Dict[str, Any]) -> str:
        """Build prompt for profile analysis."""
        return f"""Based on the information about this person, please answer the questions below in as much detail that is present in the given information:  

## Rules:

* Give an extremely detailed break down including all relevant information related to the questions
* Omit any pre-text and post text, just output the report and nothing else

## Questions:

List the persons name
List the persons location
List the persons work history
List the persons education
List an associations shown in the data
List any Charities, Boards and Causes present in the data  

## Information:
{json.dumps(profile_data, indent=2)}
"""
    
    def _build_posts_prompt(self, posts: List[Dict[str, Any]], first_name: str) -> str:
        """Build prompt for posts analysis."""
        formatted_posts = json.dumps(posts, indent=2, ensure_ascii=False)
        return f"""Based on this users posts, provide answer to the questions below. Always use the persons name and refer to them by their name which is {first_name}.   

## Rules:

* Give an extremely detailed break down including all relevant information related to the questions
* Always specify which post(s) the information came from and hyperlink it with the post URL
* Always output the date (MM-DD-YY) the post was made on for every reference
* Omit any pre-text and post text, just output the report and nothing else
* If information regarding a question below is not available from {first_name}'s posts, omit that section from the report
* Do not make up any information

## Questions:

 1. What are {first_name}'s main interests?
 2. What are {first_name}'s main hobbies outside of work?
 3. List any people they associate with
 4. What are {first_name}'s current professional goals and aspirations?
 5. What key challenges or pain points does {first_name} discuss in their field or industry?
 6. What recent accomplishments or recognitions has {first_name} shared?
 7. What topics or causes does {first_name} support or advocate for?
 8. What are some recent events, conferences, or webinars {first_name} has attended or mentioned?
 9. Has {first_name} discussed any future trends they are excited about or watching closely?
10. What specific skills or areas of expertise does {first_name} showcase in their posts?
11. How does {first_name} position themselves as a thought leader in their industry?

## Posts:
{formatted_posts}
"""
    
    def _build_comments_prompt(self, comments: List[Dict[str, Any]], first_name: str) -> str:
        """Build prompt for comments analysis."""
        formatted_comments = json.dumps(comments, indent=2, ensure_ascii=False)
        return f"""Based on this context, answer questions about the commentor, {first_name}.

## Rules:

* always hyperlink the comment text with the comment URL
* Always output the date (MM-DD-YY) the comment was made on for every reference
* Omit any pre-text and post text, just output the report and nothing else
* Give an extremely detailed break down including all relevant information related to the questions
* If information regarding a question below is not available from {first_name}'s posts, omit that section from the report
* Do not make up any information

## Questions:

1. What kind of content does {first_name} typically enjoy, list 3 main interests
2. Do they show any buying intent on posts? if so, list them. Be specific on the context of the post and what the user specifically shows interest in buying.
3. What are the common themes or topics they engage with in others' posts?
4. Are there specific brands, products, or services that {first_name} consistently mentions or endorses?
5. Does {first_name} reveal any key challenges or needs in their comments?
6. What type of questions does {first_name} ask when commenting on others' posts?
7. Does {first_name} reference any personal or professional achievements in comments?

## Context:
{formatted_comments}
"""
    
    def _build_summary_prompt(self, full_name: str, linkedin_data: Dict[str, Any], post_and_comment_data: str) -> str:
        """Build prompt for summary."""
        return f'''
Based on {full_name}'s Linkedin data an research report. Please create a summary about them starting with an overview and then highlighting key points that would be valuable
to know as a salesperson before speaking with them on a call

## Linkedin data:

{json.dumps(linkedin_data, indent=2)}

## Report:

{post_and_comment_data}
'''
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API with a prompt and return the result."""
        response = self.openai_manager.chat(prompt, self.model)
        return response.choices[0].message.content
    
    def _run_parallel_analyses(self, profile_prompt: str, posts_prompt: str, comments_prompt: str) -> tuple:
        """Run analyses in parallel for efficiency."""
        profile_analysis = ""
        posts_analysis = ""
        comments_analysis = ""
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            profile_future = executor.submit(self._call_openai, profile_prompt)
            
            posts_future = None
            if posts_prompt:
                posts_future = executor.submit(self._call_openai, posts_prompt)
                
            comments_future = None
            if comments_prompt:
                comments_future = executor.submit(self._call_openai, comments_prompt)
            
            # Get results
            profile_analysis = profile_future.result()
            
            if posts_future:
                posts_analysis = posts_future.result()
                
            if comments_future:
                comments_analysis = comments_future.result()
                
        return profile_analysis, posts_analysis, comments_analysis