"""
AI Team Integrations Module
Supports: Claude AI, ChatGPT, DALL-E, Facebook, Instagram
"""

import anthropic
import openai
import requests
from typing import Dict, List, Optional
import sqlite3
import os
from datetime import datetime

class IntegrationsManager:
    """Manage all third-party integrations"""
    
    def __init__(self):
        self.db_path = 'integrations.db'
        self._init_database()
    
    def _init_database(self):
        """Initialize integrations database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                integration_type TEXT NOT NULL,
                api_key TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expires TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, integration_type)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                integration_type TEXT NOT NULL,
                action TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== CREDENTIAL MANAGEMENT ====================
    
    def save_integration(self, user_id: int, integration_type: str, 
                        api_key: str = None, access_token: str = None,
                        refresh_token: str = None, token_expires: str = None) -> bool:
        """Save or update integration credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_integrations 
                (user_id, integration_type, api_key, access_token, refresh_token, token_expires)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, integration_type) 
                DO UPDATE SET 
                    api_key = COALESCE(excluded.api_key, api_key),
                    access_token = COALESCE(excluded.access_token, access_token),
                    refresh_token = COALESCE(excluded.refresh_token, refresh_token),
                    token_expires = COALESCE(excluded.token_expires, token_expires),
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, integration_type, api_key, access_token, refresh_token, token_expires))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving integration: {e}")
            return False
    
    def get_integration(self, user_id: int, integration_type: str) -> Optional[Dict]:
        """Get integration credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT api_key, access_token, refresh_token, token_expires, is_active
            FROM user_integrations
            WHERE user_id = ? AND integration_type = ?
        """, (user_id, integration_type))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'api_key': row[0],
                'access_token': row[1],
                'refresh_token': row[2],
                'token_expires': row[3],
                'is_active': bool(row[4])
            }
        return None
    
    def get_all_integrations(self, user_id: int) -> List[Dict]:
        """Get all integrations for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT integration_type, is_active, created_at
            FROM user_integrations
            WHERE user_id = ?
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'type': row[0],
                'is_active': bool(row[1]),
                'created_at': row[2]
            }
            for row in rows
        ]
    
    def delete_integration(self, user_id: int, integration_type: str) -> bool:
        """Delete integration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM user_integrations
                WHERE user_id = ? AND integration_type = ?
            """, (user_id, integration_type))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting integration: {e}")
            return False
    
    # ==================== CLAUDE AI ====================
    
    def call_claude(self, user_id: int, prompt: str, model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
        """Call Claude AI API"""
        integration = self.get_integration(user_id, 'claude')
        if not integration or not integration['api_key']:
            return None
        
        try:
            client = anthropic.Anthropic(api_key=integration['api_key'])
            
            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            
            # Log usage
            self._log_usage(user_id, 'claude', 'chat', 
                          tokens_used=message.usage.input_tokens + message.usage.output_tokens)
            
            return response_text
        except Exception as e:
            print(f"Claude API error: {e}")
            return f"Error calling Claude: {str(e)}"
    
    # ==================== CHATGPT ====================
    
    def call_chatgpt(self, user_id: int, prompt: str, model: str = "gpt-4") -> Optional[str]:
        """Call ChatGPT API"""
        integration = self.get_integration(user_id, 'openai')
        if not integration or not integration['api_key']:
            return None
        
        try:
            openai.api_key = integration['api_key']
            
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
            
            response_text = response.choices[0].message.content
            
            # Log usage
            self._log_usage(user_id, 'openai', 'chat',
                          tokens_used=response.usage.total_tokens)
            
            return response_text
        except Exception as e:
            print(f"ChatGPT API error: {e}")
            return f"Error calling ChatGPT: {str(e)}"
    
    # ==================== DALL-E ====================
    
    def generate_image(self, user_id: int, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """Generate image with DALL-E"""
        integration = self.get_integration(user_id, 'openai')
        if not integration or not integration['api_key']:
            return None
        
        try:
            openai.api_key = integration['api_key']
            
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size=size
            )
            
            image_url = response.data[0].url
            
            # Log usage
            self._log_usage(user_id, 'openai', 'image_generation')
            
            return image_url
        except Exception as e:
            print(f"DALL-E API error: {e}")
            return None
    
    # ==================== FACEBOOK ====================
    
    def post_to_facebook(self, user_id: int, message: str, image_url: str = None) -> Optional[str]:
        """Post to Facebook"""
        integration = self.get_integration(user_id, 'facebook')
        if not integration or not integration['access_token']:
            return None
        
        try:
            # Facebook Graph API endpoint
            url = f"https://graph.facebook.com/v18.0/me/feed"
            
            payload = {
                'message': message,
                'access_token': integration['access_token']
            }
            
            if image_url:
                payload['link'] = image_url
            
            response = requests.post(url, data=payload)
            result = response.json()
            
            if 'id' in result:
                # Log usage
                self._log_usage(user_id, 'facebook', 'post')
                return result['id']
            else:
                print(f"Facebook error: {result}")
                return None
        except Exception as e:
            print(f"Facebook API error: {e}")
            return None
    
    def get_facebook_posts(self, user_id: int, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent Facebook posts"""
        integration = self.get_integration(user_id, 'facebook')
        if not integration or not integration['access_token']:
            return None
        
        try:
            url = f"https://graph.facebook.com/v18.0/me/posts"
            params = {
                'access_token': integration['access_token'],
                'limit': limit,
                'fields': 'id,message,created_time,likes.summary(true),comments.summary(true)'
            }
            
            response = requests.get(url, params=params)
            result = response.json()
            
            if 'data' in result:
                return result['data']
            return None
        except Exception as e:
            print(f"Facebook API error: {e}")
            return None
    
    # ==================== INSTAGRAM ====================
    
    def post_to_instagram(self, user_id: int, image_url: str, caption: str) -> Optional[str]:
        """Post to Instagram"""
        integration = self.get_integration(user_id, 'instagram')
        if not integration or not integration['access_token']:
            return None
        
        try:
            # Instagram Graph API - Create container
            url = f"https://graph.facebook.com/v18.0/me/media"
            
            payload = {
                'image_url': image_url,
                'caption': caption,
                'access_token': integration['access_token']
            }
            
            response = requests.post(url, data=payload)
            result = response.json()
            
            if 'id' in result:
                # Publish the container
                container_id = result['id']
                publish_url = f"https://graph.facebook.com/v18.0/me/media_publish"
                publish_payload = {
                    'creation_id': container_id,
                    'access_token': integration['access_token']
                }
                
                publish_response = requests.post(publish_url, data=publish_payload)
                publish_result = publish_response.json()
                
                if 'id' in publish_result:
                    # Log usage
                    self._log_usage(user_id, 'instagram', 'post')
                    return publish_result['id']
            
            return None
        except Exception as e:
            print(f"Instagram API error: {e}")
            return None
    
    def get_instagram_posts(self, user_id: int, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent Instagram posts"""
        integration = self.get_integration(user_id, 'instagram')
        if not integration or not integration['access_token']:
            return None
        
        try:
            url = f"https://graph.facebook.com/v18.0/me/media"
            params = {
                'access_token': integration['access_token'],
                'limit': limit,
                'fields': 'id,caption,media_type,media_url,timestamp,like_count,comments_count'
            }
            
            response = requests.get(url, params=params)
            result = response.json()
            
            if 'data' in result:
                return result['data']
            return None
        except Exception as e:
            print(f"Instagram API error: {e}")
            return None
    
    # ==================== USAGE TRACKING ====================
    
    def _log_usage(self, user_id: int, integration_type: str, action: str, 
                   tokens_used: int = 0, cost: float = 0.0):
        """Log integration usage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO integration_usage 
                (user_id, integration_type, action, tokens_used, cost)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, integration_type, action, tokens_used, cost))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging usage: {e}")
    
    def get_usage_stats(self, user_id: int, integration_type: str = None) -> List[Dict]:
        """Get usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if integration_type:
            cursor.execute("""
                SELECT integration_type, action, COUNT(*) as count, 
                       SUM(tokens_used) as total_tokens, SUM(cost) as total_cost
                FROM integration_usage
                WHERE user_id = ? AND integration_type = ?
                GROUP BY integration_type, action
            """, (user_id, integration_type))
        else:
            cursor.execute("""
                SELECT integration_type, action, COUNT(*) as count,
                       SUM(tokens_used) as total_tokens, SUM(cost) as total_cost
                FROM integration_usage
                WHERE user_id = ?
                GROUP BY integration_type, action
            """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'integration': row[0],
                'action': row[1],
                'count': row[2],
                'total_tokens': row[3] or 0,
                'total_cost': row[4] or 0.0
            }
            for row in rows
        ]

# Singleton instance
integrations_manager = IntegrationsManager()
