# routes/chat_routes.py - CORS 문제 해결된 완전한 완전한 버전

from flask import Blueprint, request, jsonify
import asyncio
import sys
import os
import logging
from datetime import datetime

# ─── Allow importing from project root ────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)

# ─── Import services with graceful fallbacks ──────────────────────────────────
try:
    from services.azure_openai_service import AzureOpenAIService
    logger.info("✅ AzureOpenAIService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ AzureOpenAIService not available: {e}")
    AzureOpenAIService = None

try:
    from services.cosmos_service import CosmosVectorService
    logger.info("✅ CosmosVectorService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ CosmosVectorService not available: {e}")
    CosmosVectorService = None

try:
    from services.notion_service import NotionService
    logger.info("✅ NotionService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ NotionService not available: {e}")
    NotionService = None

try:
    from services.web_scraper_service import EnhancedWebScraperService
    logger.info("✅ EnhancedWebScraperService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ EnhancedWebScraperService not available: {e}")
    EnhancedWebScraperService = None

# ─── Blueprint Definition ─────────────────────────────────────────────────────
chat_bp = Blueprint('chat', __name__)

# ─── Global service instances ─────────────────────────────────────────────────
openai_service = None
cosmos_service = None
notion_service = None
web_scraper_service = None

def initialize_services():
    """Initialize all available services."""
    global openai_service, cosmos_service, notion_service, web_scraper_service

    # Initialize OpenAI Service
    if AzureOpenAIService:
        try:
            openai_service = AzureOpenAIService()
            logger.info("✅ AzureOpenAIService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AzureOpenAIService: {e}")
            openai_service = None

    # Initialize Cosmos Service
    if CosmosVectorService:
        try:
            cosmos_service = CosmosVectorService()
            logger.info("✅ CosmosVectorService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CosmosVectorService: {e}")
            cosmos_service = None

    # Initialize Notion Service
    if NotionService:
        try:
            notion_service = NotionService()
            logger.info("✅ NotionService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize NotionService: {e}")
            notion_service = None

    # Initialize Web Scraper Service
    if EnhancedWebScraperService:
        try:
            web_scraper_service = EnhancedWebScraperService(
                cosmos_service=cosmos_service,
                openai_service=openai_service
            )
            logger.info("🕷️ EnhancedWebScraperService initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize EnhancedWebScraperService: {e}")
            web_scraper_service = None

# Initialize services on import
initialize_services()

# ─── CORS Helper Function ─────────────────────────────────────────────────────
def _handle_cors():
    """Handle CORS preflight requests."""
    response = jsonify()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# ─── Main Chat Endpoints ──────────────────────────────────────────────────────

@chat_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """Full chat with vector search, Notion search, and context."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service:
        return _error_response("OpenAI service not available", 503)

    data = request.get_json()
    if not data or 'message' not in data:
        return _error_response("Field 'message' is required", 400)

    user_message = data['message']
    context = data.get('context', [])

    logger.info(f"💬 Full chat: {user_message[:100]}")

    try:
        # 비동기 파이프라인을 동기적으로 실행
        result_data = asyncio.run(_process_full_chat(user_message, context))
        return _success_response(result_data, "Chat response generated")

    except Exception as e:
        logger.error(f"❌ Full chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

@chat_bp.route('/simple', methods=['POST', 'OPTIONS'])
def simple_chat():
    """Simple chat without vector search - just return OpenAI response."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service:
        return _error_response("OpenAI service not available", 503)

    data = request.get_json()
    if not data or 'message' not in data:
        return _error_response("Field 'message' is required", 400)

    user_message = data['message']
    logger.info(f"💬 Simple chat: {user_message[:100]}")

    try:
        response = asyncio.run(_simple_openai_call(user_message))

        result_data = {
            "assistant_message": response,
            "content": response,  # 프론트엔드 호환
            "mode": "simple",
            "azure_services_used": {
                "openai": True,
                "cosmos_db": False,
                "vector_search": False
            }
        }

        return _success_response(result_data, "Simple chat response generated")

    except Exception as e:
        logger.error(f"❌ Simple chat error: {e}", exc_info=True)
        return _error_response(f"Chat failed: {str(e)}", 500)

# ─── Health and Test Endpoints ────────────────────────────────────────────────

@chat_bp.route('/health', methods=['GET', 'OPTIONS'])
def chat_health():
    """Health check for chat services."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": openai_service is not None,
            "cosmos": cosmos_service is not None,
            "notion": notion_service is not None,
            "web_scraper": web_scraper_service is not None
        },
        "endpoints": [
            "/chat", "/simple", "/health", "/test", "/fix-embeddings",
            "/scrape-url", "/scrape-multiple", "/scrape-test"
        ]
    })

@chat_bp.route('/test', methods=['GET', 'OPTIONS'])
def test_endpoint():
    """Simple test endpoint to confirm that chat routes are working."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    return jsonify({
        "status": "Chat routes working",
        "message": "Test endpoint successful",
        "timestamp": datetime.now().isoformat(),
        "backend_url": "http://localhost:5000"
    })

# ─── Embedding Fix Endpoint ───────────────────────────────────────────────────

@chat_bp.route('/fix-embeddings', methods=['POST', 'OPTIONS'])
def fix_embeddings():
    """Fix missing embeddings for stored documents in Cosmos DB."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not openai_service or not CosmosVectorService:
        return _error_response("Services not available", 503)

    try:
        result = asyncio.run(_fix_embeddings_async())
        return _success_response(result, "임베딩 수정 완료")
    except Exception as e:
        logger.error(f"❌ 임베딩 수정 오류: {e}", exc_info=True)
        return _error_response(f"임베딩 수정 실패: {str(e)}", 500)

# ─── Web Scraping Endpoints ───────────────────────────────────────────────────

@chat_bp.route('/scrape-url', methods=['POST', 'OPTIONS'])
def scrape_single_url():
    """Scrape a single URL and save data into Cosmos DB."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not web_scraper_service:
        return _error_response("웹 스크래핑 서비스를 사용할 수 없습니다", 503)

    data = request.get_json()
    if not data or 'url' not in data:
        return _error_response("Field 'url' is required", 400)

    url = data['url']

    try:
        logger.info(f"🕷️ URL Scraping request: {url}")
        result = asyncio.run(web_scraper_service.scrape_and_save_url(url))

        if result.get('success'):
            message = f"URL 스크래핑 및 저장 완료: {result.get('title', 'Unknown')}"
            if result.get('cosmos_saved'):
                message += f" ({result.get('chunks_saved', 0)}개 청크 저장됨)"
            return _success_response(result, message)
        else:
            return _error_response(f"스크래핑 실패: {result.get('error')}", 400)

    except Exception as e:
        logger.error(f"❌ URL Scraping error: {e}", exc_info=True)
        return _error_response(f"스크래핑 실패: {str(e)}", 500)

@chat_bp.route('/scrape-multiple', methods=['POST', 'OPTIONS'])
def scrape_multiple_urls():
    """Scrape multiple URLs and save data into Cosmos DB."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not web_scraper_service:
        return _error_response("웹 스크래핑 서비스를 사용할 수 없습니다", 503)

    data = request.get_json()
    if not data or 'urls' not in data:
        return _error_response("Field 'urls' is required", 400)

    urls = data['urls']
    if not isinstance(urls, list):
        return _error_response("'urls' must be an array", 400)
    if len(urls) > 10:
        return _error_response("한 번에 최대 10개 URL만 처리할 수 있습니다", 400)

    try:
        logger.info(f"🕷️ 다중 URL 스크래핑 요청: {len(urls)}개")
        result = asyncio.run(web_scraper_service.scrape_multiple_and_save(urls))

        message = f"{result.get('successful_saves')}/{result.get('total_urls')} URL 성공적으로 저장됨"
        return _success_response(result, message)

    except Exception as e:
        logger.error(f"❌ Multiple scraping error: {e}", exc_info=True)
        return _error_response(f"스크래핑 실패: {str(e)}", 500)

@chat_bp.route('/scrape-test', methods=['GET', 'OPTIONS'])
def test_scraping():
    """Test web scraping by hitting a known page."""
    if request.method == 'OPTIONS':
        return _handle_cors()

    if not web_scraper_service:
        return _error_response("웹 스크래핑 서비스를 사용할 수 없습니다", 503)

    try:
        test_url = "https://azure.microsoft.com/en-us/products/ai-services/"
        logger.info(f"🧪 Scraping test: {test_url}")
        result = asyncio.run(web_scraper_service.scrape_and_save_url(test_url))
        return _success_response(result, "스크래핑 테스트 완료")
    except Exception as e:
        logger.error(f"❌ Scraping test error: {e}", exc_info=True)
        return _error_response(f"테스트 실패: {str(e)}", 500)

# ─── Async Helper Functions ───────────────────────────────────────────────────

async def _simple_openai_call(user_message: str) -> str:
    """Simple OpenAI call without any context."""
    try:
        if openai_service and hasattr(openai_service, 'generate_response'):
            response = await openai_service.generate_response(
                user_message=user_message,
                context=[],
                document_chunks=[],
                notion_pages=[]
            )
            if isinstance(response, dict):
                return response.get("assistant_message", str(response))
            return str(response)
        elif openai_service and hasattr(openai_service, 'chat_completion'):
            return await openai_service.chat_completion(user_message)
        else:
            return "OpenAI service is not properly configured."
    except Exception as e:
        logger.error(f"❌ OpenAI call failed: {e}", exc_info=True)
        return f"I apologize, but I encountered an error: {str(e)}"

async def _process_full_chat(user_message: str, context: list) -> dict:
    """Process chat with full pipeline: Notion search, embedding 생성, Cosmos 검색, then OpenAI."""
    result_data = {
        "assistant_message": "",
        "content": "",
        "sources": [],
        "azure_services_used": {
            "openai": False,
            "openai_embedding": False,
            "cosmos_db": False,
            "vector_search": False,
            "notion_search": False,
            "document_chunks": 0
        },
        "notion_pages": [],
        "document_chunks": []
    }

    try:
        # 1. Notion 검색 (예약어 기반)
        notion_pages = []
        if notion_service and any(
            kw in user_message.lower()
            for kw in ["notion", "meeting", "agenda", "schedule"]
        ):
            try:
                notion_pages = await _search_notion(user_message)
                result_data["notion_pages"] = notion_pages
                result_data["azure_services_used"]["notion_search"] = len(notion_pages) > 0
                logger.info(f"🔍 Found {len(notion_pages)} Notion pages")

                if notion_pages:
                    for i, page in enumerate(notion_pages[:3]):
                        logger.info(f"📄 Notion page {i+1}: {page.get('title', 'No title')}")

            except Exception as e:
                logger.error(f"❌ Notion search failed: {e}", exc_info=True)

        # 2. Cosmos DB 벡터 검색
        document_chunks = []
        if cosmos_service:
            try:
                await cosmos_service.initialize_database()
                result_data["azure_services_used"]["cosmos_db"] = True

                # embedding 생성
                embedding = await openai_service.generate_embeddings(user_message)
                if embedding:
                    result_data["azure_services_used"]["openai_embedding"] = True

                    search_results = await cosmos_service.search_similar_chunks(
                        embedding, limit=5, similarity_threshold=0.1
                    )
                    if search_results:
                        result_data["azure_services_used"]["vector_search"] = True

                        document_chunks = [
                            {
                                "file_name": r.get("file_name", "unknown"),
                                "content": r.get("chunk_text", "")[:1000],
                                "similarity": r.get("similarity", 0.0)
                            }
                            for r in search_results
                        ]
                        result_data["sources"] = [
                            f"{r.get('file_name', '?')} ({int(r.get('similarity', 0.0)*100)}%)"
                            for r in search_results
                        ]

                    logger.info(f"🔍 Found {len(document_chunks)} document chunks")

            except Exception as e:
                logger.error(f"❌ Cosmos search failed: {e}", exc_info=True)

        result_data["document_chunks"] = document_chunks
        result_data["azure_services_used"]["document_chunks"] = len(document_chunks)

        # 3. Debug logs before sending to AI
        logger.info(f"🔍 Sending to AI - Notion pages: {len(notion_pages)}")
        logger.info(f"🔍 Sending to AI - Document chunks: {len(document_chunks)}")
        logger.info(f"🔍 User message: {user_message}")

        # 4. OpenAI 최종 응답 생성
        ai_response = await openai_service.generate_response(
            user_message=user_message,
            context=context,
            document_chunks=document_chunks,
            notion_pages=notion_pages,
            max_tokens=1500,
            temperature=0.7
        )

        if isinstance(ai_response, dict):
            response_text = ai_response.get("assistant_message", str(ai_response))
        else:
            response_text = str(ai_response)

        # 5. 응답이 너무 짧으면 Notion 데이터로 보강
        if len(response_text) < 100 and notion_pages:
            logger.warning(f"⚠️ AI response too short ({len(response_text)} chars), enhancing with Notion data")
            enhanced_response = response_text + "\n\n📝 **Notion에서 찾은 미팅 정보:**\n"
            for i, page in enumerate(notion_pages[:3]):
                title = page.get('title', 'Untitled')
                url = page.get('url', '')
                last_edited = page.get('last_edited_time', '')
                enhanced_response += f"\n{i+1}. **{title}**"
                if last_edited:
                    enhanced_response += f" (마지막 수정: {last_edited[:10]})"
                if url:
                    enhanced_response += f"\n   🔗 {url}"
                enhanced_response += "\n"
            response_text = enhanced_response
            logger.info(f"✅ Enhanced response with Notion data: {len(response_text)} characters")

        if not response_text.strip():
            response_text = "죄송합니다. 응답을 생성하는 데 문제가 발생했습니다. 다시 시도해주세요."

        result_data["assistant_message"] = response_text
        result_data["content"] = response_text
        result_data["azure_services_used"]["openai"] = True

        logger.info(f"✅ Generated response: {len(response_text)} characters")

    except Exception as e:
        logger.error(f"❌ Full chat processing failed: {e}", exc_info=True)
        error_msg = f"I apologize, but I encountered an error: {str(e)}"
        result_data["assistant_message"] = error_msg
        result_data["content"] = error_msg

    return result_data

async def _search_notion(query: str) -> list:
    """Search Notion pages asynchronously."""
    if not notion_service:
        return []

    try:
        if hasattr(notion_service, 'search_meeting_pages'):
            pages = await notion_service.search_meeting_pages(query)
        elif hasattr(notion_service, 'search_pages'):
            pages = await notion_service.search_pages(query, limit=5)
        else:
            return []

        detailed_pages = []
        for p in pages:
            if isinstance(p, dict):
                page_data = {
                    "id": p.get("id", ""),
                    "title": p.get("title", "Untitled"),
                    "url": p.get("url", ""),
                    "last_edited_time": p.get("last_edited_time", ""),
                    "created_time": p.get("created_time", ""),
                    "content": p.get("content", "")[:2000] if p.get("content") else ""
                }
                detailed_pages.append(page_data)

        return detailed_pages

    except Exception as e:
        logger.error(f"❌ Notion search error: {e}", exc_info=True)
        return []

async def _fix_embeddings_async():
    """Fix missing embeddings for all documents in Cosmos DB asynchronously."""
    base_result = {
        "total_documents": 0,
        "fixed_count": 0,
        "error_count": 0,
        "status": "완료"
    }

    try:
        cosmos_instance = CosmosVectorService()
        await cosmos_instance.initialize_database()

        # 모든 문서 조회
        container = cosmos_instance.container
        query = "SELECT * FROM c"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))

        base_result["total_documents"] = len(items)
        logger.info(f"📄 총 {len(items)}개 문서 검사 중...")

        for item in items:
            try:
                # embedding 필드가 없거나 비어 있으면
                if 'embedding' not in item or not item.get('embedding'):
                    chunk_text = item.get('chunk_text', '')
                    if chunk_text:
                        embedding = await openai_service.generate_embeddings(chunk_text)
                        if embedding and len(embedding) > 0:
                            item['embedding'] = embedding
                            container.upsert_item(item)
                            base_result["fixed_count"] += 1
                            logger.info(f"✅ 임베딩 추가: {item.get('file_name')} - chunk {item.get('chunk_index', 0)}")
                        else:
                            base_result["error_count"] += 1
                            logger.error(f"❌ 임베딩 생성 실패: {item.get('id')}")
            except Exception as e:
                base_result["error_count"] += 1
                logger.error(f"❌ 문서 처리 오류 {item.get('id')}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ _fix_embeddings_async 전체 오류: {e}", exc_info=True)
        base_result["status"] = "오류 발생"

    return base_result

# ─── Response Helpers ─────────────────────────────────────────────────────────

def _success_response(data, message="Success"):
    """Create standardized success response with CORS headers."""
    response = jsonify({
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

def _error_response(message, status_code=400):
    """Create standardized error response with CORS headers."""
    response = jsonify({
        "success": False,
        "error": message,
        "timestamp": datetime.now().isoformat()
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, status_code
