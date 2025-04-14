from sqlalchemy import Column, Integer, String, ForeignKey
from data.db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash


class Payment(SqlAlchemyBase):
    __tablename__ = 'payments'
    __table_args__ = {'extend_existing': True}  # Добавляем, чтобы переопределить существующую таблицу

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Хэшированные данные карты
    card_number = Column(String, nullable=False)
    card_last4 = Column(String, nullable=False)
    card_holder = Column(String, nullable=False)
    expiry_date = Column(String, nullable=False)
    cvv = Column(String, nullable=False)
