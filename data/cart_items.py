from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase

class CartItem(SqlAlchemyBase):
    __tablename__ = 'cart_items'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variants.id', ondelete='CASCADE'), nullable=False)
    quantity   = Column(Integer, default=1, nullable=False)

    user    = relationship('User',           back_populates='cart_items')
    variant = relationship('ProductVariant', back_populates='cart_items')

    __table_args__ = (
        UniqueConstraint('user_id', 'variant_id', name='_user_variant_cart_uc'),
    )

    @property
    def subtotal(self):
        return self.quantity * self.variant.price
