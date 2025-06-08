import requests
import json
import os
import re
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
        
        logger.info(f"🟣 Enhanced NotionService initialized (API version {self.notion_version})")

    async def search_pages_and_content(self, query: str, limit: int = 50) -> List[Dict]:
        """Enhanced search: Search BOTH titles AND content, return all matching content"""
        try:
            logger.info(f"🔍 Enhanced search for: '{query}' (searching titles AND content)")
            
            # Step 1: Get all pages (broader search)
            all_pages = self._get_all_accessible_pages(limit)
            
            matching_results = []
            search_terms = self._prepare_search_terms(query)
            
            for page in all_pages:
                try:
                    page_id = page.get('id', '')
                    page_title = self._extract_page_title(page)
                    
                    # Get full page content
                    content = self.get_page_content(page_id)
                    
                    # Check if query matches title OR content
                    title_match = self._matches_search_terms(page_title, search_terms)
                    content_match = self._matches_search_terms(content, search_terms)
                    
                    if title_match or content_match:
                        # Extract matching snippets
                        content_snippets = self._extract_matching_snippets(content, search_terms)
                        
                        result = {
                            'id': page_id,
                            'title': page_title,
                            'url': page.get('url', ''),
                            'last_edited_time': page.get('last_edited_time', ''),
                            'created_time': page.get('created_time', ''),
                            'full_content': content,  # Full content for AI context
                            'content_snippets': content_snippets,  # Highlighted snippets
                            'match_score': self._calculate_match_score(page_title, content, search_terms),
                            'match_type': 'both' if title_match and content_match else ('title' if title_match else 'content'),
                            'content_length': len(content)
                        }
                        
                        matching_results.append(result)
                        logger.info(f"✅ Match found: '{page_title}' (score: {result['match_score']:.2f})")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing page {page.get('id', 'unknown')}: {e}")
                    continue
            
            # Sort by match score (highest first)
            matching_results.sort(key=lambda x: x['match_score'], reverse=True)
            
            logger.info(f"✅ Enhanced search completed: {len(matching_results)} matches found")
            return matching_results
            
        except Exception as e:
            logger.error(f"❌ Enhanced search failed: {e}")
            return []

    def _get_all_accessible_pages(self, limit: int = 50) -> List[Dict]:
        """Get all accessible pages with broader search"""
        try:
            # Use empty query to get more pages
            url = f"{self.base_url}/search"
            data = {
                "filter": {
                    "value": "page",
                    "property": "object"
                },
                "page_size": min(limit, 100)  # Notion API limit
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=15)
            response.raise_for_status()
            
            results = response.json().get('results', [])
            logger.info(f"📄 Retrieved {len(results)} pages for content search")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting pages: {e}")
            return []

    def _prepare_search_terms(self, query: str) -> List[str]:
        """Prepare search terms for better matching"""
        # Split query into individual terms
        terms = re.findall(r'\b\w+\b', query.lower())
        
        # Add the full query as well
        search_terms = [query.lower()] + terms
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen and len(term) > 1:  # Skip single characters
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms

    def _matches_search_terms(self, text: str, search_terms: List[str]) -> bool:
        """Check if text matches any search terms"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(term in text_lower for term in search_terms)

    def _extract_matching_snippets(self, content: str, search_terms: List[str], snippet_length: int = 200) -> List[str]:
        """Extract snippets around matching search terms"""
        snippets = []
        content_lower = content.lower()
        
        for term in search_terms:
            start_pos = 0
            while True:
                pos = content_lower.find(term, start_pos)
                if pos == -1:
                    break
                
                # Extract snippet around the match
                snippet_start = max(0, pos - snippet_length // 2)
                snippet_end = min(len(content), pos + len(term) + snippet_length // 2)
                
                snippet = content[snippet_start:snippet_end].strip()
                
                # Highlight the matching term
                highlighted_snippet = self._highlight_term_in_snippet(snippet, term)
                
                if highlighted_snippet and highlighted_snippet not in snippets:
                    snippets.append(highlighted_snippet)
                
                start_pos = pos + 1
                
                # Limit snippets per term
                if len(snippets) >= 3:
                    break
        
        return snippets

    def _highlight_term_in_snippet(self, snippet: str, term: str) -> str:
        """Highlight search term in snippet"""
        # Simple highlighting with **term**
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        highlighted = pattern.sub(f"**{term}**", snippet)
        return f"...{highlighted}..."

    def _calculate_match_score(self, title: str, content: str, search_terms: List[str]) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        title_lower = title.lower()
        content_lower = content.lower()
        
        for term in search_terms:
            # Title matches get higher score
            if term in title_lower:
                score += 3.0
            
            # Content matches
            content_matches = content_lower.count(term)
            score += content_matches * 0.5
            
            # Exact phrase matches get bonus
            if len(term) > 5 and term in content_lower:
                score += 2.0
        
        # Normalize by content length to favor focused content
        if len(content) > 0:
            score = score / (len(content) / 1000)  # Normalize per 1000 chars
        
        return score

    async def write_long_text_to_page(self, page_id: str, long_text: str, add_timestamp: bool = True) -> Dict[str, Any]:
        """Write long text to Notion page, splitting into multiple blocks if needed"""
        try:
            logger.info(f"📝 Writing long text to page {page_id}: {len(long_text)} characters")
            
            # Add timestamp header if requested
            if add_timestamp:
                timestamp_text = f"## AI Assistant Response - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.add_text_to_page(page_id, timestamp_text, 'heading_2')
            
            # Split long text into manageable chunks
            text_blocks = self._split_long_text_into_blocks(long_text)
            
            successful_blocks = 0
            failed_blocks = 0
            
            for i, block_text in enumerate(text_blocks):
                try:
                    # Determine block formatting
                    formatting = self._detect_text_formatting(block_text)
                    
                    # Add the block
                    success = self.add_text_to_page(page_id, block_text, formatting)
                    
                    if success:
                        successful_blocks += 1
                        logger.debug(f"✅ Block {i+1}/{len(text_blocks)} added successfully")
                    else:
                        failed_blocks += 1
                        logger.warning(f"⚠️ Block {i+1}/{len(text_blocks)} failed to add")
                        
                except Exception as e:
                    failed_blocks += 1
                    logger.error(f"❌ Error adding block {i+1}: {e}")
            
            # Add separator line
            if successful_blocks > 0:
                self.add_text_to_page(page_id, "---", 'paragraph')
            
            return {
                "success": successful_blocks > 0,
                "message": f"Successfully added {successful_blocks}/{len(text_blocks)} text blocks",
                "page_id": page_id,
                "total_blocks": len(text_blocks),
                "successful_blocks": successful_blocks,
                "failed_blocks": failed_blocks,
                "total_text_length": len(long_text)
            }
            
        except Exception as e:
            logger.error(f"❌ Error writing long text: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _split_long_text_into_blocks(self, text: str, max_block_size: int = 1800) -> List[str]:
        """Split long text into blocks suitable for Notion"""
        if len(text) <= max_block_size:
            return [text]
        
        blocks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_block = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would exceed limit
            if len(current_block) + len(paragraph) + 2 > max_block_size:
                if current_block:
                    blocks.append(current_block.strip())
                    current_block = ""
                
                # If single paragraph is too long, split by sentences
                if len(paragraph) > max_block_size:
                    sentences = self._split_by_sentences(paragraph, max_block_size)
                    blocks.extend(sentences)
                else:
                    current_block = paragraph
            else:
                if current_block:
                    current_block += "\n\n" + paragraph
                else:
                    current_block = paragraph
        
        # Add remaining text
        if current_block:
            blocks.append(current_block.strip())
        
        logger.info(f"📄 Split {len(text)} chars into {len(blocks)} blocks")
        return blocks

    def _split_by_sentences(self, text: str, max_size: int) -> List[str]:
        """Split text by sentences when paragraphs are too long"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        blocks = []
        current_block = ""
        
        for sentence in sentences:
            if len(current_block) + len(sentence) + 1 <= max_size:
                if current_block:
                    current_block += " " + sentence
                else:
                    current_block = sentence
            else:
                if current_block:
                    blocks.append(current_block.strip())
                current_block = sentence
        
        if current_block:
            blocks.append(current_block.strip())
        
        return blocks

    def _detect_text_formatting(self, text: str) -> str:
        """Detect appropriate formatting for text block"""
        text_stripped = text.strip()
        
        if text_stripped.startswith('# '):
            return 'heading_1'
        elif text_stripped.startswith('## '):
            return 'heading_2'
        elif text_stripped.startswith(('• ', '- ', '* ')):
            return 'bulleted_list'
        elif re.match(r'^\d+\.', text_stripped):
            return 'numbered_list'
        else:
            return 'paragraph'

    async def write_chatbot_response_to_page(self, page_title: str, chatbot_response: str, user_question: str = None) -> Dict[str, Any]:
        """Write chatbot response to Notion page by title"""
        try:
            logger.info(f"🤖 Writing chatbot response to page: '{page_title}'")
            
            # Find the page
            page = self.get_page_by_title(page_title)
            
            if not page:
                return {
                    "success": False,
                    "error": f"Page '{page_title}' not found",
                    "suggestion": "Please check the page title or create the page first"
                }
            
            page_id = page['id']
            actual_title = self._extract_page_title(page)
            
            # Prepare content to write
            content_to_write = ""
            
            if user_question:
                content_to_write += f"**Question:** {user_question}\n\n"
            
            content_to_write += f"**AI Response:**\n{chatbot_response}"
            
            # Write the long text
            result = await self.write_long_text_to_page(page_id, content_to_write, add_timestamp=True)
            
            if result['success']:
                return {
                    "success": True,
                    "message": f"Chatbot response written to '{actual_title}'",
                    "page_id": page_id,
                    "page_url": page.get('url', ''),
                    "page_title": actual_title,
                    "response_length": len(chatbot_response),
                    "blocks_created": result.get('successful_blocks', 0)
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to write response to page",
                    "details": result
                }
                
        except Exception as e:
            logger.error(f"❌ Error writing chatbot response: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Keep all existing methods...
    async def append_text_to_page(self, page_id: str, text: str) -> Dict[str, Any]:
        """Append text to a Notion page (async wrapper for route compatibility)"""
        try:
            success = self.add_text_to_page(page_id, text)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully appended text to page {page_id}",
                    "page_id": page_id,
                    "appended_text": text
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to append text to page"
                }
                
        except Exception as e:
            logger.error(f"❌ Error in append_text_to_page: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def search_pages(self, query: str) -> List[Dict]:
        """Original search method (kept for compatibility)"""
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
            logger.info(f"✅ Found {len(results)} pages in basic search")
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
            logger.debug(f"✅ Retrieved content for page {page_id}: {len(full_content)} characters")
            return full_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting page content: {e}")
            return ""

    def _extract_block_content(self, block: Dict) -> str:
        """Extract text content from a Notion block"""
        try:
            block_type = block.get('type', '')
            block_data = block.get(block_type, {})
            
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
            
            elif block_type == 'callout':
                rich_text = block_data.get('rich_text', [])
                return f"💡 {self._extract_rich_text(rich_text)}"
            
            else:
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

    def get_page_by_title(self, title: str) -> Optional[Dict]:
        """Find a specific page by exact title match"""
        search_queries = [
            title,
            title.replace('(', '').replace(')', ''),
            title.split('(')[0].strip(),
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
                
                if title.lower() in page_title.lower() or page_title.lower() in title.lower():
                    logger.info(f"✅ Found partial match: '{page_title}' for '{title}'")
                    return page
        
        logger.warning(f"❌ No page found for title: '{title}'")
        return None

    def _extract_page_title(self, page: Dict) -> str:
        """Extract title from page object"""
        try:
            properties = page.get('properties', {})
            
            for title_key in ['title', 'Title', 'Name', 'name']:
                if title_key in properties:
                    title_property = properties[title_key]
                    if title_property.get('type') == 'title':
                        title_array = title_property.get('title', [])
                        if title_array:
                            return title_array[0].get('plain_text', '')
            
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
            
            block = self._create_text_block(text, formatting)
            
            data = {
                "children": [block]
            }
            
            response = requests.patch(url, headers=self.headers, json=data, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"✅ Successfully added text to page {page_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error adding text to Notion page: {e}")
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
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check Notion service health"""
        try:
            test_results = self.search_pages("test")
            
            return {
                "status": "healthy",
                "service": "Enhanced Notion",
                "api_version": self.notion_version,
                "can_search": True,
                "enhanced_features": [
                    "Full content search",
                    "Long text writing",
                    "Chatbot response integration",
                    "Advanced text splitting"
                ],
                "search_test_results": len(test_results),
                "token_configured": bool(self.notion_token)
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced Notion health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "Enhanced Notion",
                "error": str(e),
                "token_configured": bool(self.notion_token)
            }