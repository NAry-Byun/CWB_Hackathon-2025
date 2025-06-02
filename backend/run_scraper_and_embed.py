import asyncio
import logging
import time
import re
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Cosmos DB 및 Azure OpenAI 서비스 임포트
from services.cosmos_service import CosmosVectorService
from services.azure_openai_service import AzureOpenAIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


class WebScraperService:
    """웹 페이지를 스크래핑하고, 임베딩 생성 및 Cosmos DB 저장 기능을 제공하는 서비스"""
    def __init__(self, cosmos_service=None, openai_service=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0'
        })
        self.cosmos_service = cosmos_service
        self.openai_service = openai_service
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.ai_keywords = [
            'artificial intelligence', 'ai', 'machine learning',
            'deep learning', 'neural network', 'nlp', 'openai'
        ]
        logger.info("🕷️ WebScraperService 초기화됨")

    async def scrape_and_save_url(self, url: str) -> dict:
        """단일 URL 스크래핑 후 Cosmos DB에 청크 정보와 임베딩으로 저장"""
        try:
            logger.info(f"🔍 스크래핑 시작: {url}")
            scrape_res = await self.scrape_url(url)
            if not scrape_res.get('success'):
                return scrape_res

            if not self.cosmos_service or not self.openai_service:
                return {'success': False, 'error': 'Cosmos DB 또는 Azure OpenAI 서비스 미연결'}

            save_res = await self._save_to_cosmos(scrape_res)
            scrape_res.update(save_res)
            return scrape_res

        except Exception as e:
            logger.error(f"❌ scrape_and_save_url 오류: {e}")
            return {'success': False, 'error': str(e)}

    async def scrape_multiple_and_save(self, urls: list) -> dict:
        """여러 URL을 스크래핑 → 청크 분할 → Cosmos DB 저장"""
        results = {
            'total_urls': len(urls),
            'successful_scrapes': 0,
            'successful_saves': 0,
            'failed_urls': [],
            'processed_documents': []
        }
        for i, url in enumerate(urls):
            try:
                logger.info(f"📄 ({i+1}/{len(urls)}) 처리: {url}")
                res = await self.scrape_and_save_url(url)

                if res.get('success'):
                    results['successful_scrapes'] += 1
                    if res.get('cosmos_saved'):
                        results['successful_saves'] += 1
                        results['processed_documents'].append({
                            'url': url,
                            'title': res.get('title'),
                            'chunks_saved': res.get('chunks_saved', 0)
                        })
                    else:
                        results['failed_urls'].append({'url': url, 'error': res.get('error')})
                else:
                    results['failed_urls'].append({'url': url, 'error': res.get('error')})

                # 다음 요청 전 대기 (서버 부하 방지)
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ URL 처리 실패: {url} | 오류: {e}")
                results['failed_urls'].append({'url': url, 'error': str(e)})

        logger.info(f"🎉 스크래핑 완료: 저장 성공 {results['successful_saves']}/{results['total_urls']}")
        return results

    async def _save_to_cosmos(self, scrape_data: dict) -> dict:
        """스크랩된 콘텐츠를 청크로 나눠 임베딩 생성 후 Cosmos DB 저장"""
        try:
            await self.cosmos_service.initialize_database()
            content = scrape_data.get('content', '')
            title = scrape_data.get('title', '제목 없음')
            url = scrape_data.get('url')

            if not content:
                return {'cosmos_saved': False, 'error': '저장할 콘텐츠가 없습니다'}

            chunks = self._split_content_into_chunks(content)
            saved_ids = []
            for idx, chunk in enumerate(chunks):
                # 제목을 포함하여 청크 텍스트 구성
                chunk_with_header = f"{title}\n{chunk}"
                emb = await self.openai_service.generate_embeddings(chunk_with_header)
                if not emb:
                    logger.error(f"❌ 청크 {idx+1} 임베딩 생성 실패")
                    continue

                metadata = {
                    'source_url': url,
                    'source_title': title,
                    'scraped_at': scrape_data.get('scraped_at'),
                    'is_ai_related': scrape_data.get('is_ai_related', False),
                    'content_type': 'web_scraped',
                    'total_chunks': len(chunks)
                }
                doc_id = await self.cosmos_service.store_document_chunk(
                    file_name=f"web_{self._url_to_filename(url)}",
                    chunk_text=chunk_with_header,
                    embedding=emb,
                    chunk_index=idx,
                    metadata=metadata
                )
                saved_ids.append(doc_id)
                logger.info(f"✅ 청크 {idx+1}/{len(chunks)} 저장 완료")

            return {'cosmos_saved': True, 'chunks_saved': len(saved_ids), 'total_chunks': len(chunks), 'document_ids': saved_ids}
        except Exception as e:
            logger.error(f"❌ Cosmos 저장 실패: {e}")
            return {'cosmos_saved': False, 'error': str(e)}

    def _split_content_into_chunks(self, content: str) -> list:
        """긴 텍스트를 지정된 크기로 분할"""
        sentences = re.split(r'[.!?]\s+', content)
        chunks, current = [], ''
        for sentence in sentences:
            candidate = (current + ' ' + sentence).strip() if current else sentence
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence
        if current:
            chunks.append(current)

        final_chunks = []
        for ch in chunks:
            if len(ch) < 100 and final_chunks:
                final_chunks[-1] += ' ' + ch
            else:
                final_chunks.append(ch)
        return final_chunks

    def _url_to_filename(self, url: str) -> str:
        parsed = urlparse(url)
        fname = parsed.netloc + parsed.path
        fname = re.sub(r'[^\w\-_.]', '_', fname)
        fname = re.sub(r'_{2,}', '_', fname)
        return fname[:100]

    async def scrape_url(self, url: str) -> dict:
        """실제 페이지 요청 후 본문 텍스트를 추출"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = self._extract_title(soup)
            content = self._extract_content(soup)
            is_ai_related = self._is_ai_related(title + ' ' + content)
            return {'success': True, 'url': url, 'title': title, 'content': content, 'is_ai_related': is_ai_related, 'scraped_at': datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"❌ URL 스크래핑 실패: {url} | 오류: {e}")
            return {'success': False, 'url': url, 'error': str(e)}

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """h1, title, og:title 순서로 제목 추출"""
        try:
            h1 = soup.find('h1')
            if h1:
                return h1.get_text(strip=True)
            if soup.title:
                return soup.title.get_text(strip=True)
            og = soup.find('meta', property='og:title')
            if og:
                return og.get('content', '')
            return '제목 없음'
        except Exception as e:
            logger.error(f"제목 추출 오류: {e}")
            return '제목 없음'

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """본문 영역을 추출하고 불필요한 태그 제거"""
        try:
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            selectors = ['main', 'article', '.content', '.post-content', '.entry-content', '#content']
            text = ''
            for sel in selectors:
                elem = soup.select_one(sel)
                if elem:
                    text = elem.get_text(separator=' ', strip=True)
                    break
            if not text and soup.body:
                text = soup.body.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) < 100:
                text = re.sub(r'\s+', ' ', soup.get_text(separator=' ', strip=True))
            return text[:10000]
        except Exception as e:
            logger.error(f"콘텐츠 추출 오류: {e}")
            return ''

    def _is_ai_related(self, text: str) -> bool:
        """텍스트 내 AI 키워드 포함 여부 판단"""
        low = text.lower()
        return any(k in low for k in self.ai_keywords)

    async def health_check(self) -> dict:
        """네트워크 연결 및 서비스 상태 확인"""
        try:
            r = self.session.get('https://httpbin.org/status/200', timeout=10)
            return {'status': 'healthy' if r.status_code == 200 else 'unhealthy', 'network_ok': r.status_code == 200, 'cosmos_service': self.cosmos_service is not None, 'openai_service': self.openai_service is not None}
        except Exception as e:
            logger.error(f"❌ 헬스 체크 실패: {e}")
            return {'status': 'unhealthy', 'error': str(e)}


class VectorDocumentCreator:
    """샘플 코스 데이터를 벡터 문서로 생성하여 Cosmos DB에 저장하는 서비스"""
    def __init__(self):
        self.cosmos_service = CosmosVectorService()
        self.openai_service = AzureOpenAIService()

    async def create_sample_vector_documents(self) -> int:
        """샘플 벡터 문서를 Cosmos DB에 생성 및 저장"""
        await self.cosmos_service.initialize_database()
        sample_courses = [
            {"title": "Introduction to Machine Learning", "description": "Learn the fundamentals of machine learning including supervised and unsupervised learning, neural networks, and practical applications in AI.", "category": "ai-courses", "difficulty": "beginner", "modules": 8, "duration_hours": 40},
            {"title": "Deep Learning with Neural Networks", "description": "Advanced course covering deep neural networks, convolutional networks, RNNs, and transformer architectures for AI applications.", "category": "ai-courses", "difficulty": "advanced", "modules": 12, "duration_hours": 60},
            {"title": "Natural Language Processing Fundamentals", "description": "Explore NLP techniques including tokenization, sentiment analysis, language models, and text generation using modern AI.", "category": "ai-courses", "difficulty": "intermediate", "modules": 10, "duration_hours": 50},
            {"title": "Computer Vision with AI", "description": "Learn image recognition, object detection, and computer vision applications using deep learning and AI technologies.", "category": "ai-courses", "difficulty": "intermediate", "modules": 9, "duration_hours": 45},
            {"title": "AI Ethics and Responsible AI Development", "description": "Understanding ethical considerations in AI development, bias mitigation, and responsible deployment of AI systems.", "category": "ai-courses", "difficulty": "beginner", "modules": 6, "duration_hours": 25}
        ]
        created_count = 0
        for i, course in enumerate(sample_courses):
            try:
                embedding_text = f"{course['title']}. {course['description']} Category: {course['category']}. Difficulty: {course['difficulty']}. Duration: {course['duration_hours']} hours."
                emb = await self.openai_service.generate_embeddings(embedding_text)
                if emb:
                    doc = {
                        "id": f"course_{i+1}_{course['title'].lower().replace(' ', '_')}",
                        "file_name": f"course_{i+1}",
                        "chunk_text": embedding_text,
                        "chunk_index": 0,
                        "embedding": emb,
                        "metadata": {
                            "source_type": "course_catalog", "title": course['title'], "description": course['description'], "category": course['category'], "difficulty": course['difficulty'], "modules": course['modules'], "duration_hours": course['duration_hours'], "created_at": datetime.now().isoformat()
                        }
                    }
                    await self.cosmos_service.container.create_item(body=doc)
                    created_count += 1
                    logger.info(f"✅ 벡터 문서 생성: {course['title']}")
            except Exception as e:
                logger.error(f"❌ 문서 생성 실패: {course['title']} | 오류: {e}")
        logger.info(f"🎉 {created_count}개의 벡터 문서 생성 완료")
        return created_count

    async def test_vector_search(self) -> list:
        """샘플 쿼리로 Cosmos DB 벡터 검색 테스트"""
        try:
            test_query = "machine"
            emb = await self.openai_service.generate_embeddings(test_query)
            if emb:
                results = await self.cosmos_service.search_similar_chunks(query_embedding=emb, limit=3, similarity_threshold=0.1)
                logger.info(f"🔍 '{test_query}' 검색 결과 {len(results)}개:")
                for idx, res in enumerate(results, 1):
                    title = res.get('metadata', {}).get('title', 'Unknown')
                    sim = res.get('similarity', 0)
                    logger.info(f"  {idx}. {title} (유사도: {sim:.3f})")
                return results
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {e}")
        return []

async def main():
    # 1) 웹 스크래핑 및 Cosmos DB 저장
    cosmos = CosmosVectorService()
    openai = AzureOpenAIService()
    scraper = WebScraperService(cosmos_service=cosmos, openai_service=openai)

    urls = [
        'https://www.artificial-intelligence.blog/terminology/artificial-intelligence',
    ]
    scrape_results = await scraper.scrape_multiple_and_save(urls)
    logger.info(f"웹 스크래핑 결과: {scrape_results}")

    # 2) 샘플 코스 벡터 문서 생성
    creator = VectorDocumentCreator()
    logger.info("🔄 샘플 벡터 문서 생성 시작...")
    created_count = await creator.create_sample_vector_documents()
    logger.info(f"샘플 벡터 문서 {created_count}개 생성 완료")

    # 3) 벡터 검색 테스트
    logger.info("🔍 벡터 검색 테스트 시작...")
    await creator.test_vector_search()

    # 4) Cosmos DB 클라이언트 종료
    await cosmos.close()

if __name__ == '__main__':
    asyncio.run(main())