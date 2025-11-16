import requests
import time
import random

AUTH_URL = "http://localhost:8001"

USERS = ["alice", "bob", "john", "parkavi", "kumar"]

def simulate():
    while True:
        action = random.choice(["login_ok","login_fail","get_user","health"])

        if action == "login_ok":
            u = random.choice(USERS)
            requests.post(f"{AUTH_URL}/login", json={"username": u, "password":"x"})
            print("generated login_ok log")

        elif action == "login_fail":
            requests.post(f"{AUTH_URL}/login", json={"username": "", "password":"x"})
            print("generated login_fail log")

        elif action == "get_user":
            u = random.choice(USERS)
            requests.get(f"{AUTH_URL}/user/{u}")
            print("generated get_user log")

        else:
            requests.get(f"{AUTH_URL}/health")
            print("generated health log")

        time.sleep(2)  # generate every 2 sec

# if __name__ == "__main__":
#     simulate()
