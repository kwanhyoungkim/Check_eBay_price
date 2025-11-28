import json
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

class TranslationService:
    """한글 ↔ 영어 포켓몬 이름 변환"""
    
    def __init__(self):
        self._name_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """JSON 파일에서 캐시 로드"""
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'pokemon_names.json'
        )
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for pokemon in data:
                    korean = pokemon['korean_name']
                    english = pokemon['english_name']
                    self._name_cache[korean] = english
                    # 양방향 매핑 (영어→한글도 저장)
                    self._name_cache[english.lower()] = korean
                print(f"✅ {len(data)}개의 포켓몬 이름을 로드했습니다.")
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {json_path}")
            print("먼저 pokemon_name_scraper_api.py를 실행해주세요.")
        except Exception as e:
            print(f"❌ 캐시 로드 실패: {e}")
    
    def korean_to_english(self, korean_name):
        """한글 → 영어"""
        if korean_name in self._name_cache:
            result = self._name_cache[korean_name]
            # 결과가 한글이 아니면 반환
            if not self._is_korean(result):
                return result
        
        # 찾지 못하면 원본 반환
        return korean_name
    
    def english_to_korean(self, english_name):
        """영어 → 한글"""
        # 소문자로 검색
        english_lower = english_name.lower()
        if english_lower in self._name_cache:
            result = self._name_cache[english_lower]
            # 결과가 한글이면 반환
            if self._is_korean(result):
                return result
        
        return english_name
    
    def translate(self, name):
        """자동 감지 번역"""
        if self._is_korean(name):
            return self.korean_to_english(name)
        else:
            # 이미 영어면 그대로 반환
            return name
    
    def _is_korean(self, text):
        """텍스트에 한글이 포함되어 있는지 확인"""
        if not text:
            return False
        return any('\uac00' <= char <= '\ud7a3' for char in text)
    
    def search_pokemon(self, query):
        """포켓몬 이름 검색 (자동완성용)"""
        query_lower = query.lower()
        results = []
        seen = set()
        
        for key, value in self._name_cache.items():
            if query_lower in key.lower() or query_lower in value.lower():
                # 한글-영어 쌍 찾기
                if self._is_korean(key):
                    korean = key
                    english = value
                else:
                    korean = value
                    english = key
                
                pair = (korean, english)
                if pair not in seen:
                    seen.add(pair)
                    results.append({
                        'korean_name': korean,
                        'english_name': english
                    })
        
        return results[:10]  # 상위 10개만


# 테스트 코드
if __name__ == "__main__":
    print("=" * 60)
    print("포켓몬 이름 번역 서비스 테스트")
    print("=" * 60 + "\n")
    
    translator = TranslationService()
    
    if not translator._name_cache:
        print("⚠️  포켓몬 이름 데이터가 없습니다.")
        print("먼저 다음 명령을 실행하세요:")
        print("  python backend/scraper/pokemon_name_scraper_api.py")
        sys.exit(1)
    
    print("[ 번역 테스트 ]\n")
    
    # 한글 → 영어
    test_korean = ['피카츄', '리자몽', '이상해씨', '뮤츠', '잠만보']
    print("한글 → 영어:")
    for name in test_korean:
        result = translator.korean_to_english(name)
        print(f"  {name:10s} → {result}")
    
    print()
    
    # 영어 → 한글
    test_english = ['Pikachu', 'Charizard', 'Bulbasaur', 'Mewtwo', 'Snorlax']
    print("영어 → 한글:")
    for name in test_english:
        result = translator.english_to_korean(name)
        print(f"  {name:12s} → {result}")
    
    print()
    
    # 자동 번역
    print("자동 번역:")
    test_mixed = ['피카츄', 'Charizard', '뮤츠', 'Bulbasaur']
    for name in test_mixed:
        result = translator.translate(name)
        print(f"  {name:12s} → {result}")
    
    print()
    
    # 검색 테스트
    print("[ 검색 테스트 ]\n")
    search_query = '피카'
    print(f"검색어: '{search_query}'")
    search_results = translator.search_pokemon(search_query)
    for result in search_results:
        print(f"  {result['korean_name']} ({result['english_name']})")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)