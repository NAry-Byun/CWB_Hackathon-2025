import json
import os
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class TrainingConfig:
    """AI 학습 백엔드 통합 설정"""
    
    def __init__(self, config_path: str = "config/training_config.json"):
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """JSON 파일에서 설정 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = self._get_default_config()
                self._save_default_config(config_data)
            
            training_config = config_data.get('training_config', {})
            
            # Azure OpenAI 설정
            openai_config = training_config.get('azure_openai', {})
            self.openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            self.openai_api_key = os.getenv('AZURE_OPENAI_API_KEY')
            self.chat_model = openai_config.get('chat_model', 'gpt-4o')
            self.embedding_model = openai_config.get('embedding_model', 'text-embedding-3-small')
            self.embedding_dimensions = openai_config.get('embedding_dimensions', 1536)
            
            # Cosmos DB 설정
            cosmos_config = training_config.get('cosmos_db', {})
            self.cosmos_endpoint = os.getenv('COSMOS_DB_ENDPOINT')
            self.cosmos_key = os.getenv('COSMOS_DB_KEY')
            self.cosmos_database = cosmos_config.get('database_name', 'ai_training_backend')
            self.cosmos_container = cosmos_config.get('container_name', 'document_chunks')
            
            # 학습 설정
            training_settings = training_config.get('training_settings', {})
            self.chunk_size = training_settings.get('chunk_size', 1000)
            self.chunk_overlap = training_settings.get('chunk_overlap', 200)
            self.embedding_batch_size = training_settings.get('embedding_batch_size', 10)
            self.max_concurrent_files = training_settings.get('max_concurrent_files', 5)
            self.rate_limit_rpm = training_settings.get('rate_limit_rpm', 3000)
            
            # 학습 소스 설정
            sources = training_config.get('training_sources', {})
            
            # 로컬 디렉토리
            directories = sources.get('directories', [])
            self.local_training_enabled = len(directories) > 0
            self.local_directories = directories
            
            # Azure Storage
            azure_storage = sources.get('azure_storage', [])
            self.azure_storage_enabled = len(azure_storage) > 0
            self.azure_storage_containers = azure_storage
            
            # Notion
            notion_config = sources.get('notion', {})
            self.notion_enabled = notion_config.get('enabled', False)
            self.notion_database_ids = notion_config.get('database_ids', [])
            self.notion_page_ids = notion_config.get('page_ids', [])
            
            # 웹 스크래핑
            web_config = sources.get('web_scraping', {})
            self.web_scraping_enabled = web_config.get('enabled', False)
            self.web_urls = web_config.get('urls', [])
            self.web_sitemaps = web_config.get('sitemaps', [])
            
        except Exception as e:
            raise Exception(f"설정 파일 로드 실패 {self.config_path}: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "training_config": {
                "description": "AI Training Backend Configuration",
                "version": "1.0",
                "azure_openai": {
                    "chat_model": "gpt-4o",
                    "embedding_model": "text-embedding-3-small",
                    "embedding_dimensions": 1536
                },
                "cosmos_db": {
                    "database_name": "ai_training_backend",
                    "container_name": "document_chunks"
                },
                "training_sources": {
                    "directories": [
                        {
                            "path": "./data/documents",
                            "recursive": True,
                            "batch_size": 5,
                            "source_type": "document",
                            "enabled": True
                        }
                    ],
                    "azure_storage": [],
                    "notion": {
                        "database_ids": [],
                        "page_ids": [],
                        "enabled": False
                    },
                    "web_scraping": {
                        "urls": [],
                        "sitemaps": [],
                        "enabled": False
                    }
                },
                "training_settings": {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "embedding_batch_size": 10,
                    "max_concurrent_files": 5,
                    "rate_limit_rpm": 3000
                }
            }
        }
    
    def _save_default_config(self, config_data: Dict[str, Any]):
        """기본 설정 파일 저장"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)