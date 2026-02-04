#!/bin/bash
# Install dependencies
pip install -r backend/requirements.txt

# Start Backend
echo "Starting AuraFit Backend..."
python backend/run.py &

# Note: In Codespaces, use the 'Live Server' extension for the frontend.
echo "Backend started. Please use Live Server to open frontend/index.html"
