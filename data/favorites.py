# data/favorites.py

from .db_session import SqlAlchemyBase
import sqlalchemy as sa
from sqlalchemy.orm import relationship

class Favorite(SqlAlchemyBase):
    __tablename__ = 'favorites'

    id         = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id    = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    variant_id = sa.Column(sa.Integer, sa.ForeignKey('product_variants.id', ondelete='CASCADE'), nullable=False)

    user    = relationship('User', back_populates='favorites')
    variant = relationship('ProductVariant', back_populates='favorites')

    __table_args__ = (
        sa.UniqueConstraint('user_id', 'variant_id', name='_user_variant_uc'),
    )
