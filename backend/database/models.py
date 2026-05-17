from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.database.db import Base


class Case(Base):
    __tablename__ = "cases"

    case_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, index=True, nullable=False)
    intent = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    possible_issue = Column(String, nullable=True)
    recommended_product = Column(String, nullable=True)

    risk_level = Column(String, nullable=False)
    escalation_required = Column(Boolean, default=False)

    order_id = Column(String, nullable=True)
    order_status = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)