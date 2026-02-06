from app import create_app

app = create_app()

if __name__ == '__main__':
    try:
        print(">>> Starting AuraFit Server on Port 8080 (Local Only)...")
        # Bind to 0.0.0.0 to ensure accessibility
        # Changed port to 8080 to match production server and frontend config
        app.run(debug=False, port=8080, host='0.0.0.0')
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to start server: {e}")
        input("Press Enter to exit...")
