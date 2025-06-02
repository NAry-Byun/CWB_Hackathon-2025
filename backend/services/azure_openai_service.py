# services/azure_openai_service.py - ENHANCED WITH NOTION INTEGRATION AND BETTER FORMATTING

import os
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Complete Azure OpenAI Service with Notion integration support and improved text formatting"""

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
        
        cleaned = response_text
        
        # Remove excessive formatting symbols
        cleaned = re.sub(r'#{4,}', '##', cleaned)  # Reduce excessive # to ##
        cleaned = re.sub(r'\*{4,}', '**', cleaned)  # Reduce excessive * to **
        
        # Fix section headers - standardize to ##
        cleaned = re.sub(r'###\s*(.+?)\s*###', r'## \1', cleaned)
        cleaned = re.sub(r'####\s*(.+)', r'## \1', cleaned)
        
        # Clean up bullet points
        cleaned = re.sub(r'\*\*([^*]+?)\*\*\s*:', r'**\1:**', cleaned)  # Fix bold labels
        cleaned = re.sub(r'^\*\s+', '• ', cleaned, flags=re.MULTILINE)  # Convert * to •
        
        # Fix spacing issues
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Reduce excessive line breaks
        cleaned = re.sub(r'\s+$', '', cleaned, flags=re.MULTILINE)  # Remove trailing spaces
        
        # Clean up specific problematic patterns
        cleaned = re.sub(r'\*\*\*(.+?)\*\*\*', r'**\1**', cleaned)  # Triple asterisks to double
        cleaned = re.sub(r'---+', '---', cleaned)  # Standardize separators
        
        # Remove standalone formatting characters
        cleaned = re.sub(r'^\s*[*#]+\s*$', '', cleaned, flags=re.MULTILINE)
        
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
        Generate AI response using Azure OpenAI Chat Completions with improved formatting
        
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
            # Build conversation messages with Notion data
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
        Build conversation messages for Azure OpenAI Chat Completions
        
        Args:
            user_message: Current user message
            context: Previous conversation context
            document_chunks: Relevant document chunks
            notion_pages: Notion pages found during search
            
        Returns:
            List of message dictionaries for the API
        """
        messages = []

        # System message with instructions including Notion data
        system_prompt = self._get_system_prompt(document_chunks, notion_pages)
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

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def _get_system_prompt(
        self, 
        document_chunks: List[Dict] = None,
        notion_pages: List[Dict] = None
    ) -> str:
        """
        Create system prompt with optional document context and Notion data
        
        Args:
            document_chunks: Relevant document chunks from vector search
            notion_pages: Notion pages found during search
            
        Returns:
            System prompt string with all available context
        """
        base_prompt = """You are an AI Personal Assistant powered by Azure OpenAI, Cosmos DB, and Notion. 
You are helpful, knowledgeable, and provide accurate information. 
Always be polite and professional in your responses.

FORMATTING INSTRUCTIONS:
- Use clear, readable formatting
- Use ## for section headers (not ### or ####)
- Use • for bullet points (not *)
- Keep responses clean and professional
- Avoid excessive markup symbols
- Use proper spacing between sections
- Make your responses easy to read and scan

When responding to questions about meetings, schedules, or workspace information, prioritize the Notion data as it represents the user's current and most accurate information."""

        context_parts = []

        # Add Notion pages to system prompt
        if notion_pages and len(notion_pages) > 0:
            notion_context = "\n\n## Notion Workspace Data\n\n"
            notion_context += f"I have access to your Notion workspace and found {len(notion_pages)} relevant pages:\n\n"
            
            for i, page in enumerate(notion_pages[:5]):  # Limit to top 5 pages
                title = page.get("title", "Untitled Page")
                page_id = page.get("id", "unknown")
                url = page.get("url", "")
                last_edited = page.get("last_edited_time", "")
                created_time = page.get("created_time", "")
                content = page.get("content", "")
                
                notion_context += f"**Page {i+1}: {title}**\n"
                notion_context += f"• Page ID: {page_id}\n"
                if url:
                    notion_context += f"• URL: {url}\n"
                if last_edited:
                    notion_context += f"• Last edited: {last_edited}\n"
                if created_time:
                    notion_context += f"• Created: {created_time}\n"
                
                # Include content preview if available
                if content:
                    preview = content[:800] if len(content) > 800 else content
                    notion_context += f"• Content preview:\n{preview}\n"
                    if len(content) > 800:
                        notion_context += "• [Content truncated...]\n"
                
                notion_context += "\n"
            
            notion_context += """**Important Guidelines for Using Notion Data:**
• Reference specific page titles and content
• Include relevant dates and times
• Mention page URLs when helpful
• Provide actionable information based on the content
• If multiple meetings or events are found, organize them chronologically
• Always cite which Notion page the information comes from

Respond in a natural, helpful way while incorporating this Notion information."""
            
            context_parts.append(notion_context)

        # Add document context to prompt
        if document_chunks and len(document_chunks) > 0:
            doc_context = "\n\n## Document Knowledge Base\n\n"
            doc_context += "Relevant information from your knowledge base:\n\n"
            
            for i, chunk in enumerate(document_chunks[:3]):  # Limit to top 3 chunks
                file_name = chunk.get("file_name", "Unknown")
                content = chunk.get("content", "")[:500]  # Limit content length
                similarity = chunk.get("similarity", 0.0)
                
                doc_context += f"**Document {i+1}: {file_name} (Relevance: {similarity:.2f})**\n{content}\n\n"
            
            doc_context += "Please use this information to provide accurate and relevant responses."
            
            context_parts.append(doc_context)

        # Combine all context
        if context_parts:
            full_prompt = base_prompt + "".join(context_parts)
            full_prompt += "\n\nBased on the above information, please provide a helpful and accurate response to the user's question."
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
                "text_formatting": "enhanced"
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