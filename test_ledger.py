import requests
from concurrent.futures import ThreadPoolExecutor

# Update this if your port is different
BASE_URL = "http://127.0.0.1:8000"

def run_concurrency_test():
    print("🚀 Starting Concurrency Integrity Test...")

    # 1. Create a Source Account
    source_acc = requests.post(f"{BASE_URL}/accounts", json={
        "user_id": "sender_001", "account_type": "checking"
    }).json()
    source_id = source_acc["id"]

    # 2. Create a Destination Account
    dest_acc = requests.post(f"{BASE_URL}/accounts", json={
        "user_id": "receiver_001", "account_type": "savings"
    }).json()
    dest_id = dest_acc["id"]

    # 3. Deposit exactly $100 into Source
    requests.post(f"{BASE_URL}/deposits", json={
        "account_id": source_id, "amount": 100, "description": "Test Funding"
    })
    print(f"✅ Created accounts and deposited $100 into {source_id}")

    # 4. Define a function to attempt a $20 transfer
    def attempt_transfer():
        return requests.post(f"{BASE_URL}/transfers", json={
            "source_account_id": source_id,
            "destination_account_id": dest_id,
            "amount": 20
        })

    # 5. Run 10 transfers at the EXACT same time (Total requested = $200)
    # Since we only have $100, exactly 5 should succeed and 5 should fail.
    print("⏳ Executing 10 simultaneous $20 transfers (Race Condition Simulation)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(lambda f: attempt_transfer(), range(10)))

    # 6. Verify Results
    success = [r for r in responses if r.status_code == 200]
    failed = [r for r in responses if r.status_code == 422]

    print("\n--- Test Results ---")
    print(f"Successful Transfers: {len(success)} (Should be 5)")
    print(f"Rejected Transfers:   {len(failed)} (Should be 5)")

    # 7. Final Balance Check
    final_balance = requests.get(f"{BASE_URL}/accounts/{source_id}").json()["balance"]
    print(f"Final Balance: ${final_balance} (Should be $0.00)")

    if len(success) == 5 and float(final_balance) == 0:
        print("\n✅ PASSED: ACID Isolation and Row-Level Locking are working perfectly!")
    else:
        print("\n❌ FAILED: Data integrity issue detected.")

if __name__ == "__main__":
    try:
        run_concurrency_test()
    except Exception as e:
        print(f"❌ Error: Make sure your FastAPI server is running at {BASE_URL}")