# services/document_service.py - 간단한 버전
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.cosmos_service = None
        self.openai_service = None
        self.storage_service = None
        logger.info("📚 DocumentProcessor initialized")
    
    def set_services(self, cosmos_service=None, openai_service=None, storage_service=None):
        self.cosmos_service = cosmos_service
        self.openai_service = openai_service
        self.storage_service = storage_service
    
    async def process_blob_storage_files(self):
        if self.cosmos_service:
            return await self.cosmos_service.process_storage_files()
        return {'success': False, 'error': 'Cosmos service not available'}
    
    async def health_check(self):
        return {"status": "healthy", "service": "DocumentProcessor"}