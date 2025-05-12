# data/reviews.py

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase

class Review(SqlAlchemyBase):
    __tablename__ = 'reviews'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey('users.id'), nullable=False)
    variant_id  = Column(Integer, ForeignKey('product_variants.id', ondelete='CASCADE'), nullable=False)
    text        = Column(Text, nullable=False)
    rating      = Column(Integer, nullable=False, default=5)
    images      = Column(String, nullable=True)   # JSON-строка с именами файлов
    video_url   = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # связи
    user    = relationship('User',            back_populates='reviews')
    variant = relationship('ProductVariant',  back_populates='reviews')

    @property
    def images_list(self):
        """
        Возвращает список имён файлов из JSON-поля images
        """
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except json.JSONDecodeError:
            return []
