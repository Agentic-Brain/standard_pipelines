"""
LinkedIn data structures for structured data handling.
These are not database models, just data containers.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re
import json


@dataclass
class LinkedInPost:
    """A simplified representation of a LinkedIn post."""
    post_text: str
    url: str
    date: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.post_text,
            'url': self.url,
            'date': self.date
        }


@dataclass
class LinkedInComment:
    """A simplified representation of a LinkedIn comment with its parent post."""
    comment_text: str
    url: str
    date: str
    post_text: str
    post_url: str
    post_date: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.comment_text,
            'url': self.url,
            'date': self.date,
            'post': {
                'text': self.post_text,
                'url': self.post_url,
                'date': self.post_date
            }
        }


@dataclass
class LinkedInProfile:
    """A structured representation of a LinkedIn profile."""
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    location: str = ""
    headline: str = ""
    summary: str = ""
    current_role: str = ""
    current_company: str = ""
    work_history: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    associations: List[str] = field(default_factory=list)
    causes: List[str] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization."""
        return {
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'location': self.location,
            'headline': self.headline,
            'summary': self.summary,
            'current_role': self.current_role,
            'current_company': self.current_company,
            'work_history': [
                {
                    'company': job.get('company', ''),
                    'title': job.get('title', ''),
                    'description': job.get('description', ''),
                    'start_date': {
                        'year': job.get('start_date', {}).get('year', ''),
                        'month': job.get('start_date', {}).get('month', '')
                    },
                    'end_date': {
                        'year': job.get('end_date', {}).get('year', ''),
                        'month': job.get('end_date', {}).get('month', '')
                    },
                    'location': job.get('location', '')
                }
                for job in self.work_history
            ],
            'education': [
                {
                    'school': edu.get('school', ''),
                    'degree': edu.get('degree', ''),
                    'field': edu.get('field', ''),
                    'start_date': {
                        'year': edu.get('start_date', {}).get('year', ''),
                        'month': edu.get('start_date', {}).get('month', '')
                    },
                    'end_date': {
                        'year': edu.get('end_date', {}).get('year', ''),
                        'month': edu.get('end_date', {}).get('month', '')
                    }
                }
                for edu in self.education
            ],
            'associations': self.associations,
            'causes': self.causes,
            'skills': [
                {
                    'name': skill.get('name', ''),
                    'endorsements': skill.get('endorsements', 0)
                }
                for skill in self.skills
            ]
        }


@dataclass
class LinkedInAnalysis:
    """
    Container for LinkedIn analysis results.
    This is what gets passed to CRM integrations.
    """
    profile_data: LinkedInProfile
    profile_image_url: Optional[str] = None
    profile_analysis: Optional[str] = None
    posts_analysis: Optional[str] = None
    comments_analysis: Optional[str] = None
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for JSON serialization."""
        return {
            'profile': self.profile_data.to_dict(),
            'profile_image_url': self.profile_image_url,
            'analysis': {
                'profile_analysis': self.profile_analysis,
                'posts_analysis': self.posts_analysis,
                'comments_analysis': self.comments_analysis,
                'summary': self.summary
            }
        }
        
    def get_full_name(self) -> str:
        """Get the full name of the profile."""
        return self.profile_data.full_name
        
    def get_first_name(self) -> str:
        """Get the first name of the profile."""
        return self.profile_data.first_name
        
    def get_last_name(self) -> str:
        """Get the last name of the profile."""
        return self.profile_data.last_name
        
    def get_current_role(self) -> str:
        """Get the current role of the profile."""
        return self.profile_data.current_role
        
    def get_current_company(self) -> str:
        """Get the current company of the profile."""
        return self.profile_data.current_company
        
    def get_location(self) -> str:
        """Get the location of the profile."""
        return self.profile_data.location