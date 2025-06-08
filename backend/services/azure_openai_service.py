# services/azure_openai_service.py - FIXED TO EXTRACT ACTUAL MEETING DETAILS

import os
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Complete Azure OpenAI Service with proper Notion content extraction"""

    def __init__(self):
        """Initialize Azure OpenAI service with environment variables"""
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.chat_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
        self.embedding_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

        if not self.api_key or not self.endpoint:
            raise ValueError(
                "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are required. "
                "Please set them in your .env file."
            )

        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )

        logger.info("✅ AzureOpenAIService initialized successfully")
        logger.info(f"🔧 Chat deployment: {self.chat_deployment}")
        logger.info(f"🔧 Embedding deployment: {self.embedding_deployment}")

    def clean_response_formatting(self, response_text: str) -> str:
        """Clean up AI response formatting for better readability"""
        if not response_text:
            return ""
        
        # Start with the original response text
        cleaned = response_text
        
        # Remove all markdown headers (##, ###, ####)
        cleaned = re.sub(r'#{1,6}\s*', '', cleaned)
        
        # Remove all bold/italic markers (**text**, *text*)
        cleaned = re.sub(r'\*{1,3}([^*]+?)\*{1,3}', r'\1', cleaned)
        
        # Convert bullet points to simple dashes
        cleaned = re.sub(r'^\s*[•*-]\s+', '- ', cleaned, flags=re.MULTILINE)
        
        # Remove excessive line breaks
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Clean up extra spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n\s+', '\n', cleaned)
        
        # Remove any remaining special characters
        cleaned = re.sub(r'[{}[\]|\\~`]', '', cleaned)
        
        return cleaned.strip()

    async def generate_response(
        self,
        user_message: str,
        context: List[Dict] = None,
        document_chunks: List[Dict] = None,
        notion_pages: List[Dict] = None,
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate AI response using Azure OpenAI Chat Completions with proper Notion content extraction
        
        Args:
            user_message: User's input message
            context: Previous conversation context
            document_chunks: Relevant document chunks from vector search
            notion_pages: Notion pages found during search
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
            
        Returns:
            Dict with assistant_message and metadata
        """
        try:
            # Build conversation messages with enhanced Notion data processing
            messages = self._build_messages(user_message, context, document_chunks, notion_pages)
            
            logger.info(f"🤖 Generating response for: '{user_message[:50]}...'")
            logger.info(f"📝 Message count: {len(messages)}")
            
            # Log Notion pages if available
            if notion_pages and len(notion_pages) > 0:
                logger.info(f"🟣 Including {len(notion_pages)} Notion pages in context")
                for i, page in enumerate(notion_pages[:3]):
                    logger.info(f"   📄 Page {i+1}: {page.get('title', 'No title')}")

            # Log message size for debugging
            total_message_size = sum(len(str(msg.get('content', ''))) for msg in messages)
            logger.info(f"📏 Total message size: {total_message_size} characters")

            # Call Azure OpenAI Chat Completions
            response = await self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            # Extract and clean response content
            raw_assistant_message = response.choices[0].message.content.strip()
            cleaned_assistant_message = self.clean_response_formatting(raw_assistant_message)
            
            # Build response object
            result = {
                "assistant_message": cleaned_assistant_message,
                "content": cleaned_assistant_message,  # Frontend compatibility
                "raw_response": raw_assistant_message,  # Keep original for debugging
                "model_used": self.chat_deployment,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "has_context": len(context or []) > 0,
                "has_documents": len(document_chunks or []) > 0,
                "has_notion": len(notion_pages or []) > 0,
                "timestamp": "2025-06-01T18:00:00Z",
                "formatting_applied": True
            }

            logger.info(f"✅ Generated response: {len(cleaned_assistant_message)} characters (cleaned)")
            logger.info(f"📊 Token usage: {response.usage.total_tokens} total")

            return result

        except Exception as e:
            logger.error(f"❌ Azure OpenAI response generation failed: {e}")
            return {
                "assistant_message": f"I apologize, but I encountered an error: {str(e)}",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "error": str(e),
                "model_used": self.chat_deployment,
                "formatting_applied": False
            }

    async def generate_embeddings(
        self,
        text: str,
        max_retries: int = 3
    ) -> Optional[List[float]]:
        """
        Generate vector embeddings for text using Azure OpenAI
        
        Args:
            text: Text to embed
            max_retries: Number of retry attempts
            
        Returns:
            List of float values representing the embedding vector
        """
        try:
            if not text or not text.strip():
                logger.warning("⚠️ Empty text provided for embedding")
                return None

            # Clean and prepare text
            clean_text = text.strip()[:8000]  # Limit text length
            
            logger.info(f"🔢 Generating embedding for text: {len(clean_text)} characters")

            # Call Azure OpenAI Embeddings API
            response = await self.client.embeddings.create(
                model=self.embedding_deployment,
                input=clean_text
            )

            # Extract embedding vector
            embedding = response.data[0].embedding
            
            logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            return None

    def _build_messages(
        self,
        user_message: str,
        context: List[Dict] = None,
        document_chunks: List[Dict] = None,
        notion_pages: List[Dict] = None
    ) -> List[Dict[str, str]]:
        """
        Build conversation messages for Azure OpenAI Chat Completions with enhanced Notion processing
        
        Args:
            user_message: Current user message
            context: Previous conversation context
            document_chunks: Relevant document chunks
            notion_pages: Notion pages found during search
            
        Returns:
            List of message dictionaries for the API
        """
        messages = []

        # Enhanced system message with specific Notion content instructions
        system_prompt = self._get_enhanced_system_prompt(user_message, document_chunks, notion_pages)
        messages.append({
            "role": "system",
            "content": system_prompt
        })

        # Add context from previous conversation
        if context:
            for msg in context[-5:]:  # Limit to last 5 messages
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Enhanced user message with specific instructions for meeting queries
        enhanced_user_message = self._enhance_user_message(user_message, notion_pages)
        messages.append({
            "role": "user",
            "content": enhanced_user_message
        })

        return messages

    def _enhance_user_message(self, user_message: str, notion_pages: List[Dict] = None) -> str:
        """Enhance user message with specific instructions based on content type"""
        enhanced_message = user_message
        
        # Check if this is a meeting/calendar query
        meeting_keywords = ['meeting', 'calendar', 'schedule', 'appointment', 'agenda']
        is_meeting_query = any(keyword in user_message.lower() for keyword in meeting_keywords)
        
        if is_meeting_query and notion_pages and len(notion_pages) > 0:
            enhanced_message += "\n\nIMPORTANT: I can see you have Notion calendar/meeting pages available. Please extract and present the actual meeting details (dates, times, locations, titles) directly in your response. Do NOT just provide links or tell me to check the Notion page. I want to see the specific meeting schedule information right here in the chat."
        
        return enhanced_message

    def _get_enhanced_system_prompt(
        self, 
        user_message: str,
        document_chunks: List[Dict] = None,
        notion_pages: List[Dict] = None
    ) -> str:
        """
        Create enhanced system prompt with balanced instructions for all content types
        
        Args:
            user_message: The user's query to understand context
            document_chunks: Relevant document chunks from vector search
            notion_pages: Notion pages found during search
            
        Returns:
            Enhanced system prompt string with balanced extraction instructions
        """
        # Detect if this is a meeting/calendar query
        meeting_keywords = ['meeting', 'calendar', 'schedule', 'appointment', 'agenda', 'july', 'june']
        is_meeting_query = any(keyword in user_message.lower() for keyword in meeting_keywords)
        
        base_prompt = """You are an AI Personal Assistant with access to the user's documents, Notion workspace, and knowledge base. You provide helpful, accurate information based on available content.

RESPONSE GUIDELINES:

1. USE AVAILABLE CONTENT: Always use information from the provided document chunks, Notion pages, and search results to answer questions accurately and specifically.

2. BE COMPREHENSIVE: When users ask about specific topics, extract and present relevant details from the available content. Don't just acknowledge that content exists - use it to provide specific answers.

3. SPECIAL HANDLING FOR MEETINGS/CALENDARS: When users ask about meetings or schedules:
   - Extract ALL meeting details from Notion page content
   - Present dates, times, locations, and meeting titles
   - Organize chronologically and be comprehensive
   - Don't just provide links - show the actual schedule

4. DOCUMENT SEARCH RESULTS: When document chunks contain relevant information:
   - Summarize and present the key information
   - Reference specific details from the content
   - Combine information from multiple sources when relevant

5. RESPONSE STYLE:
   - Write in clear, natural language
   - Be specific and informative
   - Use simple formatting with dashes (-) for lists
   - Organize information logically

6. PROVIDE COMPLETE ANSWERS: Always aim to fully answer the user's question using the available content rather than suggesting they look elsewhere."""

        # Add specific meeting instructions if applicable
        if is_meeting_query and notion_pages and len(notion_pages) > 0:
            base_prompt += """

MEETING QUERY DETECTED: Extract and present the complete meeting schedule from the Notion page content. Include all dates, times, locations, and meeting details in your response."""

        context_parts = []

        # Add document context first (for general search results)
        if document_chunks and len(document_chunks) > 0:
            doc_context = "\n\n=== DOCUMENT SEARCH RESULTS ===\n\n"
            doc_context += f"Found {len(document_chunks)} relevant documents for your query:\n\n"
            
            for i, chunk in enumerate(document_chunks[:5]):  # Increased to 5 chunks
                file_name = chunk.get("file_name", "Unknown Document")
                content = chunk.get("content", chunk.get("chunk_text", ""))
                similarity = chunk.get("similarity", 0.0)
                
                # Ensure we have substantial content
                if content and len(content.strip()) > 10:
                    doc_context += f"DOCUMENT {i+1}: {file_name} (Relevance: {similarity:.2f})\n"
                    doc_context += f"Content: {content[:1500]}\n\n"  # Increased content length
            
            doc_context += "Use the above document content to provide specific, detailed answers to the user's question.\n"
            context_parts.append(doc_context)

        # Enhanced Notion pages processing
        if notion_pages and len(notion_pages) > 0:
            notion_context = "\n\n=== NOTION WORKSPACE CONTENT ===\n\n"
            
            for i, page in enumerate(notion_pages[:3]):
                title = page.get("title", "Untitled Page")
                page_id = page.get("id", "unknown")
                url = page.get("url", "")
                last_edited = page.get("last_edited_time", "")
                
                # CRITICAL: Get the full content from the page
                full_content = page.get("full_content", "")
                content_snippets = page.get("content_snippets", [])
                
                notion_context += f"NOTION PAGE {i+1}: {title}\n"
                if url:
                    notion_context += f"URL: {url}\n"
                
                # Include FULL content for extraction
                if full_content:
                    notion_context += f"\nPAGE CONTENT:\n{full_content}\n"
                elif content_snippets:
                    notion_context += f"\nCONTENT SNIPPETS:\n"
                    for snippet in content_snippets[:5]:
                        notion_context += f"- {snippet}\n"
                
                notion_context += "\n" + "-"*50 + "\n\n"
            
            if is_meeting_query:
                notion_context += """MEETING EXTRACTION: Extract and present the complete meeting schedule from the above Notion content. Include all dates, times, locations, and meeting titles.\n"""
            else:
                notion_context += """Use the above Notion content to provide specific answers to the user's question.\n"""
            
            context_parts.append(notion_context)

        # Combine all context
        if context_parts:
            full_prompt = base_prompt + "".join(context_parts)
            if is_meeting_query:
                full_prompt += "\n\nREMEMBER: Extract and present the actual meeting details from the Notion content above. The user wants to see the specific schedule information in your response, not just links or references to check elsewhere."
            return full_prompt

        return base_prompt

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Azure OpenAI service health and connectivity
        
        Returns:
            Dict with health status and service information
        """
        try:
            # Test with a simple embedding request
            test_response = await self.client.embeddings.create(
                model=self.embedding_deployment,
                input="test"
            )
            
            return {
                "status": "healthy",
                "service": "Azure OpenAI",
                "chat_deployment": self.chat_deployment,
                "embedding_deployment": self.embedding_deployment,
                "api_version": self.api_version,
                "test_embedding_dimensions": len(test_response.data[0].embedding),
                "connectivity": "successful",
                "notion_integration": "enabled",
                "text_formatting": "enhanced",
                "meeting_extraction": "enabled"
            }

        except Exception as e:
            logger.error(f"❌ Azure OpenAI health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "Azure OpenAI",
                "error": str(e),
                "connectivity": "failed"
            }

    async def close(self):
        """Close the Azure OpenAI client connection"""
        try:
            await self.client.close()
            logger.info("🔒 Azure OpenAI client connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Azure OpenAI client: {e}")

# Compatibility alias
OpenAIService = AzureOpenAIService