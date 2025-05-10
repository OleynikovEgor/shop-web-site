import sqlalchemy
from .db_session import SqlAlchemyBase

class Product(SqlAlchemyBase):
    __tablename__ = 'products'

    id           = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name         = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    type         = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    price        = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    image        = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    rating       = sqlalchemy.Column(sqlalchemy.Float,   default=0.0)
    review_count = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    description  = sqlalchemy.Column(sqlalchemy.Text)  # новое поле

    def __repr__(self):
        return f"<Product {self.id} {self.name!r}>"
