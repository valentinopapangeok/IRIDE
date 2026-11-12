import os
from pathlib import Path

def print_tree(startpath, prefix=""):
    items = sorted(os.listdir(startpath))
    for i, item in enumerate(items):
        path = os.path.join(startpath, item)
        connector = "└── " if i == len(items) - 1 else "├── "
        print(prefix + connector + item)
        if os.path.isdir(path):
            extension = "    " if i == len(items) - 1 else "│   "
            print_tree(path, prefix + extension)

# Base folder where your structure starts
base_folder = Path(__file__).resolve().parents[2]

print(os.path.basename(base_folder) + "/")
print_tree(base_folder)
