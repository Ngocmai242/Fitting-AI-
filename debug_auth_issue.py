
import requests
import json

BASE_URL = "http://localhost:8080/api"

def debug_auth():
    username = "debugUser123"
    password = "pass123"
    email = "debugUser123@example.com"
    
    # 1. Register
    print(f"Registering user: {username}")
    reg_payload = {
        "username": username,
        "email": email,
        "password": password,
        "phone": "1234567890"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/register", json=reg_payload)
        print(f"Registration Status: {resp.status_code}")
        print(f"Registration Response: {resp.text}")
    except Exception as e:
        print(f"Registration Failed: {e}")
        return

    # 2. Login
    print(f"\nLogging in user: {username}")
    login_payload = {
        "login_input": username,
        "password": password
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/login", json=login_payload)
        print(f"Login Status: {resp.status_code}")
        print(f"Login Response: {resp.text}")
        
        if resp.status_code == 200:
            print("LOGIN SUCCESS!")
        else:
            print("LOGIN FAILED!")
            
    except Exception as e:
        print(f"Login Failed: {e}")

if __name__ == "__main__":
    debug_auth()
