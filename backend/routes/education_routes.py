# routes/education_routes.py - 교육 콘텐츠 생성 라우트

from flask import Blueprint, request, jsonify
import asyncio
import logging
from datetime import datetime
from functools import wraps
import os

logger = logging.getLogger(__name__)

# Blueprint 생성
education_bp = Blueprint('education', __name__)

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

@education_bp.route('/health', methods=['GET'])
def health_check():
    """교육 서비스 상태 확인"""
    return jsonify({
        "status": "healthy",
        "service": "education",
        "endpoints": [
            "/process",
            "/documents", 
            "/documents/<id>",
            "/health",
            "/stats"
        ],
        "features": [
            "Document Processing",
            "Flashcard Generation",
            "Quiz Generation", 
            "Summary Generation"
        ],
        "timestamp": datetime.now().isoformat()
    })

@education_bp.route('/process', methods=['POST'])
@async_route
async def process_document():
    """문서를 업로드하고 교육 콘텐츠 생성"""
    try:
        # 파일 업로드 확인
        if 'file' not in request.files:
            return jsonify({"error": "파일이 업로드되지 않았습니다"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "파일이 선택되지 않았습니다"}), 400
        
        # 서비스 초기화
        from services.document_processor import DocumentProcessor
        from services.azure_openai_service import AzureOpenAIService
        
        doc_processor = DocumentProcessor()
        openai_service = AzureOpenAIService()
        
        # 파일 형식 검증
        if not doc_processor.validate_file_format(file.filename):
            return jsonify({
                "error": f"지원되지 않는 파일 형식입니다. 지원 형식: {list(doc_processor.supported_formats.keys())}"
            }), 400
        
        # 파일 내용 읽기
        file_content = file.read()
        
        # 텍스트 추출
        logger.info(f"📄 텍스트 추출 시작: {file.filename}")
        text_content = await doc_processor.extract_text_from_file(file_content, file.filename)
        
        if len(text_content.strip()) < 50:
            return jsonify({"error": "추출된 텍스트가 너무 짧습니다"}), 400
        
        # 교육 콘텐츠 생성
        logger.info("🎓 교육 콘텐츠 생성 시작...")
        
        # 플래시카드 생성
        flashcards = await generate_flashcards(openai_service, text_content)
        
        # 퀴즈 생성
        quiz = await generate_quiz(openai_service, text_content)
        
        # 요약 생성
        summary = await generate_summary(openai_service, text_content)
        
        # 결과 구성
        result = {
            "success": True,
            "filename": file.filename,
            "content_length": len(text_content),
            "generated_content": {
                "flashcards": flashcards,
                "quiz": quiz,
                "summary": summary
            },
            "processing_time": datetime.now().isoformat(),
            "stats": {
                "flashcard_count": len(flashcards),
                "quiz_question_count": len(quiz.get("questions", [])),
                "summary_length": len(summary)
            }
        }
        
        logger.info(f"✅ 교육 콘텐츠 생성 완료: {file.filename}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ 교육 콘텐츠 생성 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@education_bp.route('/documents', methods=['GET'])
def list_documents():
    """저장된 교육 문서 목록"""
    try:
        # 간단한 파일 목록 (실제로는 데이터베이스에서 가져와야 함)
        upload_dir = './data/uploads'
        documents = []
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    documents.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return jsonify({
            "success": True,
            "documents": documents,
            "total_count": len(documents),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 문서 목록 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@education_bp.route('/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """특정 문서 정보 조회"""
    return jsonify({
        "success": True,
        "document_id": doc_id,
        "message": "문서 상세 정보 (구현 예정)",
        "timestamp": datetime.now().isoformat()
    })

@education_bp.route('/stats', methods=['GET'])
def get_stats():
    """교육 서비스 통계"""
    try:
        upload_dir = './data/uploads'
        total_files = 0
        total_size = 0
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
        
        return jsonify({
            "success": True,
            "stats": {
                "total_documents": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "supported_formats": [".txt", ".pdf", ".docx", ".doc", ".md", ".json", ".csv"],
                "features_available": [
                    "Flashcard Generation",
                    "Quiz Generation", 
                    "Summary Generation",
                    "Text Extraction"
                ]
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 통계 조회 실패: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# 헬퍼 함수들
async def generate_flashcards(openai_service, text_content: str) -> list:
    """플래시카드 생성"""
    try:
        # 텍스트가 너무 길면 요약해서 사용
        if len(text_content) > 4000:
            text_content = text_content[:4000] + "..."
        
        prompt = f"""
다음 텍스트를 바탕으로 학습용 플래시카드 5개를 생성해주세요.
각 플래시카드는 앞면(질문)과 뒷면(답변)으로 구성되어야 합니다.

텍스트:
{text_content}

응답 형식 (JSON):
[
    {{
        "front": "질문",
        "back": "답변"
    }}
]
"""
        
        messages = [
            {"role": "system", "content": "당신은 교육 콘텐츠 생성 전문가입니다. 효과적인 학습 자료를 만들어주세요."},
            {"role": "user", "content": prompt}
        ]
        
        response = await openai_service.generate_chat_response(messages, max_tokens=1000)
        
        # JSON 파싱 시도
        import json
        try:
            # 응답에서 JSON 부분만 추출
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                flashcards = json.loads(json_str)
                return flashcards if isinstance(flashcards, list) else []
        except:
            pass
        
        # JSON 파싱 실패시 기본 플래시카드 반환
        return [
            {"front": "이 문서의 주요 내용은 무엇인가요?", "back": "텍스트 분석을 통해 확인해보세요."},
            {"front": "핵심 개념을 설명해보세요", "back": "문서의 내용을 요약해보세요."}
        ]
        
    except Exception as e:
        logger.error(f"❌ 플래시카드 생성 실패: {str(e)}")
        return [{"front": "오류 발생", "back": f"플래시카드 생성 중 오류: {str(e)}"}]

async def generate_quiz(openai_service, text_content: str) -> dict:
    """퀴즈 생성"""
    try:
        if len(text_content) > 4000:
            text_content = text_content[:4000] + "..."
        
        prompt = f"""
다음 텍스트를 바탕으로 객관식 퀴즈 3문제를 생성해주세요.
각 문제는 4개의 선택지와 정답을 포함해야 합니다.

텍스트:
{text_content}

응답 형식 (JSON):
{{
    "quiz_title": "퀴즈 제목",
    "questions": [
        {{
            "question": "문제",
            "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
            "correct_answer": 0,
            "explanation": "정답 설명"
        }}
    ]
}}
"""
        
        messages = [
            {"role": "system", "content": "당신은 교육 콘텐츠 생성 전문가입니다. 학습 효과가 높은 퀴즈를 만들어주세요."},
            {"role": "user", "content": prompt}
        ]
        
        response = await openai_service.generate_chat_response(messages, max_tokens=1500)
        
        # JSON 파싱 시도
        import json
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                quiz = json.loads(json_str)
                return quiz if isinstance(quiz, dict) else {}
        except:
            pass
        
        # 기본 퀴즈 반환
        return {
            "quiz_title": "기본 퀴즈",
            "questions": [
                {
                    "question": "이 문서의 주요 주제는 무엇인가요?",
                    "options": ["옵션1", "옵션2", "옵션3", "옵션4"],
                    "correct_answer": 0,
                    "explanation": "문서를 자세히 읽어보세요."
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ 퀴즈 생성 실패: {str(e)}")
        return {"quiz_title": "오류", "questions": []}

async def generate_summary(openai_service, text_content: str) -> str:
    """요약 생성"""
    try:
        if len(text_content) > 6000:
            text_content = text_content[:6000] + "..."
        
        prompt = f"""
다음 텍스트를 3-5문장으로 요약해주세요. 핵심 내용과 주요 포인트를 포함해야 합니다.

텍스트:
{text_content}

요약:
"""
        
        messages = [
            {"role": "system", "content": "당신은 문서 요약 전문가입니다. 명확하고 간결한 요약을 제공해주세요."},
            {"role": "user", "content": prompt}
        ]
        
        summary = await openai_service.generate_chat_response(messages, max_tokens=500)
        
        return summary.strip()
        
    except Exception as e:
        logger.error(f"❌ 요약 생성 실패: {str(e)}")
        return f"요약 생성 중 오류가 발생했습니다: {str(e)}"