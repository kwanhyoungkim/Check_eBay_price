import requests
import json
import os
import time

POKEAPI_BASE = "https://pokeapi.co/api/v2"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/pokemon_names.json")


def fetch_pokemon_names(max_pokemon=1025):
    """PokeAPI에서 포켓몬 이름 수집"""
    print("=" * 70)
    print(f"PokeAPI에서 포켓몬 데이터 수집 중 (최대 {max_pokemon}개)")
    print("=" * 70)
    print("⏱️  예상 소요 시간: 3-5분")
    print("=" * 70 + "\n")
    
    pokemon_data = []
    
    for pokemon_id in range(1, max_pokemon + 1):
        try:
            # 진행 상황 표시
            if pokemon_id % 50 == 0:
                print(f"진행: {pokemon_id}/{max_pokemon} ({pokemon_id/max_pokemon*100:.1f}%)")
            
            # 포켓몬 상세 정보
            pokemon_url = f"{POKEAPI_BASE}/pokemon/{pokemon_id}"
            response = requests.get(pokemon_url, timeout=10)
            
            if response.status_code == 404:
                # 존재하지 않는 번호는 건너뛰기
                continue
            
            response.raise_for_status()
            pokemon_detail = response.json()
            
            # 영어 이름
            english_name = pokemon_detail['name'].replace('-', ' ').title()
            
            # 도감 번호
            number = str(pokemon_detail['id']).zfill(4)
            
            # 종 정보에서 한글 이름 가져오기
            species_url = pokemon_detail['species']['url']
            species_response = requests.get(species_url, timeout=10)
            species_response.raise_for_status()
            species_data = species_response.json()
            
            # 한글 이름 찾기
            korean_name = None
            for name_entry in species_data.get('names', []):
                if name_entry.get('language', {}).get('name') == 'ko':
                    korean_name = name_entry.get('name')
                    break
            
            # 한글 이름이 없으면 영어 이름 사용
            if not korean_name:
                korean_name = english_name
            
            pokemon_data.append({
                "number": number,
                "korean_name": korean_name,
                "english_name": english_name
            })
            
            # API 제한 준수 (초당 ~10 요청)
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️  포켓몬 #{pokemon_id} 처리 실패: {e}")
            continue
        except KeyboardInterrupt:
            print("\n\n중단됨! 지금까지 수집한 데이터를 저장합니다...")
            break
    
    return pokemon_data


def save_to_json(data, filename):
    """JSON 파일로 저장"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ {len(data)}개의 포켓몬 데이터를 저장했습니다.")
        print(f"파일 위치: {os.path.abspath(filename)}")
        return True
    except IOError as e:
        print(f"❌ 저장 실패: {e}")
        return False


if __name__ == "__main__":
    # 포켓몬 데이터 수집
    pokemon_names = fetch_pokemon_names(max_pokemon=1025)
    
    if pokemon_names:
        # 도감 번호순 정렬
        pokemon_names.sort(key=lambda x: int(x['number']))
        
        print(f"\n{'='*70}")
        print(f"✅ 총 {len(pokemon_names)}개의 포켓몬 이름을 수집했습니다!")
        print("=" * 70)
        
        # 샘플 출력
        print("\n[ 처음 10개 포켓몬 ]")
        for p in pokemon_names[:10]:
            print(f"  #{p['number']} {p['korean_name']} ({p['english_name']})")
        
        print("\n[ 마지막 10개 포켓몬 ]")
        for p in pokemon_names[-10:]:
            print(f"  #{p['number']} {p['korean_name']} ({p['english_name']})")
        
        # 저장
        if save_to_json(pokemon_names, OUTPUT_FILE):
            print("\n" + "=" * 70)
            print("🎉 완료! 이제 Flask 앱을 실행할 수 있습니다.")
            print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ 데이터 수집 실패")
        print("=" * 70)