# routes/blob_sync_routes.py - Flask Backend로 Blob Storage 동기화 (수정된 버전)

from flask import Blueprint, request, jsonify
import asyncio
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Blueprint 생성
blob_sync_bp = Blueprint('blob_sync', __name__)

def async_route(f):
    """Flask route를 async 함수로 변환하는 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

@blob_sync_bp.route('/sync-all', methods=['POST'])
@async_route
async def sync_all_blobs():
    """모든 Blob Storage 파일을 Cosmos DB로 동기화"""
    try:
        # 서비스 초기화
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        await cosmos_service.initialize_database()
        
        # Blob Storage에서 모든 파일 가져오기
        logger.info("🔍 Blob Storage 파일 목록 가져오기...")
        files = await storage_service.list_files()
        
        results = {
            "processed_files": [],
            "failed_files": [],
            "total_files": len(files),
            "total_chunks": 0
        }
        
        for file_info in files:
            try:
                filename = file_info['name']
                logger.info(f"📄 처리 중: {filename}")
                
                # 지원되는 파일 형식인지 확인
                if not doc_processor.validate_file_format(filename):
                    logger.info(f"⏭️ 건너뛰기 (지원되지 않는 형식): {filename}")
                    continue
                
                # Cosmos DB에 이미 존재하는지 확인
                existing = await check_file_exists_in_cosmos(cosmos_service, filename)
                if existing:
                    logger.info(f"⏭️ 건너뛰기 (이미 존재): {filename}")
                    continue
                
                # Blob에서 파일 다운로드
                file_content = await storage_service.download_file(filename)
                
                # 텍스트 추출
                text_content = await doc_processor.extract_text_from_file(
                    file_content, filename
                )
                
                if len(text_content.strip()) < 100:
                    logger.warning(f"⚠️ 텍스트가 너무 짧음: {filename}")
                    continue
                
                # 텍스트 청킹
                chunks = split_text_into_chunks(text_content)
                
                # 각 청크를 벡터화하고 저장
                chunk_count = 0
                for i, chunk in enumerate(chunks):
                    # 임베딩 생성
                    embedding = await openai_service.generate_embeddings(chunk)
                    
                    # Cosmos DB에 저장
                    await cosmos_service.store_document_chunk(
                        file_name=filename,
                        chunk_text=chunk,
                        embedding=embedding,
                        chunk_index=i,
                        metadata={
                            "file_size": file_info.get('size', 0),
                            "last_modified": file_info.get('last_modified'),
                            "content_type": file_info.get('content_type'),
                            "source": "blob_storage"
                        }
                    )
                    chunk_count += 1
                
                results["processed_files"].append({
                    "filename": filename,
                    "chunks_created": chunk_count,
                    "file_size": file_info.get('size', 0)
                })
                results["total_chunks"] += chunk_count
                
                logger.info(f"✅ 완료: {filename} ({chunk_count} chunks)")
                
            except Exception as e:
                logger.error(f"❌ 파일 처리 실패 {filename}: {str(e)}")
                results["failed_files"].append({
                    "filename": filename,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"{len(results['processed_files'])} 파일 동기화 완료",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 동기화 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/sync-file', methods=['POST'])
@async_route
async def sync_single_file():
    """특정 파일 하나만 동기화"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({"error": "filename이 필요합니다"}), 400
        
        # 서비스 초기화
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        from services.azure_openai_service import AzureOpenAIService
        from services.document_processor import DocumentProcessor
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        openai_service = AzureOpenAIService()
        doc_processor = DocumentProcessor()
        
        await cosmos_service.initialize_database()
        
        # 파일 처리
        logger.info(f"📄 단일 파일 처리: {filename}")
        
        # Blob에서 파일 다운로드
        file_content = await storage_service.download_file(filename)
        
        # 텍스트 추출
        text_content = await doc_processor.extract_text_from_file(
            file_content, filename
        )
        
        # 청킹 및 벡터화
        chunks = split_text_into_chunks(text_content)
        chunk_count = 0
        
        for i, chunk in enumerate(chunks):
            embedding = await openai_service.generate_embeddings(chunk)
            
            await cosmos_service.store_document_chunk(
                file_name=filename,
                chunk_text=chunk,
                embedding=embedding,
                chunk_index=i,
                metadata={"source": "blob_storage_manual"}
            )
            chunk_count += 1
        
        return jsonify({
            "success": True,
            "message": f"파일 '{filename}' 동기화 완료",
            "chunks_created": chunk_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 단일 파일 동기화 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/status', methods=['GET'])
@async_route
async def sync_status():
    """동기화 상태 확인"""
    try:
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        
        await cosmos_service.initialize_database()
        
        # Blob Storage 파일 수
        blob_files = await storage_service.list_files()
        blob_count = len(blob_files)
        
        # Cosmos DB 문서 수
        cosmos_stats = await cosmos_service.get_document_stats()
        
        # 동기화되지 않은 파일 찾기
        not_synced = []
        for file_info in blob_files:
            filename = file_info['name']
            exists = await check_file_exists_in_cosmos(cosmos_service, filename)
            if not exists:
                not_synced.append(filename)
        
        return jsonify({
            "success": True,
            "status": {
                "blob_storage_files": blob_count,
                "cosmos_db_documents": cosmos_stats.get('total_documents', 0),
                "not_synced_files": len(not_synced),
                "not_synced_list": not_synced[:10],  # 최대 10개만 표시
                "sync_percentage": ((blob_count - len(not_synced)) / blob_count * 100) if blob_count > 0 else 0
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 상태 확인 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/health', methods=['GET'])
def health_check():
    """Blob 동기화 서비스 상태 확인"""
    return jsonify({
        "status": "healthy",
        "service": "blob_sync",
        "endpoints": [
            "/sync-all",
            "/sync-file", 
            "/status",
            "/health"
        ],
        "timestamp": datetime.now().isoformat()
    })

# 헬퍼 함수들
async def check_file_exists_in_cosmos(cosmos_service, filename: str) -> bool:
    """Cosmos DB에 파일이 이미 존재하는지 확인"""
    try:
        # hasattr로 메서드 존재 여부 확인
        if hasattr(cosmos_service, 'check_file_exists'):
            return await cosmos_service.check_file_exists(filename)
        else:
            # 대안: 직접 쿼리로 확인
            container = cosmos_service.container
            query = f"SELECT VALUE COUNT(1) FROM c WHERE c.file_name = '{filename}'"
            items = list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            return items[0] > 0 if items else False
    except Exception as e:
        logger.error(f"❌ 파일 존재 여부 확인 실패: {str(e)}")
        return False

def split_text_into_chunks(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> list:
    """텍스트를 청크로 분할"""
    chunks = []
    words = text.split()
    
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_chunk_size:
            current_chunk.append(word)
            current_length += len(word) + 1
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # 오버랩을 위해 마지막 몇 단어 유지
                overlap_words = max(0, min(overlap // 10, len(current_chunk) // 2))
                current_chunk = current_chunk[-overlap_words:] if overlap_words > 0 else []
                current_length = sum(len(w) + 1 for w in current_chunk)
                
            current_chunk.append(word)
            current_length += len(word) + 1
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks