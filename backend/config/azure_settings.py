import os
from dotenv import load_dotenv

load_dotenv()

class AzureConfig:
    """Azure 서비스 설정"""
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
    
    # Azure Cosmos DB
    COSMOS_DB_ENDPOINT = os.getenv('COSMOS_DB_ENDPOINT')
    COSMOS_DB_KEY = os.getenv('COSMOS_DB_KEY')
    COSMOS_DB_DATABASE_NAME = os.getenv('COSMOS_DB_DATABASE_NAME', 'ai_training_backend')
    COSMOS_DB_CONTAINER_NAME = os.getenv('COSMOS_DB_CONTAINER_NAME', 'document_chunks')
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    AZURE_STORAGE_ACCOUNT_NAME = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    AZURE_STORAGE_CONTAINER_NAME = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents')
    
    # Notion API
    NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
    NOTION_API_VERSION = os.getenv('NOTION_API_VERSION', '2022-06-28')
    
    # Flask 설정
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # 보안 설정
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    API_KEY = os.getenv('API_KEY')  # API 접근용 키
    
    @classmethod
    def validate_required_settings(cls):
        """필수 설정 확인"""
        required_settings = [
            ('AZURE_OPENAI_ENDPOINT', cls.AZURE_OPENAI_ENDPOINT),
            ('AZURE_OPENAI_API_KEY', cls.AZURE_OPENAI_API_KEY),
            ('COSMOS_DB_ENDPOINT', cls.COSMOS_DB_ENDPOINT),
            ('COSMOS_DB_KEY', cls.COSMOS_DB_KEY),
        ]
        
        missing_settings = []
        for setting_name, setting_value in required_settings:
            if not setting_value:
                missing_settings.append(setting_name)
        
        if missing_settings:
            raise ValueError(f"다음 환경 변수들이 설정되지 않았습니다: {', '.join(missing_settings)}")
        
        return True