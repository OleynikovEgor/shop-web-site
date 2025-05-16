from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .db_session import SqlAlchemyBase
from .favorites import Favorite

class Product(SqlAlchemyBase):
    __tablename__ = 'products'

    id       = Column(Integer, primary_key=True, autoincrement=True)


    variants = relationship(
        'ProductVariant',
        back_populates='product',
        cascade='all, delete-orphan'
    )


class ProductVariant(SqlAlchemyBase):
    __tablename__ = 'product_variants'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    product_id   = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)


    name         = Column(String, nullable=False)
    type         = Column(String, nullable=False)
    price        = Column(Integer, nullable=False)
    description  = Column(Text,    nullable=True)
    rating       = Column(Float,   default=0.0)
    reviews_cnt  = Column(Integer, default=0)


    color_code   = Column(String(50), nullable=False)
    image_main   = Column(String,    nullable=False)
    image_1      = Column(String,    nullable=True)
    image_2      = Column(String,    nullable=True)
    image_3      = Column(String,    nullable=True)
    stock = Column(
        Integer,
        nullable=False,
        default=1000,
        server_default="1000"
    )
    # связи
    product      = relationship('Product',        back_populates='variants')
    reviews      = relationship('Review',         back_populates='variant',
                                 cascade='all, delete-orphan')

    favorites = relationship('Favorite', back_populates='variant', cascade='all, delete-orphan')
    cart_items = relationship('CartItem', back_populates='variant', cascade='all,delete-orphan')
    order_items = relationship('OrderItem', back_populates='variant', cascade='all, delete-orphan')
    @hybrid_property
    def images_list(self):
        imgs = [self.image_main]
        for img in (self.image_1, self.image_2, self.image_3):
            if img:
                imgs.append(img)
        return imgs
