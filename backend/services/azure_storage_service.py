import os
import logging
from azure.storage.blob import BlobServiceClient
from typing import Dict, List, Any, Optional
from datetime import datetime

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureStorageService:
    """Azure Blob Storage 서비스"""
    
    def __init__(self):
        """Azure Storage 서비스 초기화"""
        try:
            # Get configuration from environment variables
            self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
            self.container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents')
            
            if not self.connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is required")
            
            # Blob 서비스 클라이언트 초기화
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            
            # 컨테이너 존재 확인 및 생성
            self._ensure_container_exists()
            
            logger.info(f"📦 Azure Storage 서비스 초기화됨: {self.account_name or 'unknown'}")
            
        except Exception as e:
            logger.error(f"❌ Azure Storage 초기화 실패: {e}")
            raise
    
    def _ensure_container_exists(self):
        """컨테이너 존재 확인 및 생성"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
            logger.info(f"✅ 컨테이너 '{self.container_name}' 존재 확인")
        except:
            try:
                self.blob_service_client.create_container(self.container_name)
                logger.info(f"✅ 컨테이너 '{self.container_name}' 생성됨")
            except Exception as e:
                logger.error(f"❌ 컨테이너 생성 실패: {e}")
    
    async def upload_file(self, file_name: str, file_content: bytes, content_type: str = 'application/octet-stream') -> Optional[str]:
        """파일을 Azure Blob Storage에 업로드"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=file_name
            )
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={'content_type': content_type}
            )
            
            blob_url = blob_client.url
            logger.info(f"📤 파일 업로드 완료: {file_name}")
            return blob_url
            
        except Exception as e:
            logger.error(f"❌ 파일 업로드 실패: {e}")
            return None
    
    async def download_file(self, file_name: str) -> Optional[bytes]:
        """Azure Blob Storage에서 파일 다운로드"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=file_name
            )
            
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            
            logger.info(f"📥 파일 다운로드 완료: {file_name}")
            return content
            
        except Exception as e:
            logger.error(f"❌ 파일 다운로드 실패: {e}")
            return None
    
    async def list_files(self, prefix: str = None) -> List[Dict[str, Any]]:
        """컨테이너의 파일 목록 조회"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            files = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None
                })
            
            logger.info(f"📋 파일 목록 조회 완료: {len(files)}개 파일")
            return files
            
        except Exception as e:
            logger.error(f"❌ 파일 목록 조회 실패: {e}")
            return []
    
    async def delete_file(self, file_name: str) -> bool:
        """파일 삭제"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=file_name
            )
            
            blob_client.delete_blob()
            logger.info(f"🗑️ 파일 삭제 완료: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 파일 삭제 실패: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Azure Storage 서비스 상태 확인"""
        try:
            # 컨테이너 정보 조회로 연결 확인
            container_client = self.blob_service_client.get_container_client(self.container_name)
            properties = container_client.get_container_properties()
            
            return {
                "status": "healthy",
                "service": "Azure Storage",
                "account_name": self.account_name or "unknown",
                "container_name": self.container_name,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "connectivity": "successful"
            }
            
        except Exception as e:
            logger.error(f"❌ Azure Storage 상태 확인 실패: {e}")
            return {
                "status": "unhealthy",
                "service": "Azure Storage",
                "error": str(e),
                "connectivity": "failed"
            }