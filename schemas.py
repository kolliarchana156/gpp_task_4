from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# --- Account Schemas ---
class AccountCreate(BaseModel):
    user_id: str
    account_type: str
    currency: str = "USD"

class AccountResponse(BaseModel):
    id: str
    user_id: str
    account_type: str
    currency: str
    status: str
    balance: Decimal

    class Config:
        from_attributes = True

# --- Ledger History Schema ---
class LedgerEntryResponse(BaseModel):
    id: str
    account_id: str
    transaction_id: str
    entry_type: str
    amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

# --- Transaction Schemas ---
class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    description: Optional[str] = "Internal Transfer"

class DepositRequest(BaseModel):
    account_id: str
    amount: Decimal
    description: Optional[str] = "Cash Deposit"

class WithdrawalRequest(BaseModel):
    account_id: str
    amount: Decimal
    description: Optional[str] = "Cash Withdrawal"