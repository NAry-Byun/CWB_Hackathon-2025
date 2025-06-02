#!/usr/bin/env python3
"""
AI Personal Assistant Backend 시작 스크립트
"""

import os
import sys
import logging
from datetime import datetime
from app import create_app, initialize_backend_on_startup
from config.azure_settings import AzureConfig
from utils.azure_logger import setup_azure_logger

logger = setup_azure_logger(__name__)

def validate_environment():
    """환경 변수 검증"""
    try:
        AzureConfig.validate_required_settings()
        logger.info("✅ 모든 필수 환경 변수가 설정되었습니다")
        return True
    except ValueError as e:
        logger.error(f"❌ 환경 변수 오류: {e}")
        logger.error("💡 .env 파일을 확인하거나 환경 변수를 설정해주세요")
        return False

def main():
    """메인 실행 함수"""
    print("🚀 AI Personal Assistant Backend 시작")
    print("=" * 60)
    print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python 버전: {sys.version}")
    print("=" * 60)
    
    # 환경 변수 검증
    if not validate_environment():
        return 1
    
    # Flask 앱 생성
    try:
        app = create_app()
        logger.info("✅ Flask 앱이 성공적으로 생성되었습니다")
    except Exception as e:
        logger.error(f"❌ Flask 앱 생성 실패: {e}")
        return 1
    
    # 백엔드 초기화
    try:
        initialize_backend_on_startup()
        logger.info("✅ 백엔드 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ 백엔드 초기화 경고: {e}")
        logger.info("ℹ️ 백엔드는 첫 번째 요청 시 초기화됩니다")
    
    # 서버 설정
    host = AzureConfig.FLASK_HOST
    port = AzureConfig.FLASK_PORT
    debug = AzureConfig.FLASK_DEBUG
    
    print(f"🌐 서버 주소: http://{host}:{port}")
    print(f"🔧 디버그 모드: {debug}")
    print(f"📚 API 문서: http://{host}:{port}/")
    print(f"🏥 헬스 체크: http://{host}:{port}/health")
    print("=" * 60)
    print("🎯 주요 엔드포인트:")
    print(f"   💬 채팅: http://{host}:{port}/api/chat/enhanced-chat")
    print(f"   📄 문서: http://{host}:{port}/api/documents/upload")
    print(f"   📝 Notion: http://{host}:{port}/api/notion/search")
    print(f"   🎓 학습: http://{host}:{port}/api/training/run-comprehensive")
    print("=" * 60)
    
    try:
        # 서버 시작
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 서버가 정상적으로 종료되었습니다")
        return 0
    except Exception as e:
        logger.error(f"❌ 서버 시작 오류: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())