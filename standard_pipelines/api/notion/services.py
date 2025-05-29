"""
Notion API service for making authenticated requests.
"""
from typing import Dict, Any, Optional, List
import requests
from datetime import datetime, timedelta
from flask import current_app

from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.api.notion.models import NotionCredentials


class NotionAPIManager(BaseAPIManager):
    """Manager for Notion API interactions."""
    
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(self, credentials: NotionCredentials):
        """Initialize Notion API manager with credentials."""
        self.credentials = credentials
        self.access_token = credentials.oauth_access_token
        self.workspace_id = credentials.workspace_id
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Notion API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": "2022-06-28",  # Latest stable version
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to Notion API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs
        )
        
        return response
    
    def search(self, query: str, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for pages and databases in the workspace.
        
        Args:
            query: Search query string
            filter_type: Optional filter ('page' or 'database')
            
        Returns:
            Search results
        """
        data = {"query": query}
        if filter_type:
            data["filter"] = {"property": "object", "value": filter_type}
        
        response = self._make_request("POST", "search", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_databases(self) -> List[Dict[str, Any]]:
        """Get all databases in the workspace."""
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            data = {}
            if start_cursor:
                data["start_cursor"] = start_cursor
            
            response = self._make_request("POST", "search", json={
                "filter": {"property": "object", "value": "database"},
                **data
            })
            response.raise_for_status()
            
            result = response.json()
            results.extend(result.get("results", []))
            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")
        
        return results
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get a specific database by ID."""
        response = self._make_request("GET", f"databases/{database_id}")
        response.raise_for_status()
        return response.json()
    
    def query_database(self, database_id: str, filter_obj: Optional[Dict] = None, 
                      sorts: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Query a database with optional filters and sorts.
        
        Args:
            database_id: The database ID to query
            filter_obj: Optional filter object
            sorts: Optional list of sort objects
            
        Returns:
            List of database entries
        """
        data = {}
        if filter_obj:
            data["filter"] = filter_obj
        if sorts:
            data["sorts"] = sorts
        
        results = []
        has_more = True
        start_cursor = None
        
        while has_more:
            if start_cursor:
                data["start_cursor"] = start_cursor
            
            response = self._make_request("POST", f"databases/{database_id}/query", json=data)
            response.raise_for_status()
            
            result = response.json()
            results.extend(result.get("results", []))
            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")
        
        return results
    
    def create_page(self, parent: Dict[str, Any], properties: Dict[str, Any], 
                   children: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a new page in Notion.
        
        Args:
            parent: Parent object (database_id or page_id)
            properties: Page properties
            children: Optional content blocks
            
        Returns:
            Created page object
        """
        data = {
            "parent": parent,
            "properties": properties
        }
        if children:
            data["children"] = children
        
        response = self._make_request("POST", "pages", json=data)
        response.raise_for_status()
        return response.json()
    
    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update a page's properties."""
        response = self._make_request("PATCH", f"pages/{page_id}", json={
            "properties": properties
        })
        response.raise_for_status()
        return response.json()
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a page by ID."""
        response = self._make_request("GET", f"pages/{page_id}")
        response.raise_for_status()
        return response.json()
    
    def get_user(self, user_id: str = "me") -> Dict[str, Any]:
        """Get user information."""
        response = self._make_request("GET", f"users/{user_id}")
        response.raise_for_status()
        return response.json()