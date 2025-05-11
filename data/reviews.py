# data/reviews.py

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .db_session import SqlAlchemyBase  # ваш базовый класс

class Review(SqlAlchemyBase):
    __tablename__ = 'reviews'  # обязательно!

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id  = Column(Integer, ForeignKey('products.id'), nullable=False)
    text        = Column(Text, nullable=False)
    rating      = Column(Integer, nullable=False, default=5)
    images      = Column(String, nullable=True)   # JSON-строка с именами файлов
    video_url   = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # связи
    user    = relationship('User',    back_populates='reviews')
    product = relationship('Product', back_populates='reviews')

    @hybrid_property
    def images_list(self):
        """Возвращает список файлов из JSON-поля images"""
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except json.JSONDecodeError:
            return []

