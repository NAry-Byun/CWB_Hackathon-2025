"""
환경변수 로딩 문제를 해결한 전문적인 스크래퍼
.env 파일을 명시적으로 로드합니다.
"""

import asyncio
import logging
import sys
import os
import requests
from bs4 import BeautifulSoup
import re
import time
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from dataclasses import dataclass, field

# 환경변수 명시적 로딩
def load_env_file():
    """환경변수 파일을 명시적으로 로드"""
    try:
        # 현재 디렉토리와 부모 디렉토리에서 .env 파일 찾기
        possible_paths = [
            '.env',
            '../.env',
            '../../.env',
            os.path.join(os.path.dirname(__file__), '.env'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        ]
        
        env_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                env_file_path = path
                break
        
        if not env_file_path:
            print("⚠️ .env 파일을 찾을 수 없습니다. 수동으로 환경변수를 설정합니다.")
            return False
        
        print(f"📁 .env 파일 발견: {env_file_path}")
        
        # .env 파일 읽기
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    if key and value:
                        os.environ[key] = value
                        print(f"✅ 환경변수 설정: {key}")
        
        return True
        
    except Exception as e:
        print(f"❌ .env 파일 로딩 실패: {e}")
        return False

# .env 파일 로드
print("🔧 환경변수 로딩 시작...")
load_env_file()

# 환경변수 확인
required_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY']
missing_vars = []

for var in required_vars:
    if not os.environ.get(var):
        missing_vars.append(var)
    else:
        print(f"✅ {var}: {'*' * 10}...{os.environ[var][-10:]}")

if missing_vars:
    print(f"❌ 누락된 환경변수: {', '.join(missing_vars)}")
    print("📝 .env 파일에 다음 변수들을 설정하세요:")
    for var in missing_vars:
        print(f"   {var}=your_value_here")

# 이제 서비스들 import (올바른 경로로 수정)
try:
    from services.cosmos_service import CosmosVectorService
    print("✅ services.cosmos_service 성공적으로 import")
except ImportError as e:
    print(f"❌ services.cosmos_service import 실패: {e}")
    print("⚠️ 대안: 간단한 더미 서비스 사용")
    
    class DummyCosmosService:
        async def initialize_database(self):
            print("🤖 더미 Cosmos DB 초기화")
            return True
        
        async def store_document_chunk(self, file_name, chunk_text, embedding, chunk_index, metadata):
            print(f"🤖 더미 문서 청크 저장: {file_name}[{chunk_index}]")
            return f"dummy_doc_id_{chunk_index}"
    
    CosmosVectorService = DummyCosmosService

# OpenAI 서비스
try:
    from services.azure_openai_service import AzureOpenAIService
    openai_service_class = AzureOpenAIService
    print("✅ services.azure_openai_service 발견")
except ImportError:
    try:
        from services.openai_service import OpenAIService
        openai_service_class = OpenAIService
        print("✅ services.openai_service 발견")
    except ImportError:
     print("⚠️ OpenAI 서비스들 없음. 더미 서비스 사용")
    
    class DummyOpenAIService:
        async def generate_embeddings(self, text):
            print(f"🤖 더미 임베딩 생성: {len(text)} 문자")
            import random
            return [random.random() for _ in range(1536)]
        
        async def generate_response(self, *args, **kwargs):
            return {
                "assistant_message": "더미 응답입니다.",
                "content": "더미 응답입니다."
            }
    
    openai_service_class = DummyOpenAIService

@dataclass
class ProfessionalDocument:
    """전문적인 문서 구조"""
    url: str
    title: str
    content: str
    author: Optional[str] = None
    content_type: str = "blog_post"
    word_count: int = 0
    quality_score: float = 0.0
    ai_relevance_score: float = 0.0
    key_concepts: List[str] = field(default_factory=list)
    summary: str = ""

class EnvironmentFixedScraper:
    """환경변수 문제가 해결된 전문적인 스크래퍼"""
    
    def __init__(self, cosmos_service=None, openai_service=None):
        # 서비스가 제공되지 않으면 기본 서비스 생성
        if cosmos_service is None:
            try:
                self.cosmos_service = CosmosVectorService()
            except Exception as e:
                print(f"⚠️ Cosmos 서비스 초기화 실패: {e}")
                self.cosmos_service = DummyCosmosService()
        else:
            self.cosmos_service = cosmos_service
            
        if openai_service is None:
            try:
                self.openai_service = openai_service_class()
            except Exception as e:
                print(f"⚠️ OpenAI 서비스 초기화 실패: {e}")
                self.openai_service = DummyOpenAIService()
        else:
            self.openai_service = openai_service
        
        # HTTP 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
        
        # AI 키워드 (가중치 포함)
        self.ai_keywords = {
            'artificial intelligence': 5.0,
            'machine learning': 4.5,
            'deep learning': 4.0,
            'neural network': 3.5,
            'natural language processing': 3.5,
            'computer vision': 3.0,
            'ai': 3.0,
            'ml': 2.5,
            'nlp': 2.5,
            'algorithm': 2.0,
            'automation': 1.5,
            'cognitive': 2.0,
            'intelligent': 1.5
        }
        
        if hasattr(logging, 'getLogger'):
            logger = logging.getLogger(__name__)
            logger.info("🚀 환경변수 문제가 해결된 전문적인 스크래퍼 초기화 완료")

    async def scrape_and_store_professionally(self, url: str) -> Dict[str, Any]:
        """전문적으로 스크래핑하고 저장"""
        try:
            print(f"🔍 전문적인 스크래핑 시작: {url}")
            
            # 1. 웹 페이지 가져오기
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 2. 전문적인 문서 추출
            document = self.extract_professional_document(soup, url)
            
            # 3. 품질 검증
            if document.quality_score < 30:
                return {
                    'success': False,
                    'url': url,
                    'error': f'품질이 너무 낮음: {document.quality_score}/100',
                    'quality_score': document.quality_score
                }
            
            # 4. 전문적인 청크 생성
            chunks = self.create_professional_chunks(document)
            
            if not chunks:
                return {
                    'success': False,
                    'url': url,
                    'error': '유효한 청크를 생성할 수 없음'
                }
            
            # 5. Cosmos DB에 저장
            storage_result = await self.store_with_rich_metadata(document, chunks)
            
            # 6. 결과 반환
            result = {
                'success': True,
                'url': url,
                'document': {
                    'title': document.title,
                    'author': document.author,
                    'word_count': document.word_count,
                    'quality_score': round(document.quality_score, 1),
                    'ai_relevance_score': round(document.ai_relevance_score, 1),
                    'key_concepts': document.key_concepts,
                    'summary': document.summary[:200] + "..." if len(document.summary) > 200 else document.summary
                },
                'chunks': {
                    'total_created': len(chunks),
                    'stored_successfully': storage_result.get('successful_chunks', 0),
                    'success_rate': storage_result.get('success_rate', 0),
                    'chunk_types': list(set(chunk['chunk_type'] for chunk in chunks))
                },
                'storage': storage_result
            }
            
            print(f"✅ 전문적인 스크래핑 완료: {document.title}")
            print(f"📊 품질: {document.quality_score:.1f}/100, AI 관련성: {document.ai_relevance_score:.1f}/100")
            print(f"📝 저장: {storage_result.get('successful_chunks', 0)}/{len(chunks)} 청크")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP 요청 실패: {e}")
            return {
                'success': False,
                'url': url,
                'error': f'웹 페이지 접근 실패: {str(e)}',
                'error_type': 'network_error'
            }
        except Exception as e:
            print(f"❌ 전문적인 스크래핑 실패: {e}")
            return {
                'success': False,
                'url': url,
                'error': f'처리 실패: {str(e)}',
                'error_type': 'processing_error'
            }

    def extract_professional_document(self, soup: BeautifulSoup, url: str) -> ProfessionalDocument:
        """전문적인 문서 추출"""
        
        # 노이즈 제거
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # 핵심 정보 추출
        title = self.extract_title(soup)
        content = self.extract_clean_content(soup)
        author = self.extract_author(soup)
        
        # 분석
        word_count = len(content.split())
        key_concepts = self.extract_key_concepts(content, title)
        summary = self.generate_summary(content, title)
        quality_score = self.calculate_quality_score(content, title, word_count)
        ai_relevance_score = self.calculate_ai_relevance(content, title)
        
        return ProfessionalDocument(
            url=url,
            title=title,
            content=content,
            author=author,
            word_count=word_count,
            quality_score=quality_score,
            ai_relevance_score=ai_relevance_score,
            key_concepts=key_concepts,
            summary=summary
        )

    def extract_title(self, soup: BeautifulSoup) -> str:
        """제목 추출"""
        # 우선순위별 제목 추출
        strategies = [
            lambda: soup.select_one('article h1, .post-title h1, .entry-title h1'),
            lambda: soup.find('h1'),
            lambda: soup.find('meta', property='og:title'),
            lambda: soup.find('meta', attrs={'name': 'twitter:title'}),
            lambda: soup.title
        ]
        
        for strategy in strategies:
            try:
                element = strategy()
                if element:
                    if element.name == 'meta':
                        title_text = element.get('content', '').strip()
                    else:
                        title_text = element.get_text(strip=True)
                    
                    if title_text and len(title_text) > 5:
                        # 사이트명 제거
                        clean_title = re.sub(r'\s*[\|\-–—]\s*[^|\-–—]*$', '', title_text)
                        return clean_title if clean_title else title_text
            except:
                continue
        
        return "Professional Article"

    def extract_clean_content(self, soup: BeautifulSoup) -> str:
        """깨끗한 콘텐츠 추출"""
        content_selectors = [
            'article .post-content',
            'article .entry-content',
            'article .content',
            'main article',
            '.blog-post-content',
            '.post-body',
            'article',
            'main',
            '[role="main"]',
            '.main-content',
            '#main-content'
        ]
        
        best_content = ""
        best_score = 0
        
        for selector in content_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    content_text = element.get_text(separator='\n\n', strip=True)
                    score = self.score_content_quality(content_text)
                    
                    if score > best_score and len(content_text) > 300:
                        best_score = score
                        best_content = content_text
            except:
                continue
        
        # 폴백
        if not best_content or len(best_content) < 300:
            if soup.body:
                best_content = soup.body.get_text(separator='\n\n', strip=True)
            else:
                best_content = soup.get_text(separator='\n\n', strip=True)
        
        return self.clean_text(best_content)

    def clean_text(self, text: str) -> str:
        """텍스트 정리"""
        # 공백 정규화
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 웹 아티팩트 제거 (AI 응답 품질 향상을 위해)
        patterns = [
            r'(Click here|Read more|Continue reading|Subscribe|Share)',
            r'(Facebook|Twitter|LinkedIn|Instagram)\s*(share|button)?',
            r'(Cookie|Privacy)\s*(Policy|Notice)',
            r'https?://\S+',
            r'www\.\S+',
            r'Sources?:\s*web_\S+',
            r'web_www\.\S+',
            r'\([0-9]+%\)',  # 퍼센트 제거 (핵심!)
            r'Sources?:\s*[^\n]*%[^\n]*'  # 소스 라인 제거 (핵심!)
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 정리
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()

    def extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """저자 추출"""
        selectors = ['.author-name', '.post-author', '.byline', '.author']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True)
                if author and 3 <= len(author) <= 50:
                    return author
        
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            return author_meta.get('content').strip()
        
        return None

    def extract_key_concepts(self, content: str, title: str) -> List[str]:
        """키 컨셉 추출"""
        combined_text = f"{title} {content}".lower()
        found_concepts = []
        
        for concept, weight in self.ai_keywords.items():
            if concept in combined_text:
                found_concepts.append(concept)
        
        # 중요도순 정렬
        concept_scores = [(concept, self.ai_keywords[concept]) for concept in found_concepts]
        concept_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [concept for concept, _ in concept_scores[:10]]

    def generate_summary(self, content: str, title: str) -> str:
        """요약 생성"""
        sentences = re.split(r'[.!?]+', content)
        meaningful_sentences = [s.strip() for s in sentences if 50 <= len(s.strip()) <= 300]
        
        if meaningful_sentences:
            summary = '. '.join(meaningful_sentences[:3])
            if summary and not summary.endswith('.'):
                summary += '.'
            return summary[:400] + ("..." if len(summary) > 400 else "")
        
        return f"This article discusses {title.lower()} and related concepts."

    def score_content_quality(self, content: str) -> float:
        """콘텐츠 품질 점수"""
        if not content:
            return 0.0
        
        score = 0.0
        word_count = len(content.split())
        
        # 길이 점수
        if 500 <= word_count <= 3000:
            score += 10.0
        elif 200 <= word_count < 500:
            score += 8.0
        
        # 구조 점수
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        if paragraph_count >= 5:
            score += 5.0
        
        # AI 관련성
        ai_terms = sum(1 for keyword in self.ai_keywords if keyword in content.lower())
        score += min(ai_terms * 0.5, 5.0)
        
        return score

    def calculate_quality_score(self, content: str, title: str, word_count: int) -> float:
        """품질 점수 계산"""
        score = 0.0
        
        # 단어 수 (40점)
        if 800 <= word_count <= 3000:
            score += 40.0
        elif 400 <= word_count < 800:
            score += 35.0
        elif 200 <= word_count < 400:
            score += 25.0
        elif word_count >= 100:
            score += 15.0
        
        # 구조 (30점)
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 7:
            score += 30.0
        elif len(paragraphs) >= 5:
            score += 25.0
        elif len(paragraphs) >= 3:
            score += 20.0
        
        # 제목 품질 (15점)
        if title and len(title) > 15:
            score += 15.0
        elif title and len(title) > 8:
            score += 10.0
        
        # AI 관련성 (15점)
        ai_terms = sum(1 for keyword in self.ai_keywords if keyword in content.lower())
        score += min(ai_terms * 2, 15.0)
        
        return min(score, 100.0)

    def calculate_ai_relevance(self, content: str, title: str) -> float:
        """AI 관련성 계산"""
        combined_text = f"{title} {title} {content}".lower()  # 제목 가중치
        
        relevance_score = 0.0
        total_weight = 0.0
        
        for keyword, weight in self.ai_keywords.items():
            count = combined_text.count(keyword)
            total_weight += count * weight
        
        word_count = len(combined_text.split())
        if word_count > 0:
            density = (total_weight / word_count) * 1000  # per 1000 words
            relevance_score = min(density * 15, 100.0)
        
        return relevance_score

    def create_professional_chunks(self, document: ProfessionalDocument) -> List[Dict[str, Any]]:
        """전문적인 청크 생성"""
        chunks = []
        
        # 1. 소개 청크 (제목 + 요약 + 주요 개념)
        intro_parts = [
            f"Document: {document.title}",
            f"Summary: {document.summary}",
            f"Key AI concepts: {', '.join(document.key_concepts[:5])}"
        ]
        
        paragraphs = [p.strip() for p in document.content.split('\n\n') if p.strip()]
        if paragraphs:
            intro_parts.append(f"Content: {paragraphs[0]}")
        
        intro_text = '\n\n'.join(intro_parts)
        
        chunks.append({
            'text': intro_text,
            'chunk_type': 'comprehensive_introduction',
            'importance_level': 'high',
            'concepts': document.key_concepts[:3],
            'metadata': {
                'chunk_purpose': 'comprehensive_introduction',
                'contains_title': True,
                'contains_summary': True,
                'contains_key_concepts': True
            }
        })
        
        # 2. 콘텐츠 청크들 (의미적 분할)
        remaining_content = '\n\n'.join(paragraphs[1:]) if len(paragraphs) > 1 else ""
        
        if remaining_content and len(remaining_content) > 300:
            chunk_size = 1200
            sentences = re.split(r'[.!?]+\s+', remaining_content)
            
            current_chunk = ""
            chunk_index = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                test_chunk = current_chunk + " " + sentence if current_chunk else sentence
                
                if len(test_chunk) <= chunk_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk and len(current_chunk) > 300:
                        chunk_text = f"Section {chunk_index + 1} of {document.title}:\n\n{current_chunk.strip()}"
                        
                        chunks.append({
                            'text': chunk_text,
                            'chunk_type': 'content_section',
                            'importance_level': 'medium',
                            'concepts': self.extract_chunk_concepts(current_chunk, document.key_concepts),
                            'metadata': {
                                'chunk_purpose': 'semantic_content_section',
                                'section_number': chunk_index + 1,
                                'document_title': document.title
                            }
                        })
                        chunk_index += 1
                    
                    # 오버랩을 위한 마지막 문장들 유지
                    last_sentences = current_chunk.split('.')[-2:] if current_chunk else []
                    overlap_text = '. '.join(s.strip() for s in last_sentences if s.strip())
                    current_chunk = overlap_text + ". " + sentence if overlap_text else sentence
            
            # 마지막 청크
            if current_chunk and len(current_chunk) > 300:
                chunk_text = f"Final section of {document.title}:\n\n{current_chunk.strip()}"
                
                chunks.append({
                    'text': chunk_text,
                    'chunk_type': 'content_section',
                    'importance_level': 'medium',
                    'concepts': self.extract_chunk_concepts(current_chunk, document.key_concepts),
                    'metadata': {
                        'chunk_purpose': 'semantic_content_section',
                        'section_number': chunk_index + 1,
                        'is_final_section': True
                    }
                })
        
        # 3. 종합 요약 청크 (긴 문서의 경우)
        if document.word_count > 1000:
            summary_parts = [
                f"Complete Summary of {document.title}",
                f"Overview: {document.summary}",
                f"Main AI concepts covered: {', '.join(document.key_concepts[:8])}",
                f"Document statistics: {document.word_count} words"
            ]
            
            summary_text = '\n\n'.join(summary_parts)
            
            chunks.append({
                'text': summary_text,
                'chunk_type': 'comprehensive_summary',
                'importance_level': 'high',
                'concepts': document.key_concepts,
                'metadata': {
                    'chunk_purpose': 'comprehensive_summary',
                    'document_overview': True
                }
            })
        
        return chunks

    def extract_chunk_concepts(self, chunk_text: str, document_concepts: List[str]) -> List[str]:
        """청크별 개념 추출"""
        chunk_lower = chunk_text.lower()
        present_concepts = []
        
        for concept in document_concepts:
            if concept.lower() in chunk_lower:
                present_concepts.append(concept)
        
        return present_concepts

    async def store_with_rich_metadata(self, document: ProfessionalDocument, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """풍부한 메타데이터와 함께 저장"""
        try:
            await self.cosmos_service.initialize_database()
            
            successful_chunks = []
            failed_chunks = []
            filename = self.generate_filename(document)
            
            for i, chunk in enumerate(chunks):
                try:
                    # 임베딩 생성
                    embedding = await self.openai_service.generate_embeddings(chunk['text'])
                    
                    if not embedding:
                        failed_chunks.append({'index': i, 'error': 'Embedding generation failed'})
                        continue
                    
                    # 전문적인 메타데이터 생성
                    professional_metadata = {
                        # 문서 정보
                        'source_url': document.url,
                        'document_title': document.title,
                        'document_type': 'environment_fixed_professional_blog',
                        'content_type': document.content_type,
                        'language': 'english',
                        
                        # 품질 정보
                        'quality_level': self.get_quality_level(document.quality_score),
                        'document_quality_score': round(document.quality_score, 1),
                        'ai_relevance_level': self.get_ai_relevance_level(document.ai_relevance_score),
                        'document_ai_relevance_score': round(document.ai_relevance_score, 1),
                        
                        # 청크 정보
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'chunk_type': chunk['chunk_type'],
                        'importance_level': chunk['importance_level'],
                        'semantic_context': f"Chunk {i+1} of {len(chunks)} from {document.title}",
                        'chunk_word_count': len(chunk['text'].split()),
                        'chunk_concepts': chunk['concepts'],
                        
                        # 문서 메트릭
                        'document_word_count': document.word_count,
                        'document_summary': document.summary[:100] if document.summary else None,
                        'key_concepts': document.key_concepts,
                        'author': document.author,
                        
                        # 처리 정보
                        'extraction_method': 'environment_fixed_professional_scraper',
                        'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                        'optimized_for_professional_responses': True,
                        'noise_patterns_removed': True,
                        'semantically_chunked': True,
                        'context_preservation_enabled': True,
                        
                        # 검색 최적화
                        'searchable_title': document.title.lower(),
                        'searchable_concepts': [concept.lower() for concept in document.key_concepts],
                        'domain': urlparse(document.url).netloc,
                        
                        # AI 응답 힌트
                        'ai_response_hints': {
                            'is_primary_content': chunk['importance_level'] == 'high',
                            'contains_introduction': 'introduction' in chunk['chunk_type'],
                            'contains_summary': 'summary' in chunk['chunk_type'],
                            'has_title_context': chunk['metadata'].get('contains_title', False)
                        },
                        
                        # 청크별 메타데이터
                        **chunk['metadata']
                    }
                    
                    # Cosmos DB에 저장
                    doc_id = await self.cosmos_service.store_document_chunk(
                        file_name=filename,
                        chunk_text=chunk['text'],
                        embedding=embedding,
                        chunk_index=i,
                        metadata=professional_metadata
                    )
                    
                    successful_chunks.append(doc_id)
                    print(f"✅ 전문적인 메타데이터로 청크 {i+1}/{len(chunks)} 저장 완료")
                    
                except Exception as e:
                    print(f"❌ 청크 {i+1} 저장 실패: {e}")
                    failed_chunks.append({'index': i, 'error': str(e)})
            
            success_rate = (len(successful_chunks) / len(chunks) * 100) if chunks else 0
            
            return {
                'successful_chunks': len(successful_chunks),
                'failed_chunks': len(failed_chunks),
                'total_chunks': len(chunks),
                'success_rate': round(success_rate, 1),
                'document_ids': successful_chunks,
                'failed_chunk_details': failed_chunks,
                'filename': filename,
                'metadata_quality': 'professional_grade'
            }
            
        except Exception as e:
            print(f"❌ 전문적인 메타데이터 저장 실패: {e}")
            return {
                'successful_chunks': 0,
                'failed_chunks': len(chunks),
                'success_rate': 0.0,
                'error': str(e)
            }

    def generate_filename(self, document: ProfessionalDocument) -> str:
        """전문적인 파일명 생성"""
        try:
            domain = urlparse(document.url).netloc.replace('www.', '')
            title_clean = re.sub(r'[^\w\s-]', '', document.title)
            title_clean = re.sub(r'\s+', '_', title_clean).lower()
            
            quality_suffix = self.get_quality_level(document.quality_score)
            
            if title_clean and len(title_clean) > 8:
                filename = f"professional_{domain}_{title_clean}_{quality_suffix}"
            else:
                path_clean = re.sub(r'[^\w-]', '_', urlparse(document.url).path)
                filename = f"professional_{domain}_{path_clean}_{quality_suffix}"
            
            # 길이 제한
            filename = filename[:120]
            filename = re.sub(r'_{2,}', '_', filename)
            filename = filename.strip('_')
            
            return filename
            
        except Exception:
            url_hash = hashlib.md5(document.url.encode()).hexdigest()[:12]
            return f"professional_content_{url_hash}"

    def get_quality_level(self, score: float) -> str:
        """품질 점수를 레벨로 변환"""
        if score >= 80:
            return 'excellent'
        elif score >= 65:
            return 'very_good'
        elif score >= 50:
            return 'good'
        elif score >= 35:
            return 'acceptable'
        else:
            return 'needs_improvement'

    def get_ai_relevance_level(self, score: float) -> str:
        """AI 관련성을 레벨로 변환"""
        if score >= 70:
            return 'highly_relevant'
        elif score >= 50:
            return 'relevant'
        elif score >= 30:
            return 'moderately_relevant'
        elif score >= 15:
            return 'somewhat_relevant'
        else:
            return 'low_relevance'

    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 확인"""
        try:
            health_info = {
                'service_name': 'EnvironmentFixedScraper',
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'environment_variables': {},
                'services': {},
                'scraper_config': {}
            }
            
            # 환경변수 상태 확인
            env_vars = ['COSMOS_DB_ENDPOINT', 'COSMOS_DB_KEY']
            for var in env_vars:
                value = os.environ.get(var)
                if value:
                    health_info['environment_variables'][var] = f"{'*' * 5}...{value[-5:]}"
                else:
                    health_info['environment_variables'][var] = 'NOT_SET'
            
            # 네트워크 테스트
            try:
                test_response = self.session.get('https://httpbin.org/status/200', timeout=10)
                health_info['services']['network'] = {
                    'status': 'healthy' if test_response.status_code == 200 else 'unhealthy',
                    'response_time_ms': round(test_response.elapsed.total_seconds() * 1000, 2)
                }
            except Exception as e:
                health_info['services']['network'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_info['status'] = 'degraded'
            
            # 서비스 상태
            health_info['services']['cosmos_service'] = {
                'status': 'connected' if self.cosmos_service else 'not_connected',
                'service_type': type(self.cosmos_service).__name__ if self.cosmos_service else 'None'
            }
            
            health_info['services']['openai_service'] = {
                'status': 'connected' if self.openai_service else 'not_connected',
                'service_type': type(self.openai_service).__name__ if self.openai_service else 'None'
            }
            
            # 스크래퍼 설정
            health_info['scraper_config'] = {
                'ai_keywords_loaded': len(self.ai_keywords),
                'user_agent': self.session.headers.get('User-Agent')[:50] + "..."
            }
            
            return health_info
            
        except Exception as e:
            return {
                'service_name': 'EnvironmentFixedScraper',
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

# Simple scraper fallback for basic functionality
class SimpleWebScraper:
    """간단한 웹 스크래퍼 (fallback용)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.ai_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'ai', 'ml', 'algorithm'
        ]

    def scrape_url(self, url: str) -> dict:
        """URL을 스크래핑하고 결과 반환"""
        try:
            print(f"🔍 간단한 스크래핑 시작: {url}")
            
            # HTTP 요청
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 기본 정보 추출
            title = self.extract_title(soup)
            content = self.extract_content(soup)
            
            # 분석
            word_count = len(content.split())
            ai_related = self.is_ai_related(content, title)
            quality_score = self.calculate_quality(content, title, word_count)
            
            result = {
                'success': True,
                'url': url,
                'title': title,
                'content': content[:1000] + "..." if len(content) > 1000 else content,
                'word_count': word_count,
                'ai_related': ai_related,
                'quality_score': quality_score,
                'scraped_at': datetime.now().isoformat()
            }
            
            print(f"✅ 간단한 스크래핑 완료: {title}")
            return result
            
        except Exception as e:
            print(f"❌ 간단한 스크래핑 실패: {e}")
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }

    def extract_title(self, soup):
        """제목 추출"""
        # H1 태그 시도
        h1 = soup.find('h1')
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)
        
        # Title 태그 시도
        if soup.title:
            return soup.title.get_text(strip=True)
        
        return "Untitled"

    def extract_content(self, soup):
        """콘텐츠 추출"""
        # 노이즈 제거
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # 본문 추출
        article = soup.find('article')
        if article:
            content = article.get_text(separator=' ', strip=True)
        elif soup.body:
            content = soup.body.get_text(separator=' ', strip=True)
        else:
            content = soup.get_text(separator=' ', strip=True)
        
        # 텍스트 정리
        content = re.sub(r'\s+', ' ', content)
        return content.strip()

    def is_ai_related(self, content, title):
        """AI 관련 여부 확인"""
        text = f"{title} {content}".lower()
        return any(keyword in text for keyword in self.ai_keywords)

    def calculate_quality(self, content, title, word_count):
        """품질 점수 계산"""
        score = 0
        
        if word_count >= 200:
            score += 30
        if word_count >= 500:
            score += 20
        if title and len(title) > 10:
            score += 25
        if self.is_ai_related(content, title):
            score += 25
        
        return min(score, 100)


# Factory function to get the appropriate scraper
def get_scraper(use_professional=True):
    """적절한 스크래퍼를 반환하는 팩토리 함수"""
    if use_professional:
        try:
            return EnvironmentFixedScraper()
        except Exception as e:
            print(f"⚠️ 전문 스크래퍼 초기화 실패, 간단한 스크래퍼 사용: {e}")
            return SimpleWebScraper()
    else:
        return SimpleWebScraper()


# Test functions
async def run_environment_fixed_scraping():
    """환경변수 문제가 해결된 스크래핑 실행"""
    print("🚀 환경변수 문제 해결된 전문적인 블로그 스크래핑")
    print("=" * 70)
    
    try:
        # 스크래퍼 생성
        scraper = get_scraper(use_professional=True)
        
        if isinstance(scraper, EnvironmentFixedScraper):
            print("✅ 전문적인 스크래퍼 초기화 성공")
            
            # 상태 확인
            print("\n🏥 서비스 상태 확인...")
            health = await scraper.health_check()
            print(f"서비스 상태: {health['status']}")
            
            # 환경변수 확인 출력
            env_status = health.get('environment_variables', {})
            for var, status in env_status.items():
                if status == 'NOT_SET':
                    print(f"   ❌ {var}: {status}")
                else:
                    print(f"   ✅ {var}: {status}")
            
            # 네트워크 상태
            network_status = health.get('services', {}).get('network', {})
            print(f"   🌐 네트워크: {network_status.get('status', 'unknown')}")
            
            if health['status'] == 'unhealthy':
                print("❌ 서비스 상태가 불량합니다. 간단한 스크래퍼로 대체합니다.")
                scraper = SimpleWebScraper()
        
        # URL 테스트
        test_url = "https://www.artificial-intelligence.blog/terminology/artificial-intelligence"
        
        print(f"\n📄 처리할 URL: {test_url}")
        print("🔄 스크래핑 실행 중...")
        
        # 스크래핑 실행
        if isinstance(scraper, EnvironmentFixedScraper):
            result = await scraper.scrape_and_store_professionally(test_url)
        else:
            result = scraper.scrape_url(test_url)
        
        if result['success']:
            print(f"\n🎉 성공적으로 처리 완료!")
            print("=" * 50)
            
            if isinstance(scraper, EnvironmentFixedScraper):
                # 전문적인 결과 출력
                doc = result['document']
                print(f"📋 문서 정보:")
                print(f"   제목: {doc['title']}")
                print(f"   저자: {doc.get('author', 'Unknown')}")
                print(f"   단어 수: {doc['word_count']}")
                print(f"   품질 점수: {doc['quality_score']}/100")
                print(f"   AI 관련성: {doc['ai_relevance_score']}/100")
                
                if doc['key_concepts']:
                    print(f"   주요 AI 개념:")
                    for i, concept in enumerate(doc['key_concepts'][:5], 1):
                        print(f"      {i}. {concept}")
                
                if doc['summary']:
                    print(f"   요약: {doc['summary']}")
                
                # 청킹 분석
                chunks = result['chunks']
                print(f"\n📦 청킹 분석:")
                print(f"   총 생성된 청크: {chunks['total_created']}")
                print(f"   성공적으로 저장: {chunks['stored_successfully']}")
                print(f"   저장 성공률: {chunks['success_rate']}%")
                print(f"   청크 타입들: {', '.join(chunks['chunk_types'])}")
            else:
                # 간단한 결과 출력
                print(f"📋 문서 정보:")
                print(f"   제목: {result['title']}")
                print(f"   단어 수: {result['word_count']}")
                print(f"   품질 점수: {result['quality_score']}/100")
                print(f"   AI 관련: {result['ai_related']}")
                print(f"   내용 미리보기: {result['content'][:200]}...")
            
        else:
            print(f"\n❌ 처리 실패:")
            print(f"   오류: {result['error']}")
            print(f"   오류 타입: {result.get('error_type', 'unknown')}")
    
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔧 환경변수 문제 해결된 전문적인 블로그 스크래퍼")
    print("Cosmos DB 연결 문제를 해결하고 최고 품질의 메타데이터를 생성합니다.")
    print("=" * 80)
    
    try:
        # 전체 실행
        asyncio.run(run_environment_fixed_scraping())
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 실행 실패: {e}")