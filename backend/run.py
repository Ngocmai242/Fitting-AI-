from app import create_app

app = create_app()

if __name__ == '__main__':
    print(">>> Starting AuraFit Server on Port 5050...")
    app.run(debug=True, port=5050, host='0.0.0.0')
