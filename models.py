import uuid
import enum
import datetime
from sqlalchemy import Column, String, Numeric, ForeignKey, Enum, DateTime
from database import Base

class EntryType(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="ACTIVE")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False) # TRANSFER, DEPOSIT, WITHDRAWAL
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(Numeric(19, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)