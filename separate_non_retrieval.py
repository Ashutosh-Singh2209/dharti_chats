import os
import glob
import json

def find_modified_json_files(root_dir="."):
    pattern = os.path.join(root_dir, "**", "messages.modified.json")
    paths = glob.glob(pattern, recursive=True)
    return paths

def count_json_objects():
    file_paths = find_modified_json_files()
    total_objects = 0
    
    for path in file_paths:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = 1
                else:
                    count = 0
                print(f"{path}: {count} objects")
                total_objects += count
        except Exception as e:
            print(f"Error reading {path}: {str(e)}")
    
    return total_objects

total = count_json_objects()
print(f"\nTotal number of JSON objects across all files: {total}")