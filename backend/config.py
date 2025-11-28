import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///pokemon_cards.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 캐시 설정
    CACHE_EXPIRY_HOURS = 24
    MAX_SEARCH_RESULTS = 50
    
    # eBay 설정
    EBAY_MAX_RESULTS = 50