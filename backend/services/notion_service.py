import os
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class NotionService:
    """Real Notion API Integration Service"""

    def __init__(self):
        """
        Initialize Notion service:
          - Requires NOTION_API_TOKEN in environment
          - Uses NOTION_API_VERSION (default "2022-06-28")
        """
        self.api_token = os.getenv('NOTION_API_TOKEN')
        self.api_version = os.getenv('NOTION_API_VERSION', '2022-06-28')
        self.base_url = 'https://api.notion.com/v1'

        if not self.api_token:
            raise ValueError("NOTION_API_TOKEN is required")

        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Notion-Version': self.api_version,
            'Content-Type': 'application/json'
        }

        logger.info(f"🟣 NotionService initialized (API version {self.api_version})")

    async def search_pages(self, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for pages in your Notion workspace.
        - query: free‐text search
        - limit: maximum number of pages to return
        """
        try:
            url = f"{self.base_url}/search"
            payload = {
                "page_size": limit,
                "filter": {
                    "property": "object",
                    "value": "page"
                }
            }
            if query:
                payload["query"] = query

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results: List[Dict[str, Any]] = []
                        for page in data.get('results', []):
                            page_info = {
                                'id': page['id'],
                                'title': self._extract_title(page),
                                'url': page['url'],
                                'created_time': page['created_time'],
                                'last_edited_time': page['last_edited_time'],
                                'object': page['object']
                            }
                            results.append(page_info)
                        logger.info(f"✅ Found {len(results)} pages in Notion search")
                        return results
                    else:
                        error_text = await resp.text()
                        logger.error(f"❌ Notion search failed: {resp.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"❌ Error searching Notion pages: {e}")
            return []

    async def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch the metadata and block content for a specific page.
        - page_id: Notion page UUID
        Returns a dict with keys: 'success', 'id', 'title', 'content', 'url', 'created_time', 'last_edited_time'
        """
        try:
            page_url = f"{self.base_url}/pages/{page_id}"
            blocks_url = f"{self.base_url}/blocks/{page_id}/children"

            async with aiohttp.ClientSession() as session:
                # 1) Get page metadata
                async with session.get(page_url, headers=self.headers) as resp_page:
                    if resp_page.status != 200:
                        error_text = await resp_page.text()
                        logger.error(f"❌ Failed to get page {page_id}: {resp_page.status} - {error_text}")
                        return {"success": False, "error": f"Page not found: {resp_page.status}"}
                    page_data = await resp_page.json()

                # 2) Get page block children
                async with session.get(blocks_url, headers=self.headers) as resp_blocks:
                    if resp_blocks.status != 200:
                        logger.warning(f"⚠️ Failed to get blocks for page {page_id}: {resp_blocks.status}")
                        blocks_data = {"results": []}
                    else:
                        blocks_data = await resp_blocks.json()

                content = self._extract_content_from_blocks(blocks_data.get('results', []))
                result = {
                    "success": True,
                    "id": page_data['id'],
                    "title": self._extract_title(page_data),
                    "content": content,
                    "url": page_data['url'],
                    "created_time": page_data['created_time'],
                    "last_edited_time": page_data['last_edited_time']
                }
                logger.info(f"✅ Retrieved content for page: {result['title']}")
                return result

        except Exception as e:
            logger.error(f"❌ Error getting page content: {e}")
            return {"success": False, "error": str(e)}

    async def append_text_to_page(self, page_id: str, text: str) -> Dict[str, Any]:
        """
        Append a paragraph block containing `text` to the specified page.
        """
        try:
            blocks_url = f"{self.base_url}/blocks/{page_id}/children"
            payload = {
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": text}
                                }
                            ]
                        }
                    }
                ]
            }
            async with aiohttp.ClientSession() as session:
                async with session.patch(blocks_url, headers=self.headers, json=payload) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        logger.info(f"✅ Appended text to page {page_id}")
                        return {"success": True, "data": data}
                    else:
                        error_text = await resp.text()
                        logger.error(f"❌ Failed to append text to page {page_id}: {resp.status} - {error_text}")
                        return {"success": False, "error": error_text}
        except Exception as e:
            logger.error(f"❌ Exception appending text to page: {e}")
            return {"success": False, "error": str(e)}

    async def search_databases(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Search for databases in Notion.
        - query: free‐text (optional)
        Returns a list of database metadata (id, title, url, etc.)
        """
        try:
            url = f"{self.base_url}/search"
            payload = {
                "filter": {
                    "property": "object",
                    "value": "database"
                }
            }
            if query:
                payload["query"] = query

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results: List[Dict[str, Any]] = []
                        for db in data.get('results', []):
                            db_info = {
                                'id': db['id'],
                                'title': self._extract_title(db),
                                'url': db['url'],
                                'created_time': db['created_time'],
                                'last_edited_time': db['last_edited_time']
                            }
                            results.append(db_info)
                        logger.info(f"✅ Found {len(results)} databases in Notion")
                        return results
                    else:
                        error_text = await resp.text()
                        logger.error(f"❌ Notion database search failed: {resp.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"❌ Error searching Notion databases: {e}")
            return []

    async def query_database(self, database_id: str, filter_conditions: Dict = None) -> List[Dict[str, Any]]:
        """
        Query a specific database using Notion's /databases/{database_id}/query endpoint.
        - filter_conditions: Notion filter JSON (optional)
        Returns a list of page entries (id, title, url, properties, etc.)
        """
        try:
            url = f"{self.base_url}/databases/{database_id}/query"
            payload = {}
            if filter_conditions:
                payload["filter"] = filter_conditions

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results: List[Dict[str, Any]] = []
                        for page in data.get('results', []):
                            page_info = {
                                'id': page['id'],
                                'title': self._extract_title(page),
                                'url': page['url'],
                                'properties': page.get('properties', {}),
                                'created_time': page['created_time'],
                                'last_edited_time': page['last_edited_time']
                            }
                            results.append(page_info)
                        logger.info(f"✅ Found {len(results)} entries in database {database_id}")
                        return results
                    else:
                        error_text = await resp.text()
                        logger.error(f"❌ Database query failed: {resp.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"❌ Error querying database: {e}")
            return []

    def _extract_title(self, page_or_db: Dict) -> str:
        """
        Extract the title from a page or database record.
        - For pages: find the first 'title' property under 'properties'
        - For databases: look at the 'title' field
        """
        try:
            if 'properties' in page_or_db:
                props = page_or_db['properties']
                for prop_name, prop_data in props.items():
                    if prop_data.get('type') == 'title':
                        title_arr = prop_data.get('title', [])
                        if title_arr:
                            return title_arr[0].get('plain_text', 'Untitled')
            if 'title' in page_or_db:
                title_arr = page_or_db['title']
                if title_arr:
                    return title_arr[0].get('plain_text', 'Untitled Database')
            return 'Untitled'
        except Exception as e:
            logger.error(f"❌ Error extracting title: {e}")
            return 'Untitled'

    def _extract_content_from_blocks(self, blocks: List[Dict]) -> str:
        """
        Convert a list of Notion block objects into plain‐text content.
        Supports: paragraph, heading_1/2/3, bulleted_list_item, numbered_list_item, to_do, code.
        """
        content_parts: List[str] = []

        for block in blocks:
            btype = block.get('type', '')
            try:
                if btype == 'paragraph':
                    text = self._extract_rich_text(block['paragraph'].get('rich_text', []))
                    if text:
                        content_parts.append(text)
                elif btype == 'heading_1':
                    text = self._extract_rich_text(block['heading_1'].get('rich_text', []))
                    if text:
                        content_parts.append(f"# {text}")
                elif btype == 'heading_2':
                    text = self._extract_rich_text(block['heading_2'].get('rich_text', []))
                    if text:
                        content_parts.append(f"## {text}")
                elif btype == 'heading_3':
                    text = self._extract_rich_text(block['heading_3'].get('rich_text', []))
                    if text:
                        content_parts.append(f"### {text}")
                elif btype == 'bulleted_list_item':
                    text = self._extract_rich_text(block['bulleted_list_item'].get('rich_text', []))
                    if text:
                        content_parts.append(f"• {text}")
                elif btype == 'numbered_list_item':
                    text = self._extract_rich_text(block['numbered_list_item'].get('rich_text', []))
                    if text:
                        content_parts.append(f"1. {text}")
                elif btype == 'to_do':
                    text = self._extract_rich_text(block['to_do'].get('rich_text', []))
                    checked = block['to_do'].get('checked', False)
                    checkbox = "☑️" if checked else "☐"
                    if text:
                        content_parts.append(f"{checkbox} {text}")
                elif btype == 'code':
                    text = self._extract_rich_text(block['code'].get('rich_text', []))
                    lang = block['code'].get('language', '')
                    if text:
                        content_parts.append(f"```{lang}\n{text}\n```")
            except Exception as e:
                logger.warning(f"⚠️ Error processing block type {btype}: {e}")
                continue

        return "\n\n".join(content_parts)

    def _extract_rich_text(self, rich_text_array: List[Dict]) -> str:
        """
        Convert a Notion rich_text array into plain string.
        """
        parts: List[str] = []
        for txt in rich_text_array:
            if 'plain_text' in txt:
                parts.append(txt['plain_text'])
        return "".join(parts)

    async def search_meeting_pages(self, query: str = "meeting") -> List[Dict[str, Any]]:
        """
        Combine a free-text query with a set of meeting-related keyword searches.
        Returns top 10 unique pages with their full content.
        """
        try:
            meeting_keywords = ["meeting", "agenda", "notes", "conference", "call"]
            all_results: Dict[str, Dict[str, Any]] = {}

            # Search with user-provided query
            if query:
                results = await self.search_pages(query=query, limit=20)
                for page in results:
                    all_results[page['id']] = page

            # Also search using meeting_keywords
            for keyword in meeting_keywords:
                results = await self.search_pages(query=keyword, limit=10)
                for page in results:
                    all_results[page['id']] = page

            final_results = list(all_results.values())
            # Fetch full content for each page
            enriched_results = []
            for page in final_results:
                content_data = await self.get_page_content(page['id'])
                if content_data.get('success'):
                    page['content'] = content_data.get('content', '')
                else:
                    page['content'] = ''
                enriched_results.append(page)

            enriched_results.sort(key=lambda x: x['last_edited_time'], reverse=True)
            logger.info(f"✅ Found {len(enriched_results)} meeting-related pages with content")
            return enriched_results[:10]
        except Exception as e:
            logger.error(f"❌ Error searching meeting pages: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify connectivity by calling /users/me.
        Returns {"status": "healthy"} on success.
        """
        try:
            url = f"{self.base_url}/users/me"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        user_data = await resp.json()
                        return {
                            "status": "healthy",
                            "workspace_user_type": user_data.get('type', 'unknown')
                        }
                    else:
                        err = await resp.text()
                        return {"status": "unhealthy", "error": f"HTTP {resp.status}: {err}"}
        except Exception as e:
            logger.error(f"❌ Notion health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}