import pandas as pd
import requests
from datetime import datetime

###############################################
# CONFIGURATION
###############################################

# ---- MODE 1: Read logs from Excel (Active Now) ----
EXCEL_PATH = r"C:\Users\VParkavi\Downloads\Untitled discover search (1).csv"   # FIXED
# ---- MODE 2: Read from Elasticsearch (Commented Now) ----
ELASTIC_URL = "http://localhost:9200/logs-*/_search"
ELASTIC_USERNAME = "elastic"
ELASTIC_PASSWORD = "changeme"

# ---- ServiceNow Credentials ----
#"https://<instance>.service-now.com/api/now/table/incident"
SNOW_URL = "https://dev280340.service-now.com/api/now/table/incident"
SNOW_USER = "admin"
SNOW_PASS = "xvY74%IVbQk$"


###############################################
# UTILITY FUNCTIONS
###############################################

def detect_issue(log_message: str):
    """
    SRE Issue Detection — Pattern Based
    Matches payment-service log patterns
    """
    log_message = str(log_message).lower()

    patterns = {
        # ---- PAYMENT VALIDATION ERRORS ----
        "Invalid Amount": ["error_type=invalidamount"],
        "Duplicate Transaction": ["error_type=duplicatetransaction"],
        "Fraud Blocked": ["error_type=fraudblocked"],

        # ---- PAYMENT CRITICAL FAILURES ----
        "Random Failure": ["error_type=randomfail", "event=payment_failure"],

        # ---- GENERIC PAYMENT FAILURES ----
        "Payment Failure": ["payment failed", "transaction failed", "failed payment"],

        # ---- TIMEOUTS / NETWORK ----
        #"Timeout Error": ["timeout", "connection timed out"],

        # ---- INFRA (OPTIONAL) ----
        #"Service Down": ["service unavailable", "503", "service down"],
        #"Database Error": ["db error", "sql error", "connection refused"],
    }

    for issue_name, keywords in patterns.items():
        if any(k in log_message for k in keywords):
            return issue_name

    return None


def create_snow_ticket(short_desc, description):
    """
    Create ServiceNow Incident
    """
    payload = {
        "short_description": short_desc,
        "description": description,
        "urgency": "2",       # Medium
        "impact": "2",        # Medium
        "category": "Software"
    }

    response = requests.post(
        SNOW_URL,
        auth=(SNOW_USER, SNOW_PASS),
        json=payload
    )

    if response.status_code in [200, 201]:
        print("✔ ServiceNow Ticket CREATED")
        print("RAW RESPONSE:", response.text)  # Debug
    else:
        print("❌ Failed to create ticket:", response.status_code, response.text)



###############################################
# MODE 1 — READ LOGS FROM EXCEL (ACTIVE)
###############################################

def read_logs_from_excel():
    print("📁 Reading logs from Excel:", EXCEL_PATH)
    df = pd.read_csv(EXCEL_PATH)

    for index, row in df.iterrows():
        message = row.get("message") or row.get("event.original") or row.get("msg")
        timestamp = row.get("@timestamp")

        issue = detect_issue(message)

        if issue:
            print(f"\n🚨 Issue Detected: {issue}")
            print("Log Message:", message)

            description = f"""
Timestamp: {timestamp}
Detected Issue: {issue}
Log Message:
{message}
"""
            create_snow_ticket(issue, description)


###############################################
# MODE 2 — READ LOGS FROM ELASTICSEARCH (COMMENTED)
###############################################

def read_logs_from_elastic():
    print("🔄 Connecting to Elasticsearch...")

    query = {
        "size": 200,
        "_source": ["@timestamp", "message", "event.original", "msg"],
        "sort": [{"@timestamp": {"order": "desc"}}]
    }

    response = requests.get(
        ELASTIC_URL,
        auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD),
        json=query
    )

    hits = response.json()["hits"]["hits"]

    for hit in hits:
        source = hit["_source"]
        message = (
            source.get("message") or
            source.get("event.original") or
            source.get("msg")
        )
        timestamp = source.get("@timestamp")

        issue = detect_issue(message)

        if issue:
            print(f"\n🚨 Issue Detected: {issue}")
            print("Log Message:", message)

            description = f"""
Timestamp: {timestamp}
Detected Issue: {issue}
Log Message:
{message}
"""
            create_snow_ticket(issue, description)




if __name__ == "__main__":
    read_logs_from_excel()
    # read_logs_from_elastic()
