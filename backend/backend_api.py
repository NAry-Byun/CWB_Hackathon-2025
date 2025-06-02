import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uvicorn

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main_training import AITrainingBackend

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for API requests
class TrainingRequest(BaseModel):
    source_type: str  # "local", "azure_storage", "notion", "web", "sitemap", "all"
    path: Optional[str] = None
    container_name: Optional[str] = None
    blob_prefix: Optional[str] = None
    urls: Optional[List[str]] = None
    base_url: Optional[str] = None
    database_ids: Optional[List[str]] = None
    page_ids: Optional[List[str]] = None
    max_pages: Optional[int] = 50
    batch_size: Optional[int] = 5
    recursive: Optional[bool] = True

class ContentRequest(BaseModel):
    content: str
    source_type: str = "manual"
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    min_similarity: float = 0.7

class TrainingResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str

# Initialize FastAPI app
app = FastAPI(
    title="AI Training Backend API",
    description="Backend API for AI training with Cosmos DB, Azure Storage, Notion, and Web Scraping",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global backend instance
backend: Optional[AITrainingBackend] = None

@app.on_event("startup")
async def startup_event():
    """Initialize backend on startup"""
    global backend
    try:
        backend = AITrainingBackend()
        await backend.initialize_services()
        logger.info("Backend API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize backend: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Training Backend API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if backend and backend.initialized:
            stats = await backend.get_training_statistics()
            return {
                "status": "healthy",
                "services": {
                    "cosmos_db": "connected",
                    "azure_openai": "connected",
                    "training_service": "ready"
                },
                "knowledge_base": {
                    "total_documents": stats.get("knowledgeBase", {}).get("totalDocuments", 0)
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "initializing",
                "message": "Backend services are initializing",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/initialize")
async def initialize_infrastructure():
    """Initialize Cosmos DB infrastructure"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        await backend.initialize_infrastructure()
        
        return TrainingResponse(
            status="success",
            message="Infrastructure initialized successfully",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Infrastructure initialization failed: {str(e)}")

@app.post("/train")
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Start training process"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        # Add training task to background
        if request.source_type == "local":
            if not request.path:
                raise HTTPException(status_code=400, detail="Path is required for local training")
            background_tasks.add_task(
                _background_local_training,
                request.path,
                request.recursive,
                request.batch_size
            )
            message = f"Local training started for: {request.path}"
        
        elif request.source_type == "azure_storage":
            if not request.container_name:
                raise HTTPException(status_code=400, detail="Container name is required for Azure Storage training")
            background_tasks.add_task(
                _background_storage_training,
                request.container_name,
                request.blob_prefix,
                request.batch_size
            )
            message = f"Azure Storage training started for container: {request.container_name}"
        
        elif request.source_type == "notion":
            background_tasks.add_task(
                _background_notion_training,
                request.database_ids,
                request.page_ids
            )
            message = "Notion training started"
        
        elif request.source_type == "web":
            if not request.urls:
                raise HTTPException(status_code=400, detail="URLs are required for web training")
            background_tasks.add_task(
                _background_web_training,
                request.urls
            )
            message = f"Web training started for {len(request.urls)} URLs"
        
        elif request.source_type == "sitemap":
            if not request.base_url:
                raise HTTPException(status_code=400, detail="Base URL is required for sitemap training")
            background_tasks.add_task(
                _background_sitemap_training,
                request.base_url,
                request.max_pages
            )
            message = f"Sitemap training started for: {request.base_url}"
        
        elif request.source_type == "all":
            background_tasks.add_task(_background_comprehensive_training)
            message = "Comprehensive training started from all configured sources"
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source type: {request.source_type}")
        
        return TrainingResponse(
            status="started",
            message=message,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed to start: {str(e)}")

@app.post("/train/sync")
async def train_synchronous(request: TrainingRequest):
    """Synchronous training endpoint"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        result = None
        
        if request.source_type == "local":
            if not request.path:
                raise HTTPException(status_code=400, detail="Path is required for local training")
            result = await backend.train_from_local_files(
                request.path, 
                request.recursive, 
                request.batch_size
            )
        
        elif request.source_type == "azure_storage":
            if not request.container_name:
                raise HTTPException(status_code=400, detail="Container name is required")
            result = await backend.train_from_azure_storage(
                request.container_name,
                request.blob_prefix,
                request.batch_size
            )
        
        elif request.source_type == "notion":
            result = await backend.train_from_notion(
                request.database_ids,
                request.page_ids
            )
        
        elif request.source_type == "web":
            if not request.urls:
                raise HTTPException(status_code=400, detail="URLs are required")
            result = await backend.train_from_web_urls(request.urls)
        
        elif request.source_type == "sitemap":
            if not request.base_url:
                raise HTTPException(status_code=400, detail="Base URL is required")
            result = await backend.train_from_website_sitemap(
                request.base_url,
                request.max_pages
            )
        
        elif request.source_type == "all":
            result = await backend.run_comprehensive_training()
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source type: {request.source_type}")
        
        return TrainingResponse(
            status="completed",
            message="Training completed successfully",
            data=result,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/content/add")
async def add_content(request: ContentRequest):
    """Add manual content to knowledge base"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        document_ids = await backend.add_manual_content(
            request.content,
            request.source_type,
            request.metadata
        )
        
        return TrainingResponse(
            status="success",
            message=f"Content added successfully: {len(document_ids)} documents created",
            data={"document_ids": document_ids},
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add content: {str(e)}")

@app.post("/search")
async def search_knowledge_base(request: SearchRequest):
    """Search the knowledge base"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        results = await backend.search_knowledge_base(
            request.query,
            request.top_k,
            request.min_similarity
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/stats")
async def get_training_statistics():
    """Get training statistics"""
    try:
        if not backend:
            raise HTTPException(status_code=500, detail="Backend not initialized")
        
        stats = await backend.get_training_statistics()
        
        return {
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@app.get("/status")
async def get_training_status():
    """Get current training status"""
    try:
        if not backend:
            return {
                "status": "not_initialized",
                "message": "Backend not initialized",
                "timestamp": datetime.now().isoformat()
            }
        
        stats = await backend.get_training_statistics()
        
        return {
            "status": "ready",
            "initialized": backend.initialized,
            "knowledge_base": {
                "total_documents": stats.get("knowledgeBase", {}).get("totalDocuments", 0),
                "total_conversations": stats.get("conversations", {}).get("totalConversations", 0),
                "source_distribution": stats.get("knowledgeBase", {}).get("sourceDistribution", {})
            },
            "services": {
                "cosmos_db": "azure_storage" in backend.services,
                "azure_storage": "azure_storage" in backend.services,
                "notion": "notion" in backend.services,
                "web_scraper": "web_scraper" in backend.services
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

# Background task functions
async def _background_local_training(path: str, recursive: bool, batch_size: int):
    """Background task for local training"""
    try:
        result = await backend.train_from_local_files(path, recursive, batch_size)
        logger.info(f"Background local training completed: {result}")
    except Exception as e:
        logger.error(f"Background local training failed: {e}")

async def _background_storage_training(container_name: str, blob_prefix: Optional[str], batch_size: int):
    """Background task for Azure Storage training"""
    try:
        result = await backend.train_from_azure_storage(container_name, blob_prefix, batch_size)
        logger.info(f"Background storage training completed: {result}")
    except Exception as e:
        logger.error(f"Background storage training failed: {e}")

async def _background_notion_training(database_ids: Optional[List[str]], page_ids: Optional[List[str]]):
    """Background task for Notion training"""
    try:
        result = await backend.train_from_notion(database_ids, page_ids)
        logger.info(f"Background Notion training completed: {result}")
    except Exception as e:
        logger.error(f"Background Notion training failed: {e}")

async def _background_web_training(urls: List[str]):
    """Background task for web training"""
    try:
        result = await backend.train_from_web_urls(urls)
        logger.info(f"Background web training completed: {result}")
    except Exception as e:
        logger.error(f"Background web training failed: {e}")

async def _background_sitemap_training(base_url: str, max_pages: int):
    """Background task for sitemap training"""
    try:
        result = await backend.train_from_website_sitemap(base_url, max_pages)
        logger.info(f"Background sitemap training completed: {result}")
    except Exception as e:
        logger.error(f"Background sitemap training failed: {e}")

async def _background_comprehensive_training():
    """Background task for comprehensive training"""
    try:
        result = await backend.run_comprehensive_training()
        logger.info(f"Background comprehensive training completed: {result}")
    except Exception as e:
        logger.error(f"Background comprehensive training failed: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )