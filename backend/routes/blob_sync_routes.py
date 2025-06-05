# routes/blob_sync_routes.py - 간단한 Blob Storage와 Cosmos DB 동기화

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

@blob_sync_bp.route('/health', methods=['GET'])
def health_check():
    """Blob 동기화 서비스 상태 확인"""
    return jsonify({
        "status": "healthy",
        "service": "blob_sync",
        "description": "Blob Storage to Cosmos DB synchronization",
        "endpoints": [
            "/health",
            "/sync-all",
            "/sync-file", 
            "/status",
            "/test-connection"
        ],
        "timestamp": datetime.now().isoformat()
    })

@blob_sync_bp.route('/test-connection', methods=['GET'])
@async_route
async def test_connection():
    """Blob Storage와 Cosmos DB 연결 테스트"""
    try:
        results = {
            "blob_storage": {"status": "unknown", "error": None},
            "cosmos_db": {"status": "unknown", "error": None}
        }
        
        # Blob Storage 연결 테스트
        try:
            from services.azure_storage_service import AzureStorageService
            storage_service = AzureStorageService()
            storage_health = await storage_service.health_check()
            results["blob_storage"] = storage_health
        except Exception as e:
            results["blob_storage"] = {"status": "error", "error": str(e)}
        
        # Cosmos DB 연결 테스트
        try:
            from services.cosmos_service import CosmosVectorService
            cosmos_service = CosmosVectorService()
            cosmos_health = await cosmos_service.health_check()
            results["cosmos_db"] = cosmos_health
        except Exception as e:
            results["cosmos_db"] = {"status": "error", "error": str(e)}
        
        # 전체 상태 결정
        overall_status = "healthy"
        if results["blob_storage"]["status"] != "healthy" or results["cosmos_db"]["status"] != "healthy":
            overall_status = "degraded"
        
        return jsonify({
            "success": True,
            "overall_status": overall_status,
            "services": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 연결 테스트 실패: {str(e)}")
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
        
        # Blob Storage 파일 목록
        try:
            blob_files = await storage_service.list_files()
            blob_count = len(blob_files)
        except Exception as e:
            blob_files = []
            blob_count = 0
            logger.error(f"❌ Blob 파일 목록 조회 실패: {e}")
        
        # Cosmos DB 통계
        try:
            await cosmos_service.initialize_database()
            cosmos_stats = await cosmos_service.get_blob_sync_stats()
        except Exception as e:
            cosmos_stats = {"total_blob_documents": 0, "total_blob_chunks": 0}
            logger.error(f"❌ Cosmos 통계 조회 실패: {e}")
        
        # 동기화 백분율 계산
        synced_count = cosmos_stats.get("total_blob_documents", 0)
        sync_percentage = (synced_count / blob_count * 100) if blob_count > 0 else 0
        
        return jsonify({
            "success": True,
            "status": {
                "blob_storage_files": blob_count,
                "cosmos_synced_documents": synced_count,
                "cosmos_chunks": cosmos_stats.get("total_blob_chunks", 0),
                "sync_percentage": round(sync_percentage, 2),
                "not_synced_count": blob_count - synced_count
            },
            "blob_files_sample": [f["name"] for f in blob_files[:5]],  # 첫 5개 파일명
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 상태 확인 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/sync-simple', methods=['POST'])
@async_route
async def sync_simple():
    """간단한 동기화 - 텍스트 파일만"""
    try:
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        
        await cosmos_service.initialize_database()
        
        # Blob Storage에서 텍스트 파일만 가져오기
        logger.info("🔍 텍스트 파일 검색 중...")
        all_files = await storage_service.list_files()
        text_files = [f for f in all_files if f['name'].lower().endswith(('.txt', '.md'))]
        
        results = {
            "processed_files": [],
            "failed_files": [],
            "total_found": len(text_files),
            "skipped_files": []
        }
        
        for file_info in text_files[:5]:  # 처음 5개만 처리
            try:
                filename = file_info['name']
                logger.info(f"📄 처리 중: {filename}")
                
                # 이미 존재하는지 확인
                exists = await cosmos_service.check_file_exists(filename)
                if exists:
                    results["skipped_files"].append(filename)
                    logger.info(f"⏭️ 건너뛰기 (이미 존재): {filename}")
                    continue
                
                # 파일 다운로드
                file_content = await storage_service.download_file(filename)
                
                # 텍스트 디코딩
                try:
                    text_content = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    text_content = file_content.decode('latin-1')
                
                # Cosmos DB에 저장
                doc_id = await cosmos_service.store_blob_document(
                    filename=filename,
                    content=text_content,
                    metadata={
                        "file_size": file_info.get('size', 0),
                        "content_type": "text/plain",
                        "sync_method": "simple"
                    }
                )
                
                results["processed_files"].append({
                    "filename": filename,
                    "document_id": doc_id,
                    "size": file_info.get('size', 0)
                })
                
                logger.info(f"✅ 완료: {filename}")
                
            except Exception as e:
                logger.error(f"❌ 파일 처리 실패 {filename}: {str(e)}")
                results["failed_files"].append({
                    "filename": filename,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"{len(results['processed_files'])} 텍스트 파일 동기화 완료",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 간단 동기화 실패: {str(e)}")
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
        filename = data.get('filename') if data else None
        
        if not filename:
            return jsonify({
                "success": False,
                "error": "filename 필드가 필요합니다",
                "example": {"filename": "document.txt"},
                "timestamp": datetime.now().isoformat()
            }), 400
        
        from services.azure_storage_service import AzureStorageService
        from services.cosmos_service import CosmosVectorService
        
        storage_service = AzureStorageService()
        cosmos_service = CosmosVectorService()
        
        await cosmos_service.initialize_database()
        
        logger.info(f"📄 단일 파일 동기화: {filename}")
        
        # 파일 존재 확인
        if not await storage_service.file_exists(filename):
            return jsonify({
                "success": False,
                "error": f"파일이 Blob Storage에 존재하지 않습니다: {filename}",
                "timestamp": datetime.now().isoformat()
            }), 404
        
        # 이미 동기화되었는지 확인
        if await cosmos_service.check_file_exists(filename):
            return jsonify({
                "success": True,
                "message": f"파일이 이미 동기화되어 있습니다: {filename}",
                "status": "already_synced",
                "timestamp": datetime.now().isoformat()
            })
        
        # 파일 다운로드 및 처리
        file_content = await storage_service.download_file(filename)
        
        # 간단한 텍스트 처리
        if filename.lower().endswith(('.txt', '.md')):
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_content.decode('latin-1')
        else:
            text_content = f"Binary file: {filename} (size: {len(file_content)} bytes)"
        
        # Cosmos DB에 저장
        doc_id = await cosmos_service.store_blob_document(
            filename=filename,
            content=text_content,
            metadata={
                "file_size": len(file_content),
                "sync_method": "manual"
            }
        )
        
        return jsonify({
            "success": True,
            "message": f"파일 '{filename}' 동기화 완료",
            "document_id": doc_id,
            "content_length": len(text_content),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 단일 파일 동기화 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@blob_sync_bp.route('/list-synced', methods=['GET'])
@async_route
async def list_synced_files():
    """동기화된 파일 목록"""
    try:
        from services.cosmos_service import CosmosVectorService
        
        cosmos_service = CosmosVectorService()
        await cosmos_service.initialize_database()
        
        synced_files = await cosmos_service.list_blob_files()
        
        return jsonify({
            "success": True,
            "synced_files": synced_files,
            "count": len(synced_files),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 동기화된 파일 목록 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# 에러 핸들러
@blob_sync_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Blob sync service error',
        'timestamp': datetime.now().isoformat()
    }), 500