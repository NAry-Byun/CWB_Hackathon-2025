#!/usr/bin/env python3
"""
Flask AI Chat Backend 시작 스크립트
"""

import os
import sys
from app import create_app

def main():
    """메인 실행 함수"""
    
    # 환경 변수 확인
    required_env_vars = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'COSMOS_DB_ENDPOINT',
        'COSMOS_DB_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 다음 환경 변수들이 설정되지 않았습니다:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n.env 파일을 확인하거나 환경 변수를 설정해주세요.")
        return 1
    
    # Flask 앱 생성
    app = create_app()
    
    # 포트 설정
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Flask AI Chat Backend 시작")
    print(f"📍 주소: http://{host}:{port}")
    print(f"🔧 디버그 모드: {debug}")
    print(f"🌐 CORS 활성화됨")
    print(f"📁 업로드 폴더: ./uploads")
    print("=" * 50)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n👋 서버가 정상적으로 종료되었습니다.")
        return 0
    except Exception as e:
        print(f"❌ 서버 시작 오류: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())