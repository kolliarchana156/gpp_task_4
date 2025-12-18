from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import models, schemas
from database import SessionLocal, engine, get_db
from models import EntryType

# 1. Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Double-Entry Ledger API")

# --- ACCOUNT ENDPOINTS ---

@app.post("/accounts", response_model=schemas.AccountResponse)
def create_new_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    db_account = models.Account(
        user_id=account.user_id,
        account_type=account.account_type,
        currency=account.currency
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return {**db_account.__dict__, "balance": 0.00}

@app.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def get_account_details(account_id: str, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    balance_query = text("""
        SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0)
        FROM ledger_entries
        WHERE account_id = :acc_id
    """)
    current_balance = db.execute(balance_query, {"acc_id": account_id}).scalar()
    
    return {
        "id": account.id,
        "user_id": account.user_id,
        "account_type": account.account_type,
        "currency": account.currency,
        "status": account.status,
        "balance": current_balance
    }

# --- LEDGER HISTORY ENDPOINT ---

@app.get("/accounts/{account_id}/ledger", response_model=List[schemas.LedgerEntryResponse])
def get_ledger_history(account_id: str, db: Session = Depends(get_db)):
    entries = db.query(models.LedgerEntry)\
        .filter(models.LedgerEntry.account_id == account_id)\
        .order_by(models.LedgerEntry.created_at.desc())\
        .all()
    return entries

# --- SYSTEM AUDIT ENDPOINT (Step 7) ---

@app.get("/audit/integrity-check")
def integrity_check(db: Session = Depends(get_db)):
    """
    Verifies system-wide integrity.
    Checks total liquidity and ensures every transaction has a balanced set of entries.
    """
    # 1. Total Liquidity: Sum(Credits) - Sum(Debits)
    query = text("""
        SELECT SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END)
        FROM ledger_entries
    """)
    net_sum = db.execute(query).scalar()
    
    # 2. Transaction Balancing: Ensure every transaction has an even number of entries
    # (Since every transfer MUST have 1 debit and 1 credit)
    transfer_integrity_query = text("""
        SELECT transaction_id 
        FROM ledger_entries 
        GROUP BY transaction_id 
        HAVING (COUNT(*) % 2) != 0
    """)
    unbalanced_txs = db.execute(transfer_integrity_query).all()

    return {
        "total_system_liquidity": float(net_sum or 0),
        "unbalanced_transactions_count": len(unbalanced_txs),
        "status": "Healthy" if len(unbalanced_txs) == 0 else "Integrity Compromised"
    }

# --- TRANSACTION ENDPOINTS (ACID PROTECTED) ---

@app.post("/deposits")
def deposit_funds(deposit: schemas.DepositRequest, db: Session = Depends(get_db)):
    if deposit.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    with db.begin():
        new_tx = models.Transaction(type="DEPOSIT", description=deposit.description, status="COMPLETED")
        db.add(new_tx)
        db.flush()

        entry = models.LedgerEntry(
            account_id=deposit.account_id,
            transaction_id=new_tx.id,
            entry_type=EntryType.CREDIT,
            amount=deposit.amount
        )
        db.add(entry)
    return {"message": "Deposit successful"}

@app.post("/withdrawals")
def withdraw_funds(withdrawal: schemas.WithdrawalRequest, db: Session = Depends(get_db)):
    if withdrawal.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        with db.begin():
            account = db.query(models.Account).filter(models.Account.id == withdrawal.account_id).with_for_update().first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")

            balance_query = text("""
                SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0)
                FROM ledger_entries WHERE account_id = :acc_id
            """)
            current_balance = db.execute(balance_query, {"acc_id": withdrawal.account_id}).scalar()
            
            if current_balance < withdrawal.amount:
                raise HTTPException(status_code=422, detail="Insufficient funds")

            new_tx = models.Transaction(type="WITHDRAWAL", description=withdrawal.description, status="COMPLETED")
            db.add(new_tx)
            db.flush()

            entry = models.LedgerEntry(
                account_id=withdrawal.account_id,
                transaction_id=new_tx.id,
                entry_type=EntryType.DEBIT,
                amount=withdrawal.amount
            )
            db.add(entry)
        return {"message": "Withdrawal successful"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transfers")
def execute_transfer(transfer: schemas.TransferRequest, db: Session = Depends(get_db)):
    if transfer.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    try:
        with db.begin():
            source_account = db.query(models.Account).filter(models.Account.id == transfer.source_account_id).with_for_update().first()
            if not source_account:
                raise HTTPException(status_code=404, detail="Source account not found")

            balance_query = text("""
                SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0)
                FROM ledger_entries WHERE account_id = :acc_id
            """)
            source_balance = db.execute(balance_query, {"acc_id": transfer.source_account_id}).scalar()
            
            if source_balance < transfer.amount:
                raise HTTPException(status_code=422, detail="Insufficient funds")

            new_tx = models.Transaction(type="TRANSFER", description=transfer.description, status="COMPLETED")
            db.add(new_tx)
            db.flush()

            debit_entry = models.LedgerEntry(
                account_id=transfer.source_account_id, transaction_id=new_tx.id,
                entry_type=EntryType.DEBIT, amount=transfer.amount
            )
            credit_entry = models.LedgerEntry(
                account_id=transfer.destination_account_id, transaction_id=new_tx.id,
                entry_type=EntryType.CREDIT, amount=transfer.amount
            )
            db.add_all([debit_entry, credit_entry])
        
        return {"message": "Transfer successful", "transaction_id": new_tx.id}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))