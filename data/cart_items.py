from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase

class CartItem(SqlAlchemyBase):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)

    product = relationship('Product')
    # вот это — связь на пользователя
    user = relationship('User', back_populates='cart_items')

    @property
    def subtotal(self):
        return self.quantity * self.product.price
