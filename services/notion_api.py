# notion_api.py
# Functions to interact with Notion API - SQLite version

import requests
import sqlite3
from typing import Optional, Dict, List

NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE = "https://api.notion.com/v1"

def get_db_connection():
    """Get connection to users database"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

class NotionAPI:
    """Helper class for Notion API interactions"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json"
        }
    
    def search(self, query: str = "", filter_type: Optional[str] = None) -> Dict:
        """
        Search for pages and databases in Notion workspace
        
        Args:
            query: Search query string
            filter_type: "page" or "database" to filter results
        
        Returns:
            Dictionary with search results
        """
        url = f"{NOTION_API_BASE}/search"
        payload = {}
        
        if query:
            payload["query"] = query
        
        if filter_type:
            payload["filter"] = {"property": "object", "value": filter_type}
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Notion search error: {str(e)}")
            return {"results": [], "error": str(e)}
    
    def get_page(self, page_id: str) -> Dict:
        """Get a specific page by ID"""
        url = f"{NOTION_API_BASE}/pages/{page_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Notion get_page error: {str(e)}")
            return {"error": str(e)}
    
    def get_page_content(self, page_id: str) -> Dict:
        """Get the content blocks of a page"""
        url = f"{NOTION_API_BASE}/blocks/{page_id}/children"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Notion get_page_content error: {str(e)}")
            return {"results": [], "error": str(e)}
    
    def query_database(self, database_id: str, filter_params: Optional[Dict] = None) -> Dict:
        """Query a database with optional filters"""
        url = f"{NOTION_API_BASE}/databases/{database_id}/query"
        payload = {}
        
        if filter_params:
            payload["filter"] = filter_params
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Notion query_database error: {str(e)}")
            return {"results": [], "error": str(e)}
    
    def extract_text_from_blocks(self, blocks: List[Dict]) -> str:
        """Extract plain text from Notion blocks"""
        text_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                            "bulleted_list_item", "numbered_list_item"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                for text_obj in rich_text:
                    text_parts.append(text_obj.get("plain_text", ""))
            
            elif block_type == "code":
                rich_text = block.get("code", {}).get("rich_text", [])
                for text_obj in rich_text:
                    text_parts.append(text_obj.get("plain_text", ""))
            
            elif block_type == "quote":
                rich_text = block.get("quote", {}).get("rich_text", [])
                for text_obj in rich_text:
                    text_parts.append(text_obj.get("plain_text", ""))
        
        return "\n".join(text_parts)
    
    def get_page_text(self, page_id: str) -> str:
        """Get all text content from a page"""
        content = self.get_page_content(page_id)
        blocks = content.get("results", [])
        return self.extract_text_from_blocks(blocks)


def get_user_notion_api(user_id: int) -> Optional[NotionAPI]:
    """
    Get NotionAPI instance for a specific user
    
    Args:
        user_id: User ID to get Notion integration for
    
    Returns:
        NotionAPI instance if user has active integration, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT access_token 
        FROM notion_integrations 
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return NotionAPI(result['access_token'])
    return None


def search_user_notion(user_id: int, query: str, filter_type: Optional[str] = None) -> Dict:
    """
    Search user's Notion workspace
    
    Args:
        user_id: User ID
        query: Search query
        filter_type: "page" or "database"
    
    Returns:
        Search results dictionary
    """
    notion_api = get_user_notion_api(user_id)
    
    if not notion_api:
        return {"error": "Notion not connected", "results": []}
    
    return notion_api.search(query, filter_type)


def get_user_notion_page_content(user_id: int, page_id: str) -> str:
    """
    Get text content from a user's Notion page
    
    Args:
        user_id: User ID
        page_id: Notion page ID
    
    Returns:
        Plain text content of the page
    """
    notion_api = get_user_notion_api(user_id)
    
    if not notion_api:
        return "Error: Notion not connected"
    
    return notion_api.get_page_text(page_id)


# Example usage in agent routes:
"""
from services.notion_api import search_user_notion, get_user_notion_page_content

# Search user's Notion
results = search_user_notion(current_user.id, "project planning", filter_type="page")

# Get specific page content
page_text = get_user_notion_page_content(current_user.id, "page-id-here")
"""
