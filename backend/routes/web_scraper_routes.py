"""
Enhanced Web Scraper Routes - Uses professional scraper with fallback
routes/web_scraper_routes.py
"""

import asyncio
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

logger = logging.getLogger(__name__)

# Blueprint 생성
web_scraper_bp = Blueprint('web_scraper', __name__)

# Global scraper instance
_scraper = None
_scraper_type = None

def get_scraper():
    """스크래퍼 인스턴스 가져오기 (전문적인 스크래퍼 우선, 실패시 간단한 스크래퍼)"""
    global _scraper, _scraper_type
    
    if _scraper is None:
        try:
            # 경로 추가
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            # 전문적인 스크래퍼 시도
            from services.web_scraper_service import get_scraper
            _scraper = get_scraper(use_professional=True)
            _scraper_type = type(_scraper).__name__
            logger.info(f"✅ {_scraper_type} 스크래퍼 초기화 성공")
        except Exception as e:
            logger.warning(f"⚠️ 전문 스크래퍼 실패, 간단한 스크래퍼 사용: {e}")
            try:
                # 간단한 스크래퍼 fallback
                from services.web_scraper_service import SimpleWebScraper
                _scraper = SimpleWebScraper()
                _scraper_type = "SimpleWebScraper"
            except Exception as e2:
                logger.warning(f"⚠️ 서비스 스크래퍼도 실패, 내장 스크래퍼 사용: {e2}")
                # 완전한 fallback - 내장 간단한 스크래퍼
                _scraper = create_fallback_scraper()
                _scraper_type = "FallbackScraper"
    
    return _scraper

def create_fallback_scraper():
    """완전한 fallback 스크래퍼 (외부 의존성 없음)"""
    import requests
    from bs4 import BeautifulSoup
    import re
    from datetime import datetime
    
    class FallbackScraper:
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
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 기본 정보 추출
                title = self.extract_title(soup)
                content = self.extract_content(soup)
                
                # 분석
                word_count = len(content.split())
                ai_related = self.is_ai_related(content, title)
                quality_score = self.calculate_quality(content, title, word_count)
                
                return {
                    'success': True,
                    'url': url,
                    'title': title,
                    'content': content[:1000] + "..." if len(content) > 1000 else content,
                    'word_count': word_count,
                    'ai_related': ai_related,
                    'quality_score': quality_score,
                    'scraped_at': datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    'success': False,
                    'url': url,
                    'error': str(e)
                }

        def extract_title(self, soup):
            h1 = soup.find('h1')
            if h1 and h1.get_text(strip=True):
                return h1.get_text(strip=True)
            if soup.title:
                return soup.title.get_text(strip=True)
            return "Untitled"

        def extract_content(self, soup):
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            article = soup.find('article')
            if article:
                content = article.get_text(separator=' ', strip=True)
            elif soup.body:
                content = soup.body.get_text(separator=' ', strip=True)
            else:
                content = soup.get_text(separator=' ', strip=True)
            
            content = re.sub(r'\s+', ' ', content)
            return content.strip()

        def is_ai_related(self, content, title):
            text = f"{title} {content}".lower()
            return any(keyword in text for keyword in self.ai_keywords)

        def calculate_quality(self, content, title, word_count):
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
    
    return FallbackScraper()

def async_route(f):
    """비동기 라우트 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# === API 엔드포인트 ===

@web_scraper_bp.route('/health', methods=['GET'])
@async_route
async def scraper_health():
    """웹 스크래퍼 상태 확인"""
    try:
        scraper = get_scraper()
        
        health_info = {
            'success': True,
            'status': 'healthy',
            'scraper_type': _scraper_type,
            'message': f'{_scraper_type}이 정상 작동 중입니다',
            'timestamp': datetime.now().isoformat()
        }
        
        # 전문적인 스크래퍼인 경우 상세 상태 확인
        if hasattr(scraper, 'health_check'):
            detailed_health = await scraper.health_check()
            health_info['detailed_status'] = detailed_health
        
        return jsonify(health_info)
        
    except Exception as e:
        logger.error(f"❌ 스크래퍼 상태 확인 실패: {e}")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@web_scraper_bp.route('/scrape', methods=['POST'])
@async_route
async def scrape_url():
    """단일 URL 스크래핑"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL이 필요합니다',
                'required_format': {'url': 'https://example.com'}
            }), 400
        
        url = data['url'].strip()
        if not url.startswith(('http://', 'https://')):
            return jsonify({
                'success': False,
                'error': '유효한 URL을 입력해주세요 (http:// 또는 https://로 시작)'
            }), 400
        
        # 옵션 파라미터
        store_to_db = data.get('store_to_db', True)  # 기본값: DB에 저장
        use_professional = data.get('use_professional', True)  # 기본값: 전문적인 스크래핑
        
        scraper = get_scraper()
        
        logger.info(f"🔍 스크래핑 시작: {url} (스크래퍼: {_scraper_type})")
        
        # 스크래핑 실행
        if hasattr(scraper, 'scrape_and_store_professionally') and use_professional and store_to_db:
            # 전문적인 스크래핑 + DB 저장
            result = await scraper.scrape_and_store_professionally(url)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': '전문적인 스크래핑이 완료되었습니다',
                    'scraper_type': 'EnvironmentFixedScraper',
                    'data': result,
                    'features': {
                        'professional_extraction': True,
                        'quality_analysis': True,
                        'ai_relevance_scoring': True,
                        'semantic_chunking': True,
                        'rich_metadata': True,
                        'cosmos_db_storage': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', '전문적인 스크래핑 실패'),
                    'details': result
                }), 400
                
        elif hasattr(scraper, 'scrape_url'):
            # 간단한 스크래핑
            result = scraper.scrape_url(url)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': '스크래핑이 완료되었습니다',
                    'scraper_type': 'SimpleWebScraper',
                    'data': result,
                    'features': {
                        'professional_extraction': False,
                        'basic_analysis': True,
                        'cosmos_db_storage': False
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', '스크래핑 실패')
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': '스크래퍼가 초기화되지 않았습니다'
            }), 500
    
    except Exception as e:
        logger.error(f"❌ 스크래핑 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@web_scraper_bp.route('/scrape/simple', methods=['POST'])
@async_route
async def scrape_url_simple():
    """간단한 스크래핑 (DB 저장 없음)"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL이 필요합니다'
            }), 400
        
        url = data['url'].strip()
        
        # 간단한 스크래퍼 사용
        try:
            # 경로 추가
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            from services.web_scraper_service import SimpleWebScraper
            simple_scraper = SimpleWebScraper()
        except Exception:
            # 완전한 fallback
            simple_scraper = create_fallback_scraper()
            
        result = simple_scraper.scrape_url(url)
            
        if result['success']:
                return jsonify({
                    'success': True,
                    'message': '간단한 스크래핑이 완료되었습니다',
                    'data': result
                })
        else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', '스크래핑 실패')
                }), 400
                
    except Exception as e:
            return jsonify({
                'success': False,
                'error': f'간단한 스크래퍼 오류: {str(e)}'
            }), 500
    
    except Exception as e:
        logger.error(f"❌ 간단한 스크래핑 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500

@web_scraper_bp.route('/test', methods=['GET'])
@async_route
async def test_scraper():
    """스크래퍼 테스트"""
    try:
        test_urls = [
            "https://httpbin.org/html",
            "https://www.wikipedia.org/",
            "https://www.bing.com",
            "https://www.artificial-intelligence.blog/terminology/artificial-intelligence"
        ]
        
        scraper = get_scraper()
        results = []
        
        for test_url in test_urls:
            try:
                if hasattr(scraper, 'scrape_url'):
                    result = scraper.scrape_url(test_url)
                    results.append({
                        'url': test_url,
                        'success': result['success'],
                        'title': result.get('title', 'N/A'),
                        'word_count': result.get('word_count', 0),
                        'quality_score': result.get('quality_score', 0)
                    })
                else:
                    results.append({
                        'url': test_url,
                        'success': False,
                        'error': '스크래퍼에 scrape_url 메서드가 없습니다'
                    })
            except Exception as e:
                results.append({
                    'url': test_url,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': '테스트 완료',
            'scraper_type': _scraper_type,
            'test_results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@web_scraper_bp.route('/capabilities', methods=['GET'])
def scraper_capabilities():
    """스크래퍼 기능 정보"""
    try:
        scraper = get_scraper()
        
        capabilities = {
            'scraper_type': _scraper_type,
            'basic_scraping': hasattr(scraper, 'scrape_url'),
            'professional_scraping': hasattr(scraper, 'scrape_and_store_professionally'),
            'health_check': hasattr(scraper, 'health_check'),
            'cosmos_db_storage': hasattr(scraper, 'cosmos_service'),
            'ai_analysis': hasattr(scraper, 'ai_keywords'),
            'quality_scoring': hasattr(scraper, 'calculate_quality_score'),
            'semantic_chunking': hasattr(scraper, 'create_professional_chunks')
        }
        
        features = []
        if capabilities['basic_scraping']:
            features.append('Basic web scraping')
        if capabilities['professional_scraping']:
            features.append('Professional content extraction')
        if capabilities['cosmos_db_storage']:
            features.append('Cosmos DB storage')
        if capabilities['ai_analysis']:
            features.append('AI relevance analysis')
        if capabilities['quality_scoring']:
            features.append('Content quality scoring')
        if capabilities['semantic_chunking']:
            features.append('Semantic text chunking')
        
        return jsonify({
            'success': True,
            'scraper_type': _scraper_type,
            'capabilities': capabilities,
            'available_features': features,
            'endpoints': {
                'health': '/api/scraper/health',
                'scrape': '/api/scraper/scrape',
                'simple_scrape': '/api/scraper/scrape/simple',
                'test': '/api/scraper/test',
                'capabilities': '/api/scraper/capabilities'
            },
            'usage_examples': {
                'professional_scraping': {
                    'url': '/api/scraper/scrape',
                    'method': 'POST',
                    'body': {
                        'url': 'https://example.com/article',
                        'store_to_db': True,
                        'use_professional': True
                    }
                },
                'simple_scraping': {
                    'url': '/api/scraper/scrape/simple',
                    'method': 'POST',
                    'body': {
                        'url': 'https://example.com/article'
                    }
                }
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@web_scraper_bp.route('/batch', methods=['POST'])
@async_route
async def batch_scrape():
    """여러 URL 일괄 스크래핑"""
    try:
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({
                'success': False,
                'error': 'URLs 배열이 필요합니다',
                'required_format': {'urls': ['https://example1.com', 'https://example2.com']}
            }), 400
        
        urls = data['urls']
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({
                'success': False,
                'error': 'URLs는 비어있지 않은 배열이어야 합니다'
            }), 400
        
        if len(urls) > 10:  # 안전을 위한 제한
            return jsonify({
                'success': False,
                'error': '한 번에 최대 10개의 URL만 처리할 수 있습니다'
            }), 400
        
        # 옵션 파라미터
        store_to_db = data.get('store_to_db', True)
        use_professional = data.get('use_professional', True)
        
        scraper = get_scraper()
        results = []
        successful = 0
        failed = 0
        
        logger.info(f"🔍 일괄 스크래핑 시작: {len(urls)}개 URL")
        
        for i, url in enumerate(urls):
            try:
                url = url.strip()
                if not url.startswith(('http://', 'https://')):
                    results.append({
                        'url': url,
                        'success': False,
                        'error': '유효하지 않은 URL 형식'
                    })
                    failed += 1
                    continue
                
                # 스크래핑 실행
                if hasattr(scraper, 'scrape_and_store_professionally') and use_professional and store_to_db:
                    result = await scraper.scrape_and_store_professionally(url)
                elif hasattr(scraper, 'scrape_url'):
                    result = scraper.scrape_url(url)
                else:
                    result = {'success': False, 'error': '스크래퍼를 사용할 수 없습니다'}
                
                if result['success']:
                    successful += 1
                    # 결과에서 큰 데이터는 요약만 포함
                    summary_result = {
                        'url': url,
                        'success': True,
                        'title': result.get('document', {}).get('title') or result.get('title', 'N/A'),
                        'word_count': result.get('document', {}).get('word_count') or result.get('word_count', 0),
                        'quality_score': result.get('document', {}).get('quality_score') or result.get('quality_score', 0)
                    }
                    
                    if 'chunks' in result:
                        summary_result['chunks_created'] = result['chunks']['total_created']
                        summary_result['chunks_stored'] = result['chunks']['stored_successfully']
                    
                    results.append(summary_result)
                else:
                    failed += 1
                    results.append({
                        'url': url,
                        'success': False,
                        'error': result.get('error', '스크래핑 실패')
                    })
                
                logger.info(f"  📄 {i+1}/{len(urls)} 완료: {url}")
                
            except Exception as e:
                failed += 1
                results.append({
                    'url': url,
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"  ❌ {i+1}/{len(urls)} 실패: {url} - {e}")
        
        return jsonify({
            'success': True,
            'message': f'일괄 스크래핑 완료: {successful}개 성공, {failed}개 실패',
            'summary': {
                'total_urls': len(urls),
                'successful': successful,
                'failed': failed,
                'success_rate': round((successful / len(urls)) * 100, 1)
            },
            'results': results,
            'scraper_type': _scraper_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 일괄 스크래핑 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@web_scraper_bp.route('/stats', methods=['GET'])
def scraper_stats():
    """스크래퍼 통계 정보"""
    try:
        scraper = get_scraper()
        
        stats = {
            'scraper_type': _scraper_type,
            'initialization_time': datetime.now().isoformat(),
            'features': {
                'professional_mode': hasattr(scraper, 'scrape_and_store_professionally'),
                'cosmos_db_integration': hasattr(scraper, 'cosmos_service'),
                'ai_analysis': hasattr(scraper, 'ai_keywords'),
                'quality_scoring': hasattr(scraper, 'calculate_quality_score')
            }
        }
        
        # AI 키워드 통계 (있는 경우)
        if hasattr(scraper, 'ai_keywords'):
            stats['ai_keywords'] = {
                'total_keywords': len(scraper.ai_keywords),
                'top_keywords': list(scraper.ai_keywords.keys())[:10]
            }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Error handlers specific to web scraper
@web_scraper_bp.errorhandler(400)
def scraper_bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request to web scraper',
        'message': '요청 형식을 확인해주세요',
        'required_format': {
            'scrape': {'url': 'https://example.com'},
            'batch': {'urls': ['https://example1.com', 'https://example2.com']}
        },
        'timestamp': datetime.now().isoformat()
    }), 400

@web_scraper_bp.errorhandler(500)
def scraper_internal_error(error):
    logger.error(f"Web scraper internal error: {error}")
    return jsonify({
        'success': False,
        'error': 'Web scraper internal error',
        'message': '웹 스크래퍼에서 내부 오류가 발생했습니다',
        'timestamp': datetime.now().isoformat()
    }), 500

# 독립 실행을 위한 테스트 코드
if __name__ == '__main__':
    print("🧪 Enhanced 웹 스크래퍼 라우트 독립 테스트")
    
    try:
        # 경로 설정
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        # 스크래퍼 초기화 테스트
        scraper = get_scraper()
        print(f"✅ 스크래퍼 초기화 성공: {_scraper_type}")
        
        # 간단한 기능 테스트
        if hasattr(scraper, 'scrape_url'):
            test_result = scraper.scrape_url("https://httpbin.org/html")
            
            if test_result['success']:
                print("✅ 기본 스크래핑 테스트 성공!")
                print(f"제목: {test_result['title']}")
                print(f"내용 길이: {len(test_result['content'])} 문자")
            else:
                print(f"❌ 기본 스크래핑 테스트 실패: {test_result['error']}")
        
        # 전문적인 기능 테스트 (비동기)
        if hasattr(scraper, 'scrape_and_store_professionally'):
            print("✅ 전문적인 스크래핑 기능 사용 가능")
        else:
            print("⚠️ 전문적인 스크래핑 기능 없음 (간단한 모드)")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()