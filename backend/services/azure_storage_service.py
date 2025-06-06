# services/azure_storage_service.py - Azure Blob Storage 서비스

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

class AzureStorageService:
    """Azure Blob Storage 서비스"""
    
    def __init__(self):
        """Azure Storage 서비스 초기화"""
        try:
            # 환경 변수에서 연결 문자열 가져오기
            self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            self.container_name = os.getenv('BLOB_CONTAINER_NAME', 'documents')
            
            if not self.connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING 환경 변수가 설정되지 않았습니다")
            
            # Blob Service Client 초기화
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            
            logger.info(f"✅ Azure Storage 서비스 초기화 완료 (Container: {self.container_name})")
            
        except Exception as e:
            logger.error(f"❌ Azure Storage 서비스 초기화 실패: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Storage 서비스 상태 확인"""
        try:
            # 컨테이너 존재 여부 확인
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_exists = container_client.exists()
            
            return {
                "status": "healthy",
                "container_exists": container_exists,
                "container_name": self.container_name,
                "service": "azure_storage"
            }
            
        except Exception as e:
            logger.error(f"❌ Storage 상태 확인 실패: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "azure_storage"
            }
    
    async def list_files(self, prefix: str = None) -> List[Dict[str, Any]]:
        """Blob Storage의 파일 목록 가져오기"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            # 컨테이너가 존재하지 않으면 빈 리스트 반환
            if not container_client.exists():
                logger.warning(f"⚠️ 컨테이너가 존재하지 않습니다: {self.container_name}")
                return []
            
            blob_list = container_client.list_blobs(name_starts_with=prefix)
            
            files = []
            for blob in blob_list:
                file_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "etag": blob.etag,
                    "creation_time": blob.creation_time.isoformat() if blob.creation_time else None
                }
                files.append(file_info)
            
            logger.info(f"📂 파일 목록 조회 완료: {len(files)}개 파일")
            return files
            
        except Exception as e:
            logger.error(f"❌ 파일 목록 조회 실패: {str(e)}")
            raise
    
    async def download_file(self, filename: str) -> bytes:
        """Blob Storage에서 파일 다운로드"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=filename
            )
            
            # 파일 존재 여부 확인
            if not blob_client.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filename}")
            
            # 파일 다운로드
            blob_data = blob_client.download_blob().readall()
            
            logger.info(f"📥 파일 다운로드 완료: {filename} ({len(blob_data)} bytes)")
            return blob_data
            
        except Exception as e:
            logger.error(f"❌ 파일 다운로드 실패 {filename}: {str(e)}")
            raise
    
    async def upload_file(self, filename: str, file_content: bytes, overwrite: bool = True) -> Dict[str, Any]:
        """파일을 Blob Storage에 업로드"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=filename
            )
            
            # 파일 업로드
            blob_client.upload_blob(
                file_content,
                overwrite=overwrite,
                content_settings={
                    'content_type': self._get_content_type(filename)
                }
            )
            
            logger.info(f"📤 파일 업로드 완료: {filename}")
            
            return {
                "success": True,
                "filename": filename,
                "size": len(file_content),
                "uploaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 파일 업로드 실패 {filename}: {str(e)}")
            raise
    
    async def delete_file(self, filename: str) -> bool:
        """Blob Storage에서 파일 삭제"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=filename
            )
            
            blob_client.delete_blob()
            
            logger.info(f"🗑️ 파일 삭제 완료: {filename}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"⚠️ 삭제할 파일이 존재하지 않습니다: {filename}")
            return False
        except Exception as e:
            logger.error(f"❌ 파일 삭제 실패 {filename}: {str(e)}")
            raise
    
    async def file_exists(self, filename: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=filename
            )
            
            return blob_client.exists()
            
        except Exception as e:
            logger.error(f"❌ 파일 존재 여부 확인 실패 {filename}: {str(e)}")
            return False
    
    async def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """파일 정보 가져오기"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=filename
            )
            
            if not blob_client.exists():
                return None
            
            properties = blob_client.get_blob_properties()
            
            return {
                "name": filename,
                "size": properties.size,
                "last_modified": properties.last_modified.isoformat(),
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "creation_time": properties.creation_time.isoformat() if properties.creation_time else None
            }
            
        except Exception as e:
            logger.error(f"❌ 파일 정보 조회 실패 {filename}: {str(e)}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """파일 확장자에 따른 Content-Type 반환"""
        extension = filename.lower().split('.')[-1]
        
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'json': 'application/json',
            'csv': 'text/csv'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    async def create_container_if_not_exists(self) -> bool:
        """컨테이너가 없으면 생성"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"📦 컨테이너 생성 완료: {self.container_name}")
                return True
            else:
                logger.info(f"📦 컨테이너 이미 존재: {self.container_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 컨테이너 생성 실패: {str(e)}")
            raise