# services/document_processor.py - SIMPLE FIX VERSION

import logging
import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Document processing service for extracting text from various file formats"""
    
    def __init__(self):
        """Initialize document processor"""
        # FIXED: Include periods in extensions
        self.supported_extensions = {'.txt', '.md', '.docx', '.doc', '.rtf', '.pdf'}
        logger.info("✅ DocumentProcessor initialized with extensions: %s", self.supported_extensions)
    
    def validate_file_format(self, filename: str) -> bool:
        """Check if file format is supported"""
        extension = self._get_file_extension(filename)
        is_supported = extension in self.supported_extensions
        logger.info(f"📋 File validation: {filename} -> extension: '{extension}' -> supported: {is_supported}")
        return is_supported
    
    def _get_file_extension(self, filename: str) -> str:
        """Get lowercase file extension WITH period"""
        if '.' not in filename:
            return ''
        # Get extension including the period
        extension = '.' + filename.lower().split('.')[-1]
        logger.debug(f"🔍 Extension detection: {filename} -> {extension}")
        return extension
    
    async def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text content from file based on its format"""
        try:
            extension = self._get_file_extension(filename)
            
            logger.info(f"📄 Extracting text from {filename} (type: {extension})")
            
            if extension in ['.txt', '.md']:
                text = self._extract_from_text(file_content)
            elif extension == '.docx':
                text = self._extract_from_docx(file_content)
            elif extension == '.doc':
                text = self._extract_from_doc(file_content)
            elif extension == '.rtf':
                text = self._extract_from_rtf(file_content)
            elif extension == '.pdf':
                text = self._extract_from_pdf(file_content)
            else:
                logger.warning(f"⚠️ Unsupported file type: {extension}")
                return f"Unsupported file type: {filename}"
            
            # Clean and validate text
            clean_text = self._clean_text(text)
            
            if len(clean_text.strip()) < 10:
                logger.warning(f"⚠️ Very little text extracted from {filename}: {len(clean_text)} chars")
                return f"Minimal content extracted from {filename}. File may be empty or corrupted."
            
            logger.info(f"✅ Text extraction successful: {len(clean_text)} characters from {filename}")
            return clean_text
            
        except Exception as e:
            logger.error(f"❌ Text extraction failed for {filename}: {str(e)}")
            return f"Error extracting text from {filename}: {str(e)}"
    
    def _extract_from_text(self, file_content: bytes) -> str:
        """Extract text from plain text files"""
        try:
            for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    return file_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return file_content.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX files"""
        try:
            with zipfile.ZipFile(io.BytesIO(file_content), 'r') as docx_zip:
                document_xml = docx_zip.read('word/document.xml')
                root = ET.fromstring(document_xml)
                
                text_elements = []
                for elem in root.iter():
                    if elem.tag.endswith('}t') and elem.text:
                        text_elements.append(elem.text)
                
                full_text = ' '.join(text_elements)
                return full_text if full_text.strip() else "No readable text found in DOCX file"
                
        except Exception as e:
            logger.error(f"❌ DOCX extraction failed: {str(e)}")
            return f"Error reading DOCX file: {str(e)}"
    
    def _extract_from_doc(self, file_content: bytes) -> str:
        """Extract text from DOC files (simplified approach)"""
        try:
            text = file_content.decode('latin-1', errors='ignore')
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', text)
            words = re.findall(r'[a-zA-Z0-9\s\.,!?;:\-()]{3,}', text)
            
            if not words:
                return "No readable text found in DOC file"
            
            extracted_text = ' '.join(words)
            extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
            
            return extracted_text if len(extracted_text) >= 50 else f"Limited text extracted from DOC file: {extracted_text}"
            
        except Exception as e:
            logger.error(f"❌ DOC extraction failed: {str(e)}")
            return f"Error reading DOC file: {str(e)}"
    
    def _extract_from_rtf(self, file_content: bytes) -> str:
        """Extract text from RTF files"""
        try:
            rtf_content = file_content.decode('latin-1', errors='ignore')
            
            # Remove RTF control codes
            text = re.sub(r'\\[a-z]+\d*\s?', '', rtf_content)
            text = re.sub(r'[{}]', '', text)
            text = re.sub(r'\\\S', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text if len(text) >= 20 else "No readable text found in RTF file"
            
        except Exception as e:
            logger.error(f"❌ RTF extraction failed: {str(e)}")
            return f"Error reading RTF file: {str(e)}"
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF files (basic implementation)"""
        try:
            pdf_text = file_content.decode('latin-1', errors='ignore')
            text_matches = re.findall(r'\((.*?)\)', pdf_text)
            
            if text_matches:
                extracted_text = ' '.join(text_matches)
                extracted_text = re.sub(r'[^\w\s\.,!?;:\-()]', '', extracted_text)
                return extracted_text.strip()
            
            return "PDF text extraction requires additional libraries (PyPDF2 or pdfplumber)"
            
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        return text.strip()