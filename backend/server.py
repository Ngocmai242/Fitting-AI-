from app import create_app
from waitress import serve
import os

app = create_app()

if __name__ == '__main__':
    print(">>> STARTING PRODUCTION SERVER (WAITRESS)...")
    print(">>> URL: http://localhost:8080 or http://127.0.0.1:8080")
    print(">>> Press Ctrl+C to stop.")
    # Run on port 8080, valid for all interfaces (0.0.0.0) to fix 'localhost' connection refused issues
    serve(app, host='0.0.0.0', port=8080)
