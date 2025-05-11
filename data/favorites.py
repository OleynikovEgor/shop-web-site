# data/favorites.py
from .db_session import SqlAlchemyBase
import sqlalchemy as sa

class Favorite(SqlAlchemyBase):
    __tablename__ = 'favorites'
    id         = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id    = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    product_id = sa.Column(sa.Integer, sa.ForeignKey('products.id'), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),
    )
