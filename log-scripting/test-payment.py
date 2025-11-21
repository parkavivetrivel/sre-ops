import requests
import uuid
import time
import random

# Microservices
AUTH = "http://localhost:8001"
ORDERS = "http://localhost:8002"
PAYMENT = "http://localhost:8003"
NOTIFY = "http://localhost:8004"

BASE_PAYMENT = PAYMENT  # used for extra payment-only test cases

users = ["michel", "alex", "robert", "sneha", "james"]

# -----------------------------------------------------------------------------
# Helper for direct payment API testing
# -----------------------------------------------------------------------------
def run_payment_test(name, payload):
    print(f"\n=== PAYMENT TEST: {name} ===")
    try:
        # Login to get real trace-id and user-id so logs are correlated across services
        login_resp = requests.post(
            f"{AUTH}/login",
            json={"username": "direct-test-user", "password": "x"},
            headers={"Content-Type": "application/json"}
        )

        trace_id = login_resp.headers.get("x-trace-id")
        user_id = login_resp.headers.get("x-user-id")

        r = requests.post(
            f"{BASE_PAYMENT}/charge",
            json=payload,
            headers={
                "x-user-id": user_id or "direct-test-user",
                "x-trace-id": trace_id or f"test-{random.randint(1000,9999)}"
            }
        )
        print("Request:", payload)
        print("Response:", r.status_code, r.json())
    except Exception as e:
        print("Error:", e)


# -----------------------------------------------------------------------------
# RUN END-TO-END FLOW FOR EACH USER
# -----------------------------------------------------------------------------
for user in users:
    print("\n====== FLOW FOR USER:", user, "========")

    # login
    resp = requests.post(
        f"{AUTH}/login",
        json={"username": user, "password": "x"},
        headers={"Content-Type": "application/json"}
    )
    trace_id = resp.headers.get("x-trace-id")
    user_id = resp.headers.get("x-user-id")

    print("TRACE:", trace_id)

    headers = {
        "x-trace-id": trace_id,
        "x-user-id": user_id
    }

    # -------------------------------------------------------
    # 1️⃣ NORMAL TRANSACTION
    # -------------------------------------------------------
    order_id = f"o-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{ORDERS}/create",
        json={"id": order_id, "customer_id": user_id, "amount": 150.0},
        headers=headers
    )

    payment_id = f"p-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{PAYMENT}/charge",
        json={"id": payment_id, "order_id": order_id, "amount": 150.0},
        headers=headers
    )

    # notify
    requests.post(
        f"{NOTIFY}/send",
        json={"to": user_id, "message": f"order {order_id} done"},
        headers=headers
    )

    # -------------------------------------------------------
    # 2️⃣ INVALID AMOUNT TEST
    # -------------------------------------------------------
    bad_order_id = f"o-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{ORDERS}/create",
        json={"id": bad_order_id, "customer_id": user_id, "amount": 0},
        headers=headers
    )

    bad_payment_id = f"p-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{PAYMENT}/charge",
        json={"id": bad_payment_id, "order_id": bad_order_id, "amount": 0},
        headers=headers
    )

    # -------------------------------------------------------
    # 3️⃣ DUPLICATE TRANSACTION TEST
    # -------------------------------------------------------
    dup_order_id = f"o-{uuid.uuid4().hex[:6]}DUP"
    requests.post(
        f"{ORDERS}/create",
        json={"id": dup_order_id, "customer_id": user_id, "amount": 150.0},
        headers=headers
    )

    dup_payment_id = f"p-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{PAYMENT}/charge",
        json={"id": dup_payment_id, "order_id": dup_order_id, "amount": 150.0},
        headers=headers
    )

    # -------------------------------------------------------
    # 4️⃣ FRAUD TEST
    # -------------------------------------------------------
    fraud_order_id = f"o-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{ORDERS}/create",
        json={"id": fraud_order_id, "customer_id": user_id, "amount": 60000.0},
        headers=headers
    )

    fraud_payment_id = f"p-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{PAYMENT}/charge",
        json={"id": fraud_payment_id, "order_id": fraud_order_id, "amount": 60000.0},
        headers=headers
    )

    time.sleep(1)

# -----------------------------------------------------------------------------
# EXTRA PAYMENT TEST CASES (Direct payment API)
# -----------------------------------------------------------------------------

print("\n\n====================== EXTRA PAYMENT TEST CASES ======================\n")

# 1️⃣ Invalid amount
run_payment_test("Invalid Amount (Zero Payment)", {
    "id": "PAY001",
    "order_id": "ORDER_ZERO",
    "amount": 0
})

# 2️⃣ Duplicate order
run_payment_test("Duplicate Transaction", {
    "id": "PAY002",
    "order_id": "ORDER123DUP",
    "amount": 150
})

# 3️⃣ Fraud
run_payment_test("Fraud Block (High Amount)", {
    "id": "PAY003",
    "order_id": "ORDER_FRAUD",
    "amount": 99999
})

# 4️⃣ Successful payment
run_payment_test("Successful Payment", {
    "id": "PAY004",
    "order_id": "ORDER_SUCCESS",
    "amount": 499
})

# 5️⃣ Random failure attempts
print("\n=== Testing Simulated Random Payment Failure (10% chance) ===")
for i in range(10):
    run_payment_test(f"RandomFail Attempt {i+1}", {
        "id": f"PAY_FAIL_{i}",
        "order_id": f"ORDER_FAIL_{i}",
        "amount": 200
    })
    time.sleep(0.2)

# 6️⃣ Retry same payment ID
print("\n=== Testing SAME payment ID multiple times ===")
retry_payload = {
    "id": "PAY777",
    "order_id": "ORDER777",
    "amount": 300
}
for i in range(5):
    run_payment_test(f"Retry #{i+1}", retry_payload)
    time.sleep(0.2)


# -----------------------------------------------------------------------------
# FETCH LOGS
# -----------------------------------------------------------------------------
print("\n========= FETCH LAST LOGS FOR ALL SERVICES =========")

for name, url in {
    "AUTH": AUTH,
    "ORDERS": ORDERS,
    "PAYMENT": PAYMENT,
    "NOTIFY": NOTIFY
}.items():
    print("\n---", name, "---")
    try:
        logs = requests.get(f"{url}/logs?lines=50").json()
        for l in logs.get("logs", []):
            print(l)
    except Exception as e:
        print(f"Failed to fetch logs from {name}: {e}")

print("\n🎉 All scenarios executed successfully!")
