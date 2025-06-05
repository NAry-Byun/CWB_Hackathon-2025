# services/notion_service.py - Complete Enhanced Notion Service with Content Reading

import requests
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self):
        self.notion_token = os.getenv('NOTION_API_TOKEN')
        self.notion_version = '2022-06-28'
        self.base_url = 'https://api.notion.com/v1'
        
        if not self.notion_token:
            raise ValueError("NOTION_API_TOKEN environment variable is required")
        
        self.headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Notion-Version': self.notion_version,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"🟣 NotionService initialized (API version {self.notion_version})")

    def search_pages(self, query: str) -> List[Dict]:
        """Search for Notion pages by title using requests (sync)"""
        try:
            url = f"{self.base_url}/search"
            data = {
                "query": query,
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            
            results = response.json().get('results', [])
            logger.info(f"✅ Found {len(results)} pages in Notion search")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error searching Notion pages: {e}")
            return []

    def get_page_content(self, page_id: str) -> str:
        """Get the actual content of a Notion page"""
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            blocks = response.json().get('results', [])
            content_parts = []
            
            for block in blocks:
                block_content = self._extract_block_content(block)
                if block_content:
                    content_parts.append(block_content)
            
            full_content = '\n'.join(content_parts)
            logger.info(f"✅ Retrieved content for page {page_id}: {len(full_content)} characters")
            return full_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting page content: {e}")
            return ""

    def _extract_block_content(self, block: Dict) -> str:
        """Extract text content from a Notion block"""
        try:
            block_type = block.get('type', '')
            block_data = block.get(block_type, {})
            
            # Handle different block types
            if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
                rich_text = block_data.get('rich_text', [])
                return self._extract_rich_text(rich_text)
            
            elif block_type == 'bulleted_list_item':
                rich_text = block_data.get('rich_text', [])
                text = self._extract_rich_text(rich_text)
                return f"• {text}" if text else ""
            
            elif block_type == 'numbered_list_item':
                rich_text = block_data.get('rich_text', [])
                text = self._extract_rich_text(rich_text)
                return f"1. {text}" if text else ""
            
            elif block_type == 'to_do':
                rich_text = block_data.get('rich_text', [])
                checked = block_data.get('checked', False)
                text = self._extract_rich_text(rich_text)
                checkbox = "☑️" if checked else "☐"
                return f"{checkbox} {text}" if text else ""
            
            elif block_type == 'table':
                return "[Table content]"
            
            elif block_type == 'callout':
                rich_text = block_data.get('rich_text', [])
                return f"💡 {self._extract_rich_text(rich_text)}"
            
            else:
                # For unknown block types, try to extract any rich_text
                if 'rich_text' in block_data:
                    return self._extract_rich_text(block_data['rich_text'])
                
            return ""
            
        except Exception as e:
            logger.error(f"❌ Error extracting block content: {e}")
            return ""

    def _extract_rich_text(self, rich_text_array: List[Dict]) -> str:
        """Extract plain text from Notion rich text array"""
        try:
            text_parts = []
            for text_obj in rich_text_array:
                if text_obj.get('type') == 'text':
                    content = text_obj.get('text', {}).get('content', '')
                    text_parts.append(content)
            return ''.join(text_parts)
        except Exception as e:
            logger.error(f"❌ Error extracting rich text: {e}")
            return ""

    def search_meeting_pages(self, query: str) -> List[Dict]:
        """Search for meeting-related pages with content"""
        try:
            # Search for pages
            pages = self.search_pages(query)
            
            enhanced_pages = []
            for page in pages:
                try:
                    page_id = page.get('id', '')
                    page_title = self._extract_page_title(page)
                    
                    # Get page content
                    content = self.get_page_content(page_id)
                    
                    # Enhanced page info
                    enhanced_page = {
                        'id': page_id,
                        'title': page_title,
                        'url': page.get('url', ''),
                        'last_edited_time': page.get('last_edited_time', ''),
                        'created_time': page.get('created_time', ''),
                        'content': content,
                        'content_preview': content[:500] + "..." if len(content) > 500 else content
                    }
                    
                    enhanced_pages.append(enhanced_page)
                    logger.info(f"✅ Retrieved content for page: {page_title}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing page {page.get('id', 'unknown')}: {e}")
                    # Add page without content as fallback
                    enhanced_pages.append({
                        'id': page.get('id', ''),
                        'title': self._extract_page_title(page),
                        'url': page.get('url', ''),
                        'last_edited_time': page.get('last_edited_time', ''),
                        'created_time': page.get('created_time', ''),
                        'content': 'Unable to load content',
                        'content_preview': 'Content loading failed'
                    })
            
            logger.info(f"✅ Found {len(enhanced_pages)} meeting-related pages with content")
            return enhanced_pages
            
        except Exception as e:
            logger.error(f"❌ Error searching meeting pages: {e}")
            return []

    def get_page_by_title(self, title: str) -> Optional[Dict]:
        """Find a specific page by exact title match"""
        # Try different search variations
        search_queries = [
            title,
            title.replace('(', '').replace(')', ''),  # Remove parentheses
            title.split('(')[0].strip(),  # Just the part before parentheses
            title.lower(),
            title.title()
        ]
        
        for query in search_queries:
            pages = self.search_pages(query)
            
            for page in pages:
                page_title = self._extract_page_title(page)
                if page_title.lower() == title.lower():
                    logger.info(f"✅ Found exact match: '{page_title}'")
                    return page
                
                # Partial match for pages with dates/parentheses
                if title.lower() in page_title.lower() or page_title.lower() in title.lower():
                    logger.info(f"✅ Found partial match: '{page_title}' for '{title}'")
                    return page
        
        logger.warning(f"❌ No page found for title: '{title}'")
        return None

    def _extract_page_title(self, page: Dict) -> str:
        """Extract title from page object"""
        try:
            properties = page.get('properties', {})
            
            # Try different title property names
            for title_key in ['title', 'Title', 'Name', 'name']:
                if title_key in properties:
                    title_property = properties[title_key]
                    if title_property.get('type') == 'title':
                        title_array = title_property.get('title', [])
                        if title_array:
                            return title_array[0].get('plain_text', '')
            
            # Fallback to page title in object
            if 'title' in page:
                title_array = page['title']
                if title_array:
                    return title_array[0].get('plain_text', '')
                    
            return 'Untitled'
            
        except Exception as e:
            logger.error(f"❌ Error extracting page title: {e}")
            return 'Untitled'

    def add_text_to_page(self, page_id: str, text: str, formatting: str = 'paragraph') -> bool:
        """Add text content to a Notion page"""
        try:
            url = f"{self.base_url}/blocks/{page_id}/children"
            
            # Create block based on formatting type
            block = self._create_text_block(text, formatting)
            
            data = {
                "children": [block]
            }
            
            logger.info(f"🟣 Adding text to page {page_id}: '{text}'")
            response = requests.patch(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            
            logger.info(f"✅ Successfully added text to page {page_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error adding text to Notion page: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"❌ Response: {e.response.text}")
            return False

    def _create_text_block(self, text: str, formatting: str) -> Dict:
        """Create a Notion block object based on formatting type"""
        
        if formatting == 'heading_1' or text.startswith('# '):
            clean_text = text.replace('# ', '') if text.startswith('# ') else text
            return {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": clean_text}}]
                }
            }
        
        elif formatting == 'heading_2' or text.startswith('## '):
            clean_text = text.replace('## ', '') if text.startswith('## ') else text
            return {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": clean_text}}]
                }
            }
        
        elif formatting == 'bulleted_list' or text.startswith(('• ', '- ', '* ')):
            clean_text = text.replace('• ', '').replace('- ', '').replace('* ', '') if text.startswith(('• ', '- ', '* ')) else text
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": clean_text}}]
                }
            }
        
        else:
            # Default to paragraph
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

    def add_text_by_page_title(self, page_title: str, text: str, formatting: str = 'paragraph') -> Dict[str, Any]:
        """Add text to a page by searching for it by title"""
        try:
            logger.info(f"🔍 Searching for page: '{page_title}'")
            
            # Find the page
            page = self.get_page_by_title(page_title)
            
            if not page:
                return {
                    "success": False,
                    "error": f"Page '{page_title}' not found",
                    "suggestion": "Please check the page title or make sure the page exists and is shared with the integration"
                }
            
            page_id = page['id']
            actual_title = self._extract_page_title(page)
            
            logger.info(f"✅ Found page: '{actual_title}' (ID: {page_id})")
            
            # Add the text
            success = self.add_text_to_page(page_id, text, formatting)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully added text to '{actual_title}'",
                    "page_id": page_id,
                    "page_url": page.get('url', ''),
                    "added_content": text,
                    "page_title": actual_title
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add text to the page",
                    "suggestion": "Check your Notion permissions and try again"
                }
                
        except Exception as e:
            logger.error(f"❌ Error in add_text_by_page_title: {e}")
            return {
                "success": False,
                "error": str(e),
                "suggestion": "Please try again or contact support"
            }

    def extract_meetings_from_content(self, content: str) -> List[Dict]:
        """Extract meeting information from page content"""
        meetings = []
        
        try:
            lines = content.split('\n')
            current_meeting = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for meeting patterns
                if any(keyword in line.lower() for keyword in ['meeting', '회의', 'call', '미팅']):
                    if current_meeting:
                        meetings.append(current_meeting)
                        current_meeting = {}
                    
                    current_meeting['title'] = line
                
                # Look for date patterns
                elif any(keyword in line.lower() for keyword in ['date:', 'time:', '날짜:', '시간:', 'when:']):
                    current_meeting['datetime'] = line
                
                # Look for location patterns
                elif any(keyword in line.lower() for keyword in ['location:', 'zoom', 'teams', '장소:']):
                    current_meeting['location'] = line
                
                # Look for participant patterns
                elif any(keyword in line.lower() for keyword in ['attendees:', 'participants:', '참석자:']):
                    current_meeting['participants'] = line
            
            # Add the last meeting if exists
            if current_meeting:
                meetings.append(current_meeting)
            
            logger.info(f"✅ Extracted {len(meetings)} meetings from content")
            return meetings
            
        except Exception as e:
            logger.error(f"❌ Error extracting meetings: {e}")
            return []

    def get_meetings_for_month(self, month: str, year: str = None) -> List[Dict]:
        """Get all meetings for a specific month"""
        try:
            if not year:
                year = str(datetime.now().year)
            
            # Search for calendar pages
            search_terms = [f"{month} {year}", f"calendar {month}", f"meeting {month}"]
            
            all_meetings = []
            
            for term in search_terms:
                pages = self.search_meeting_pages(term)
                
                for page in pages:
                    content = page.get('content', '')
                    meetings = self.extract_meetings_from_content(content)
                    
                    # Add page context to meetings
                    for meeting in meetings:
                        meeting['source_page'] = page.get('title', 'Unknown')
                        meeting['page_url'] = page.get('url', '')
                        all_meetings.append(meeting)
            
            # Remove duplicates
            unique_meetings = []
            seen_titles = set()
            
            for meeting in all_meetings:
                title = meeting.get('title', '').lower()
                if title and title not in seen_titles:
                    unique_meetings.append(meeting)
                    seen_titles.add(title)
            
            logger.info(f"✅ Found {len(unique_meetings)} unique meetings for {month} {year}")
            return unique_meetings
            
        except Exception as e:
            logger.error(f"❌ Error getting meetings for {month}: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check Notion service health"""
        try:
            # Test basic search
            test_results = self.search_pages("test")
            
            return {
                "status": "healthy",
                "service": "Notion",
                "api_version": self.notion_version,
                "can_search": True,
                "search_test_results": len(test_results),
                "token_configured": bool(self.notion_token)
            }
            
        except Exception as e:
            logger.error(f"❌ Notion health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "Notion",
                "error": str(e),
                "token_configured": bool(self.notion_token)
            }