import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    print(">>> STARTING DEV SERVER (FLASK DEBUG)...")
    print(">>> URL: http://localhost:8080")
    print(">>> Auto-reload is ENABLED.")
    # Run in debug mode, monitoring all files in proper folders
    app.run(host='0.0.0.0', port=8080, debug=True)
