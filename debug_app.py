print("Python is working")
import flask
print(f"Flask version: {flask.__version__}")
try:
    import sys
    import os
    sys.path.append(os.path.abspath('backend'))
    from app import create_app
    print("App import successful")
    app = create_app()
    print("App creation successful")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
