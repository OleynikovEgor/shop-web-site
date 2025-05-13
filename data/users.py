import sqlalchemy
from data.db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash
from data.addresses    import Address
from data.cart_items   import CartItem
from data.favorites    import Favorite
from data.reviews      import Review
from data.payments     import Payment
from .db_session   import SqlAlchemyBase
from sqlalchemy.orm import relationship

class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    first_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    last_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    gender = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    phone_num = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    addresses = relationship(
        'Address',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # уже должны быть и другие связи:
    favorites = relationship('Favorite', back_populates='user', cascade='all, delete-orphan')
    cart_items = relationship('CartItem', back_populates='user', cascade='all, delete-orphan')
    reviews = relationship('Review', back_populates='user', cascade='all, delete-orphan')
    payments = relationship('Payment', back_populates='user', cascade='all, delete-orphan')
    payments = relationship(
        'Payment',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    # в классе User
    orders = relationship('Order', back_populates='user', cascade='all, delete-orphan')
