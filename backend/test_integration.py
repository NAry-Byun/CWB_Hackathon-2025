# test_function.py 파일 생성
import re

def clean_response_formatting(response_text: str) -> str:
    """Clean up AI response formatting for better readability"""
    if not response_text:
        return ""
    
    # Start with the original response text
    cleaned = response_text
    
    # Remove all markdown headers (##, ###, ####)
    cleaned = re.sub(r'#{1,6}\s*', '', cleaned)
    
    # Remove all bold/italic markers (**text**, *text*)
    cleaned = re.sub(r'\*{1,3}([^*]+?)\*{1,3}', r'\1', cleaned)
    
    # Convert bullet points to simple dashes
    cleaned = re.sub(r'^\s*[•*-]\s+', '- ', cleaned, flags=re.MULTILINE)
    
    # Remove excessive line breaks
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Clean up extra spaces
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n\s+', '\n', cleaned)
    
    # Remove any remaining special characters
    cleaned = re.sub(r'[{}[\]|\\~`]', '', cleaned)
    
    return cleaned.strip()

# 테스트
test_text = "**bold text** ##header text"
result = clean_response_formatting(test_text)
print(f'✅ 함수 테스트 성공: "{result}"')
print("예상 결과: 'bold text header text'")