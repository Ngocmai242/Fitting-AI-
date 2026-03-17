
import re

with open(r'c:\Mai\4\backend\app\routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'print(' in line:
        # Check if line contains non-ascii
        if any(ord(c) > 127 for c in line):
            print(f"Line {i+1}: {line.strip()}")
