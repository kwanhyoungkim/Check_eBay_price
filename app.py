from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from main import PokemonPriceApp
from backend.database.db import search_cards_en, search_cards_jp, get_pokemon_name_info

load_dotenv()

base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(base_dir, 'frontend', 'static'),
    template_folder=os.path.join(base_dir, 'frontend', 'templates')
)

# ⚠️ 카드 데이터(영문/일본판)와 포켓몬 다국어 이름 매핑 모두 더 이상 로컬 JSON을
# 통째로 메모리에 올리지 않는다. docker-compose.yml 로 띄운 Postgres 컨테이너
# (cards_en, cards_jp, pokemon_names 테이블)를 대신 조회한다.
# (backend/database/load_en_cards.py, load_jp_cards.py, load_pokemon_names.py 로
#  최초 1회 적재 필요, README 참고)

# DB 및 스크래퍼 로직 인스턴스
price_app = PokemonPriceApp()

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/api/search')
def search_cards():
    name_input = request.args.get('name', '').strip()
    raw_lang = (request.args.get('language') or request.args.get('lang') or 'EN').upper()
    target_lang = 'ja' if raw_lang == 'JP' else 'en'
    
    if not name_input:
        return jsonify([])

    # 1. 이름 정보 확보 (Postgres pokemon_names 테이블 조회)
    try:
        name_info = get_pokemon_name_info(name_input)
    except Exception as e:
        print(f"❌ Postgres 조회 오류 (pokemon_names): {e}")
        name_info = None
    eng_name = name_info.get('english_name', '').lower() if name_info else name_input.lower()
    jp_name = name_info.get('japanese_name', '') if name_info else ""

    final_results = {}

    # 2. Postgres(도커 컨테이너)에서 조회한다. 영문판/일본판 둘 다 이제 로컬 JSON을
    #    직접 읽지 않고 cards_en / cards_jp 테이블을 쓴다. 두 테이블 모두 세트를
    #    전부 순회(+ Pocket 필터)해서 만든 데이터라 TCGdex 요약 엔드포인트로 별도
    #    보완할 필요가 없다(요약 엔드포인트는 set 정보가 부실해 Pocket 필터가
    #    못 걸러내는 경우가 있어 오히려 Pocket 카드가 섞여 들어오는 원인이었음).
    if target_lang == 'ja':
        try:
            for card in search_cards_jp(eng_name, jp_name):
                final_results[card['id']] = card
        except Exception as e:
            print(f"❌ Postgres 조회 오류 (cards_jp): {e}")
    else:
        try:
            for card in search_cards_en(eng_name):
                final_results[card['id']] = card
        except Exception as e:
            print(f"❌ Postgres 조회 오류 (cards_en): {e}")

    return jsonify(list(final_results.values()))

def _search_with_ladder(fetch_fn, prefix, name, number, series, label):
    """이름+번호 -> (부족하면) 이름+세트명 -> (그래도 없으면) 이름만, 3단계로 검색을 넓혀간다.
    fetch_fn은 EbayScraper.fetch_completed_sales 또는 fetch_recent_sales 둘 다 받을 수 있다.
    """
    query = f"{prefix}{name} {number} Pokemon Card".strip()
    print(f"🌐 [eBay {label} 쿼리 1차] {query}")
    prices = fetch_fn(query)

    if (not prices or len(prices) < 2) and series:
        alt_query = f"{prefix}{name} {series} Pokemon Card".strip()
        print(f"🌐 [eBay {label} 쿼리 2차] {alt_query}")
        alt_prices = fetch_fn(alt_query)
        if alt_prices:
            prices = alt_prices

    if not prices:
        broad_query = f"{prefix}{name} Pokemon Card".strip()
        print(f"🌐 [eBay {label} 쿼리 3차] {broad_query}")
        prices = fetch_fn(broad_query)

    return prices


@app.route('/api/price', methods=['POST'])
def get_prices():
    data = request.json
    name = (data.get('name') or '').strip()
    number = (data.get('number') or '').strip()
    series = (data.get('series') or '').strip()  # 사람이 읽는 세트 이름 (예: "30th Celebration (Japanese)")
    lang = data.get('lang', 'en').lower()

    try:
        prefix = "Japanese " if lang == 'ja' else ""

        # 1) 실제 판매완료가(Marketplace Insights API)를 먼저 시도한다.
        #    eBay 승인 전에는 매번 빈 리스트가 오는 게 정상이며, 그 경우 아래 2)로 넘어간다.
        prices = _search_with_ladder(
            price_app.scraper.fetch_completed_sales, prefix, name, number, series, "판매완료"
        )

        # 2) 판매완료 데이터가 없으면 현재 판매중인 매물 가격으로 대체한다(참고용).
        #    이 경우 각 항목에 status="active"가 붙어서, 프론트에서 "판매완료가 아님"을 표시할 수 있다.
        if not prices:
            prices = _search_with_ladder(
                price_app.scraper.fetch_recent_sales, prefix, name, number, series, "활성매물(대체)"
            )

        return jsonify(prices if prices else [])
    except Exception as e:
        print(f"❌ 가격 조회 오류: {e}")
        return jsonify([]), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)