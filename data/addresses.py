from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from data.db_session import SqlAlchemyBase
from sqlalchemy.orm import relationship

class Address(SqlAlchemyBase):
    __tablename__ = 'addresses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)

    user = relationship('User', back_populates='addresses')
