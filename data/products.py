# data/products.py
from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from sqlalchemy.ext.hybrid import hybrid_property
import json

class Product(SqlAlchemyBase):
    __tablename__ = 'products'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String, nullable=False)
    type         = Column(String, nullable=False)
    price        = Column(Integer, nullable=False)
    image_main   = Column(String, nullable=False)   # главное фото
    image_1      = Column(String, nullable=True)    # доп. фото 1
    image_2      = Column(String, nullable=True)    # доп. фото 2
    image_3      = Column(String, nullable=True)    # доп. фото 3
    rating       = Column(Float, default=0.0)       # средний рейтинг
    reviews_cnt  = Column(Integer, default=0)       # кол-во отзывов
    description  = Column(Text, nullable=True)
    color_images       = Column(String, nullable=True)    # например: "#000000,#ffffff"
    # связь с отзывами
    reviews      = relationship('Review', back_populates='product', cascade='all, delete-orphan')

    @hybrid_property
    def color_images_list(self):
        if not self.color_images:
            return []
        # если CSV
        if ',' in self.color_images:
            return [fn.strip() for fn in self.color_images.split(',') if fn.strip()]
        # если JSON
        try:
            return json.loads(self.color_images)
        except Exception:
            return []