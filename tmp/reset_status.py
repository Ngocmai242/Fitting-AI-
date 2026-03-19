import sqlite3
import os
import sys

# Add project root to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

db_path = os.path.join(_project_root, "database", "database_v2.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Reset status of normalized_products to pending for test
cur.execute("UPDATE normalized_products SET status = 'pending' WHERE id = 100")
conn.commit()
conn.close()
print("Reset product 100 to pending.")
