from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class PokemonName(db.Model):
    """포켓몬 이름 매핑 테이블"""
    __tablename__ = 'pokemon_names'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), nullable=False)
    korean_name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    english_name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    def to_dict(self):
        return {
            'number': self.number,
            'korean_name': self.korean_name,
            'english_name': self.english_name
        }

class CardResult(db.Model):
    """eBay 검색 결과 캐시"""
    __tablename__ = 'card_results'
    
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(200), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    sale_date = db.Column(db.DateTime)
    condition = db.Column(db.String(50))
    url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'title': self.title,
            'price': self.price,
            'currency': self.currency,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'condition': self.condition,
            'url': self.url,
            'image_url': self.image_url
        }