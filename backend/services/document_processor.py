# services/document_processor.py - 문서 처리 서비스

import os
import io
import logging
from typing import Dict, Any, Optional, List
import asyncio

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """문서 처리 서비스 - 다양한 파일 형식에서 텍스트 추출"""
    
    def __init__(self):
        """문서 처리기 초기화"""
        self.supported_formats = {
            '.txt': self._extract_text_from_txt,
            '.md': self._extract_text_from_txt,
            '.pdf': self._extract_text_from_pdf,
            '.docx': self._extract_text_from_docx,
            '.doc': self._extract_text_from_doc,
            '.json': self._extract_text_from_json,
            '.csv': self._extract_text_from_csv
        }
        
        logger.info(f"✅ 문서 처리기 초기화 완료")
        logger.info(f"🔧 지원 형식: {list(self.supported_formats.keys())}")
    
    def validate_file_format(self, filename: str) -> bool:
        """파일 형식이 지원되는지 확인"""
        _, ext = os.path.splitext(filename.lower())
        return ext in self.supported_formats
    
    async def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """파일에서 텍스트 추출"""
        try:
            _, ext = os.path.splitext(filename.lower())
            
            if ext not in self.supported_formats:
                raise ValueError(f"지원되지 않는 파일 형식: {ext}")
            
            # 비동기적으로 텍스트 추출
            loop = asyncio.get_event_loop()
            text_content = await loop.run_in_executor(
                None,
                self.supported_formats[ext],
                file_content
            )
            
            logger.info(f"✅ 텍스트 추출 완료: {filename} ({len(text_content)} chars)")
            return text_content
            
        except Exception as e:
            logger.error(f"❌ 텍스트 추출 실패 {filename}: {str(e)}")
            return f"텍스트 추출 실패: {str(e)}"
    
    def _extract_text_from_txt(self, file_content: bytes) -> str:
        """TXT/MD 파일에서 텍스트 추출"""
        try:
            # UTF-8로 디코딩 시도
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                # UTF-8 실패시 다른 인코딩 시도
                encodings = ['cp949', 'euc-kr', 'latin-1']
                for encoding in encodings:
                    try:
                        return file_content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 모든 인코딩 실패시 오류 무시하고 디코딩
                return file_content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"❌ TXT 파일 처리 실패: {str(e)}")
            return ""
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """PDF 파일에서 텍스트 추출"""
        try:
            # PyPDF2 사용
            try:
                import PyPDF2
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
            except ImportError:
                logger.warning("PyPDF2가 설치되지 않음. pdfplumber 시도...")
                
                # pdfplumber 사용
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                        text = ""
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        return text.strip()
                        
                except ImportError:
                    logger.error("PDF 처리 라이브러리가 설치되지 않음 (PyPDF2, pdfplumber)")
                    return "PDF 처리를 위해 PyPDF2 또는 pdfplumber를 설치해주세요."
                    
        except Exception as e:
            logger.error(f"❌ PDF 파일 처리 실패: {str(e)}")
            return f"PDF 처리 실패: {str(e)}"
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """DOCX 파일에서 텍스트 추출"""
        try:
            import docx
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except ImportError:
            logger.error("python-docx가 설치되지 않음")
            return "DOCX 처리를 위해 python-docx를 설치해주세요."
        except Exception as e:
            logger.error(f"❌ DOCX 파일 처리 실패: {str(e)}")
            return f"DOCX 처리 실패: {str(e)}"
    
    def _extract_text_from_doc(self, file_content: bytes) -> str:
        """DOC 파일에서 텍스트 추출 (제한적 지원)"""
        try:
            # python-docx2txt 사용 시도
            try:
                import docx2txt
                text = docx2txt.process(io.BytesIO(file_content))
                return text if text else "DOC 파일에서 텍스트를 추출할 수 없습니다."
            except ImportError:
                logger.warning("docx2txt가 설치되지 않음")
                return "DOC 파일 처리를 위해 docx2txt를 설치해주세요."
                
        except Exception as e:
            logger.error(f"❌ DOC 파일 처리 실패: {str(e)}")
            return f"DOC 처리 실패: {str(e)}"
    
    def _extract_text_from_json(self, file_content: bytes) -> str:
        """JSON 파일에서 텍스트 추출"""
        try:
            import json
            data = json.loads(file_content.decode('utf-8'))
            
            # JSON을 문자열로 변환 (예쁘게 포맷팅)
            return json.dumps(data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ JSON 파일 처리 실패: {str(e)}")
            return f"JSON 처리 실패: {str(e)}"
    
    def _extract_text_from_csv(self, file_content: bytes) -> str:
        """CSV 파일에서 텍스트 추출"""
        try:
            import csv
            import io
            
            # CSV 내용을 문자열로 변환
            csv_text = file_content.decode('utf-8')
            csv_file = io.StringIO(csv_text)
            
            # CSV 읽기
            reader = csv.reader(csv_file)
            text_lines = []
            
            for row in reader:
                text_lines.append(", ".join(row))
            
            return "\n".join(text_lines)
            
        except Exception as e:
            logger.error(f"❌ CSV 파일 처리 실패: {str(e)}")
            return f"CSV 처리 실패: {str(e)}"
    
    async def health_check(self) -> Dict[str, Any]:
        """문서 처리기 상태 확인"""
        try:
            # 설치된 라이브러리 확인
            libraries = {}
            
            try:
                import PyPDF2
                libraries['PyPDF2'] = True
            except ImportError:
                libraries['PyPDF2'] = False
                
            try:
                import pdfplumber
                libraries['pdfplumber'] = True
            except ImportError:
                libraries['pdfplumber'] = False
                
            try:
                import docx
                libraries['python-docx'] = True
            except ImportError:
                libraries['python-docx'] = False
                
            try:
                import docx2txt
                libraries['docx2txt'] = True
            except ImportError:
                libraries['docx2txt'] = False
            
            return {
                "status": "healthy",
                "service": "document_processor",
                "supported_formats": list(self.supported_formats.keys()),
                "installed_libraries": libraries,
                "pdf_support": libraries.get('PyPDF2', False) or libraries.get('pdfplumber', False),
                "docx_support": libraries.get('python-docx', False),
                "doc_support": libraries.get('docx2txt', False)
            }
            
        except Exception as e:
            logger.error(f"❌ 문서 처리기 상태 확인 실패: {str(e)}")
            return {
                "status": "unhealthy",
                "service": "document_processor",
                "error": str(e)
            }