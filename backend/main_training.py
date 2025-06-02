# main_training.py
import asyncio
import logging
import os
import sys
from typing import Dict, List, Any
from datetime import datetime
import json
from dotenv import load_dotenv

# ─── SET UP LOGGER ───
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ─── LOAD ENVIRONMENT VARIABLES ───
load_dotenv()

# ─── ENSURE “services/” IS ON THE PYTHON PATH ───
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ─── TRY TO IMPORT REAL CosmosVectorService ───
try:
    from services.cosmos_service import CosmosVectorService
    logger.info("✅ Real CosmosVectorService imported successfully")
except ImportError:
    logger.error("❌ CRITICAL: Could not import real CosmosVectorService!")

    class CosmosVectorService:
        """Dummy fallback CosmosVectorService for local development."""

        async def initialize_database(self):
            logger.warning("⚠️ Dummy initialize_database() called (no real Cosmos).")
            return

        async def store_document_chunk(
            self,
            file_name: str,
            chunk_text: str,
            embedding: List[float],
            chunk_index: int,
            metadata: Dict
        ):
            logger.warning("⚠️ Using DUMMY Cosmos service – install azure-cosmos and create cosmos_service.py")
            return f"doc_id_{chunk_index}"

        async def search_similar_chunks(self, query_embedding: List[float], limit: int = 5, similarity_threshold: float = 0.3):
            return []

        async def health_check(self):
            return {"status": "dummy", "documents": 0}

        async def get_document_stats(self):
            return {"count": 0}

        async def close(self):
            logger.warning("⚠️ Dummy close() called (no real Cosmos).")
            return


class AzureConfig:
    NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
    AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

    @staticmethod
    def validate_required_settings():
        """Validate that mandatory environment variables are present."""
        required_vars = ['AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        print("🔍 Checking environment variables:")
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value[:20]}..." if len(value) > 20 else f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: Not found")

        if missing_vars:
            raise ValueError(f"Required environment variables missing: {missing_vars}")


class TrainingConfig:
    """Holds configuration flags for training."""
    def __init__(self, config_path: str = "config/training_config.json"):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.notion_enabled = bool(os.getenv('NOTION_API_TOKEN'))
        self.azure_storage_enabled = bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        self.web_scraping_enabled = False
        self.local_training_enabled = True


class NotionMCPService:
    """Dummy Notion service if real one is not loaded."""
    async def search_pages(self, query: str, limit: int):
        return []

    async def get_page_content(self, page_id: str):
        return {"success": False}


class AITrainingBackend:
    """Main orchestrator for AI training, service initialization, and health checks."""

    def __init__(self, config_path: str = "config/training_config.json"):
        self.config = TrainingConfig(config_path)
        self.services: Dict[str, Any] = {}
        self.initialized = False
        logger.info("🤖 AI Training Backend initialized")

    async def initialize_services(self):
        """Initialize Azure OpenAI, Cosmos DB, Document Processor, Notion, etc."""
        try:
            logger.info("🚀 Starting service initialization...")

            # 1) Validate environment variables for Azure OpenAI
            AzureConfig.validate_required_settings()

            # 2) Initialize Azure OpenAI Service
            from services.azure_openai_service import AzureOpenAIService
            self.services['openai'] = AzureOpenAIService()
            logger.info("✅ Azure OpenAI service initialized")

            # 3) Initialize a Document Processor (stub or real)
            try:
                from services.document_service import DocumentProcessor
            except ImportError:
                try:
                    from document_service import DocumentProcessor
                except ImportError:
                    logger.warning("⚠️ DocumentProcessor not found, using dummy")
                    class DocumentProcessor:
                        def __init__(self, chunk_size, chunk_overlap):
                            self.chunk_size = chunk_size
                            self.chunk_overlap = chunk_overlap

                        async def health_check(self):
                            return {"status": "healthy"}

            self.services['document_processor'] = DocumentProcessor(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
            logger.info("✅ DocumentProcessor initialized")

            # 4) Initialize Cosmos DB Service (real or dummy)
            logger.info("🌌 Initializing Cosmos DB service...")
            self.services['cosmos'] = CosmosVectorService()
            await self.services['cosmos'].initialize_database()
            logger.info("✅ Cosmos DB service initialized successfully!")

            # 5) Optionally initialize Notion service
            if self.config.notion_enabled and AzureConfig.NOTION_API_TOKEN:
                try:
                    from services.notion_service import NotionService
                    self.services['notion'] = NotionService()
                    logger.info("📝 Notion service activated")
                except Exception as e:
                    logger.warning(f"⚠️ Notion service initialization failed: {e}")
                    self.services['notion'] = NotionMCPService()

            # 6) Health check for all services
            await self._health_check_services()

            self.initialized = True
            logger.info("✅ All services successfully initialized")
            logger.info(f"🔧 Active services: {list(self.services.keys())}")

        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            raise

    async def process_document_with_embedding(
        self,
        file_name: str,
        content: str,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Processes a single document by chunking, generating embeddings, and storing to Cosmos DB."""
        try:
            logger.info(f"📄 Starting document processing: {file_name}")

            # 1) Chunk the content
            chunks = [
                content[i : i + self.config.chunk_size]
                for i in range(0, len(content), self.config.chunk_size - self.config.chunk_overlap)
            ]
            total_chunks = len(chunks)
            stored_chunks = []

            # 2) For each chunk, generate an embedding and store it
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self.services['openai'].generate_embeddings(chunk)
                    if embedding:
                        doc_id = await self.services['cosmos'].store_document_chunk(
                            file_name=file_name,
                            chunk_text=chunk,
                            embedding=embedding,
                            chunk_index=i,
                            metadata=metadata or {}
                        )
                        stored_chunks.append(doc_id)
                        logger.info(f"✅ Chunk {i+1}/{total_chunks} stored in Cosmos DB")
                except Exception as e:
                    logger.error(f"❌ Chunk {i} processing failed: {e}")
                    continue

            result = {
                'success': True,
                'document_ids': stored_chunks,
                'chunks_processed': len(stored_chunks),
                'total_chunks': total_chunks,
                'metadata': {'file_name': file_name}
            }
            logger.info(
                f"✅ Document processing completed: {file_name} - "
                f"{len(stored_chunks)}/{total_chunks} chunks stored"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Document processing failed: {e}")
            return {'success': False, 'error': str(e)}

    async def run_comprehensive_training(self) -> Dict[str, Any]:
        """Runs training across all configured sources (e.g., local files)."""
        logger.info("🎓 Starting comprehensive training")

        results = {
            'summary': {
                'totalDocuments': 0,
                'totalSources': 0,
                'sources': {},
                'startTime': datetime.now().isoformat(),
                'endTime': None
            },
            'errors': []
        }

        try:
            if self.config.local_training_enabled:
                try:
                    local_result = await self.train_from_local_files()
                    results['summary']['sources']['local'] = local_result
                    results['summary']['totalDocuments'] += local_result.get('documents_processed', 0)
                    logger.info(
                        f"📁 Local files training completed: "
                        f"{local_result.get('documents_processed', 0)} documents"
                    )
                except Exception as e:
                    error_msg = f"Local files training failed: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(f"❌ {error_msg}")

            results['summary']['totalSources'] = len(results['summary']['sources'])
            results['summary']['endTime'] = datetime.now().isoformat()

            logger.info(
                f"🎉 Comprehensive training completed: "
                f"{results['summary']['totalDocuments']} documents, "
                f"{results['summary']['totalSources']} sources"
            )
            return results

        except Exception as e:
            error_msg = f"Comprehensive training failed: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            return results

    async def train_from_local_files(
        self,
        directory_path: str = None
    ) -> Dict[str, Any]:
        """Processes all local files in `directory_path` by chunking + embedding + storing to Cosmos."""
        if not directory_path:
            directory_path = "./data/documents"

        result = {
            'documents_processed': 0,
            'files_found': 0,
            'errors': []
        }

        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
                logger.info(f"📁 Directory created: {directory_path}")
                return result

            supported_extensions = ['.txt', '.md', '.json', '.csv']

            for root, _, files in os.walk(directory_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in supported_extensions):
                        result['files_found'] += 1
                        file_path = os.path.join(root, file)

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                            if content.strip():
                                doc_result = await self.process_document_with_embedding(
                                    file_name=file,
                                    content=content,
                                    metadata={
                                        'source': 'local_file',
                                        'file_path': file_path,
                                        'processed_at': datetime.now().isoformat()
                                    }
                                )
                                if doc_result.get('success'):
                                    result['documents_processed'] += 1

                        except Exception as e:
                            error_msg = f"File processing failed {file_path}: {str(e)}"
                            result['errors'].append(error_msg)
                            logger.error(f"❌ {error_msg}")

            return result

        except Exception as e:
            logger.error(f"❌ Local files training failed: {e}")
            result['errors'].append(str(e))
            return result

    async def get_training_statistics(self) -> Dict[str, Any]:
        """Return status of all services including Cosmos DB stats."""
        try:
            stats: Dict[str, Any] = {
                'knowledgeBase': {},
                'services': {},
                'configuration': {}
            }

            # Cosmos DB stats
            if 'cosmos' in self.services:
                cosmos_stats = await self.services['cosmos'].health_check()
                cosmos_data = await self.services['cosmos'].get_document_stats()
                stats['knowledgeBase'] = {**cosmos_stats, **cosmos_data}

            # Each service health check
            for service_name, service in self.services.items():
                if hasattr(service, 'health_check'):
                    service_health = await service.health_check()
                    stats['services'][service_name] = service_health

            # Config info
            stats['configuration'] = {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap,
                'services_enabled': {
                    'notion': self.config.notion_enabled,
                    'azure_storage': self.config.azure_storage_enabled,
                    'web_scraping': self.config.web_scraping_enabled
                }
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Statistics query failed: {e}")
            return {'error': str(e)}

    async def _health_check_services(self):
        """Iterate over each service and call its `health_check()` if available."""
        logger.info("🏥 Checking services status...")

        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'health_check'):
                    health = await service.health_check()
                    if health.get('status') not in ['healthy', 'dummy']:
                        logger.warning(f"⚠️ {service_name} service status warning: {health}")
                    else:
                        logger.info(f"✅ {service_name} service is {health.get('status', 'unknown')}")
                else:
                    logger.info(f"ℹ️ {service_name} service does not have health check functionality")
            except Exception as e:
                logger.error(f"❌ {service_name} service health check failed: {e}")
                raise Exception(f"Service {service_name} health check failed")


# ─── CLI / ENTRYPOINT ───

async def main():
    """Main CLI function for training, stats, or test flags."""
    import argparse

    parser = argparse.ArgumentParser(description='AI Training Backend')
    parser.add_argument('--init', action='store_true', help='Initialize services')
    parser.add_argument('--train-local', type=str, help='Train from local files')
    parser.add_argument('--train-comprehensive', action='store_true', help='Run comprehensive training')
    parser.add_argument('--stats', action='store_true', help='Query statistics')
    parser.add_argument('--test-env', action='store_true', help='Test environment variables')
    parser.add_argument('--test-cosmos', action='store_true', help='Test Cosmos DB connection')

    args = parser.parse_args()

    # 1) Test environment variables only
    if args.test_env:
        print("🧪 Testing environment variables:")
        env_vars = [
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_DEPLOYMENT_NAME',
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT',
            'COSMOS_DB_ENDPOINT',
            'COSMOS_DB_KEY'
        ]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value[:20]}..." if len(value) > 20 else f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: Not found")
        return 0

    # 2) Test Cosmos DB connection only
    if args.test_cosmos:
        print("🌌 Testing Cosmos DB connection...")
        try:
            cosmos = CosmosVectorService()
            await cosmos.initialize_database()
            health = await cosmos.health_check()
            stats = await cosmos.get_document_stats()
            print(f"✅ Cosmos DB Health: {health}")
            print(f"📊 Cosmos DB Stats: {stats}")
            await cosmos.close()
        except Exception as e:
            print(f"❌ Cosmos DB test failed: {e}")
        return 0

    # 3) Initialize backend and run commands
    backend = AITrainingBackend()
    try:
        await backend.initialize_services()

        if args.init:
            print("✅ Service initialization completed")

        elif args.train_local:
            result = await backend.train_from_local_files(args.train_local)
            print(f"📁 Local training completed: {result}")

        elif args.train_comprehensive:
            result = await backend.run_comprehensive_training()
            print(f"🎓 Comprehensive training completed: {result}")

        elif args.stats:
            stats = await backend.get_training_statistics()
            print(f"📊 Statistics: {json.dumps(stats, indent=2, ensure_ascii=False)}")

        else:
            print("Usage: python main_training.py --help")

    except Exception as e:
        logger.error(f"❌ Execution failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
