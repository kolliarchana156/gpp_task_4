
```markdown
# 🏦 Robust Financial Ledger API

A high-integrity, double-entry bookkeeping system built with **FastAPI** and **SQLAlchemy**. This service acts as a "Single Source of Truth" for financial transactions, prioritizing correctness, auditability, and absolute data integrity.

---

## 🛠️ Project Setup

### 1. Prerequisites
* **Python 3.10+**
* **PostgreSQL** (Recommended) or **SQLite** (for quick local testing).

### 2. Local Installation
1. **Initialize Virtual Environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate # Mac/Linux

```

2. **Install Dependencies:**
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic

```


3. **Run the Application:**
```bash
uvicorn main:app --reload

```


Access the API docs at `http://127.0.0.1:8000/docs`

---

## 🏗️ Design Decisions & Architecture

### 1. Double-Entry Bookkeeping Model

We implemented a **strictly decoupled ledger model**.

* **Calculated Balances:** Accounts do **not** store a balance column. This prevents "data drift" where a stored balance might mismatch the transaction history.
* **Dual Entries:** Every transfer creates exactly **two** ledger entries: a `DEBIT` from the source and a `CREDIT` to the destination.
* **Audit Trail:** The `ledger_entries` table is the "Source of Truth."

### 2. ACID Properties & Transaction Strategy

To guarantee the **Atomicity, Consistency, Isolation, and Durability** of financial data:

* **Atomicity:** All operations (Transaction record + two Ledger entries) are wrapped in a SQLAlchemy `with db.begin():` block. If any insert fails, the entire unit of work is rolled back.
* **Durability:** Ledger entries are **immutable** and append-only. Once written, they are never updated or deleted.

### 3. Transaction Isolation & Concurrency

* **Rationale:** In a banking environment, concurrent transfers could lead to a user spending the same dollar twice (the "Race Condition").
* **Implementation:** We utilize **Pessimistic Locking** (`.with_for_update()`). When a transfer starts, the database locks the source account row. Any other request for that account must wait until the current transaction commits. This enforces a strict queue for balance updates.

### 4. Balance Calculation & Negative Prevention

* **Real-time Summation:** Balance is calculated on-the-fly using:
`SUM(Credits) - SUM(Debits)`.
* **Overdraft Prevention:** Before committing, the system calculates the projected balance within the locked transaction. If the resulting balance would be negative, the system raises a `422 Unprocessable Entity` error and triggers a database **ROLLBACK**.

---

## 🚦 API Reference

| Endpoint | Description |
| --- | --- |
| `POST /accounts` | Create a new account (Checking/Savings). |
| `GET /accounts/{id}` | Calculate current balance from ledger history. |
| `POST /transfers` | Atomic double-entry transfer between two accounts. |
| `POST /deposits` | Simulate external funds entering the system. |
| `GET /accounts/{id}/ledger` | Return the immutable chronological audit trail. |
| `GET /audit/integrity-check` | Perform a system-wide trial balance verification. |

---

## 🧪 Testing Integrity

To verify the system's robustness against race conditions, run the included concurrency test:

```bash
python test_ledger.py

```