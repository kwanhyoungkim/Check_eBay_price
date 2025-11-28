import os
import sys
import json
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

class SearchService:
    """카드 검색 및 캐싱 서비스
    
    주의: 실제로는 Flask 앱에서 DB와 함께 사용됩니다.
    이 버전은 테스트용으로 JSON 파일 캐시를 사용합니다.
    """
    
    def __init__(self, use_db=False):
        """
        Args:
            use_db: True면 데이터베이스 사용, False면 JSON 캐시 사용
        """
        self.use_db = use_db
        self.cache_hours = 24
        self.cache_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'search_cache.json'
        )
        
        # 번역 서비스 로드
        from backend.service.translation import TranslationService
        self.translator = TranslationService()
        
        # eBay 스크래퍼 로드
        from backend.scraper.ebay_scraper import EbayScraper
        self.scraper = EbayScraper()
    
    def search_cards(self, name, use_cache=True):
        """카드 검색
        
        Args:
            name: 포켓몬 이름 (한글 또는 영어)
            use_cache: 캐시 사용 여부
            
        Returns:
            list: 카드 정보 리스트
        """
        # 한글이면 영어로 변환
        english_name = self.translator.translate(name)
        
        print(f"🔍 검색: {name} → {english_name}")
        
        # 캐시 확인
        if use_cache:
            cached = self._get_from_cache(english_name)
            if cached:
                print(f"✅ 캐시에서 반환: {len(cached)}개")
                return cached
        
        # eBay 스크래핑
        print("🌐 eBay 스크래핑 시작...")
        results = self.scraper.search_sold_cards(english_name, max_results=50)
        
        if not results:
            print("⚠️  검색 결과 없음")
            return []
        
        print(f"✅ {len(results)}개 결과 발견")
        
        # 캐시에 저장
        self._save_to_cache(english_name, results)
        
        return results
    
    def _get_from_cache(self, query):
        """캐시에서 검색 (JSON 파일 사용)"""
        if not os.path.exists(self.cache_file):
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if query not in cache_data:
                return None
            
            cached_entry = cache_data[query]
            cached_time = datetime.fromisoformat(cached_entry['cached_at'])
            
            # 캐시 만료 확인
            if datetime.utcnow() - cached_time > timedelta(hours=self.cache_hours):
                print("⏰ 캐시 만료됨")
                return None
            
            return cached_entry['results']
            
        except Exception as e:
            print(f"⚠️  캐시 읽기 실패: {e}")
            return None
    
    def _save_to_cache(self, query, results):
        """캐시에 저장 (JSON 파일 사용)"""
        try:
            # 기존 캐시 로드
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
            
            # 새 데이터 추가
            cache_data[query] = {
                'cached_at': datetime.utcnow().isoformat(),
                'results': results
            }
            
            # 저장
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 캐시 저장 완료")
            
        except Exception as e:
            print(f"⚠️  캐시 저장 실패: {e}")
    
    def clear_cache(self):
        """캐시 초기화"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("🗑️  캐시 삭제 완료")
                return True
        except Exception as e:
            print(f"❌ 캐시 삭제 실패: {e}")
            return False


# 테스트 코드
if __name__ == "__main__":
    print("=" * 70)
    print("포켓몬 카드 검색 서비스 테스트")
    print("=" * 70)
    print("⚠️  이 테스트는 실제로 eBay를 스크래핑합니다.")
    print("=" * 70 + "\n")
    
    # 검색 서비스 생성 (JSON 캐시 사용)
    search_service = SearchService(use_db=False)
    
    # 테스트 검색
    test_names = ['피카츄', 'Charizard']
    
    for name in test_names:
        print(f"\n{'='*70}")
        print(f"테스트: {name}")
        print("=" * 70 + "\n")
        
        results = search_service.search_cards(name)
        
        if results:
            print(f"\n[ 검색 결과 상위 5개 ]\n")
            for idx, card in enumerate(results[:5], 1):
                print(f"{idx}. {card['title'][:60]}...")
                print(f"   💰 가격: ${card['price']:.2f} {card['currency']}")
                print(f"   📊 상태: {card['condition']}")
                print(f"   🔗 {card['url'][:50]}...\n")
        else:
            print("검색 결과가 없습니다.")
        
        # 다음 검색 전 잠시 대기 (eBay 요청 제한)
        if name != test_names[-1]:
            print("⏳ 3초 대기 중...")
            import time
            time.sleep(3)
    
    print("\n" + "=" * 70)
    print("✅ 테스트 완료!")
    print(f"💾 캐시 파일: {search_service.cache_file}")
    print("=" * 70)