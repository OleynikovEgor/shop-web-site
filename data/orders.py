from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime
from .db_session import SqlAlchemyBase

class Order(SqlAlchemyBase):
    __tablename__ = 'orders'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey('users.id'), nullable=False)
    address_id    = Column(Integer, ForeignKey('addresses.id'), nullable=False)
    payment_id    = Column(Integer, ForeignKey('payments.id'), nullable=False)
    total_amount  = Column(Numeric(10, 2), nullable=False)
    status        = Column(String(50), default='Обрабатывается', nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user          = relationship('User', back_populates='orders')
    address       = relationship('Address')
    payment       = relationship('Payment')
    items         = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')


class OrderItem(SqlAlchemyBase):
    __tablename__ = 'order_items'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id    = Column(Integer, ForeignKey('products.id'), nullable=False)
    variant_id    = Column(Integer, ForeignKey('product_variants.id'), nullable=True)
    quantity      = Column(Integer, nullable=False)
    unit_price    = Column(Numeric(10,2), nullable=False)

    order         = relationship('Order', back_populates='items')
    variant = relationship('ProductVariant', back_populates='order_items')
    product       = relationship('Product')

