"""
Prompts for LinkedIn analysis with OpenAI.
"""
import json
from flask import current_app
from typing import Dict, Any, List


def build_profile_prompt(profile_data: Dict[str, Any]) -> str:
    """
    Builds the profile analysis prompt with the given profile data.
    
    Args:
        profile_data: Dictionary containing LinkedIn profile information
        
    Returns:
        str: Formatted prompt for profile analysis
    """
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


def build_posts_prompt(posts: List[Dict[str, Any]], first_name: str) -> str:
    """
    Builds the posts analysis prompt with the given posts data.
    
    Args:
        posts: List of post dictionaries
        first_name: First name of the LinkedIn user
        
    Returns:
        str: Formatted prompt for posts analysis
    """
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


def build_comments_prompt(comments: List[Dict[str, Any]], first_name: str) -> str:
    """
    Builds the comments analysis prompt with the given comments data.
    
    Args:
        comments: List of comment dictionaries
        first_name: First name of the LinkedIn user
        
    Returns:
        str: Formatted prompt for comments analysis
    """
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


def build_summary_prompt(full_name: str, linkedin_data: Dict[str, Any], post_and_comment_data: str) -> str:
    """
    Builds the summary prompt with the given responses.
    
    Args:
        full_name: Full name of the LinkedIn user
        linkedin_data: Dictionary containing LinkedIn profile information
        post_and_comment_data: Combined posts and comments analysis
        
    Returns:
        str: Formatted prompt for summary
    """
    return f'''
Based on {full_name}'s Linkedin data an research report. Please create a summary about them starting with an overview and then highlighting key points that would be valuable
to know as a salesperson before speaking with them on a call

## Linkedin data:

{json.dumps(linkedin_data, indent=2)}

## Report:

{post_and_comment_data}
'''