
import requests
import json
import time

BASE_URL = "http://localhost:8080/api"

def verify_fix():
    username = " spacedUser "
    clean_username = "spacedUser"
    password = " password123 "
    clean_password = "password123"
    email = " spaced@example.com "
    clean_email = "spaced@example.com"
    
    # 1. Register with spaces
    print(f"Registering user with spaces: '{username}'")
    reg_payload = {
        "username": username,
        "email": email,
        "password": password,
        "phone": " 1234567890 ",
        "role": "USER"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/register", json=reg_payload)
        print(f"Registration Status: {resp.status_code}")
        print(f"Registration Response: {resp.text}")
    except Exception as e:
        print(f"Registration Failed: {e}")
        return

    # 2. Login with clean inputs (simulating trimmed inputs from frontend or user typing correctly)
    print(f"\nLogging in user: '{clean_username}' with password '{clean_password}'")
    login_payload = {
        "login_input": clean_username,
        "password": clean_password
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/login", json=login_payload)
        print(f"Login Status: {resp.status_code}")
        print(f"Login Response: {resp.text}")
        
        if resp.status_code == 200:
            print("✅ LOGIN SUCCESS! Fix Verified.")
            data = resp.json()
            if data['username'] == clean_username and data['email'] == clean_email:
                print("✅ Username and Email stored without spaces.")
            else:
                print(f"❌ Username/Email still has spaces: '{data['username']}'")
        else:
            print("❌ LOGIN FAILED!")
            
    except Exception as e:
        print(f"Login Failed: {e}")

if __name__ == "__main__":
    time.sleep(5) # Wait for server to start
    verify_fix()
