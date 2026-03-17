
import os

repo_root = r'C:\Mai\4\backend'

for root, dirs, files in os.walk(repo_root):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if 'print(' in line and any(ord(c) > 127 for c in line):
                            print(f"{path} Line {i+1}: {line.strip()}")
            except Exception:
                pass
