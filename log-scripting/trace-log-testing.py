import requests
import uuid
import time

AUTH = "http://localhost:8001"
ORDERS = "http://localhost:8002"
PAYMENT = "http://localhost:8003"
NOTIFY = "http://localhost:8004"

users = ["parkavi", "alex", "rahul", "sneha", "james"]

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

    # create order
    order_id = f"o-{uuid.uuid4().hex[:6]}"
    requests.post(
        f"{ORDERS}/create",
        json={"id": order_id, "customer_id": user_id, "amount": 150.0},
        headers=headers
    )

    # charge
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

    time.sleep(1)  # small delay to make logs cleaner

print("\n========= FETCH LAST LOGS FOR ALL SERVICES =========")

for name, url in {
    "AUTH": AUTH,
    "ORDERS": ORDERS,
    "PAYMENT": PAYMENT,
    "NOTIFY": NOTIFY
}.items():
    print("\n---", name, "---")
    logs = requests.get(f"{url}/logs?lines=50").json()
    for l in logs.get("logs", []):
        print(l)
