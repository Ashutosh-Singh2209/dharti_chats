import os
import glob
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv("../.env")

client = MongoClient(os.getenv("FYLLO_MONGO_URI"))
db = client["chat_database"]
collection = db["conversations"]

def convert_dates(obj):
    if isinstance(obj, dict):
        if "$date" in obj and isinstance(obj["$date"], str):
            return datetime.strptime(obj["$date"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        else:
            return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(i) for i in obj]
    else:
        return obj

def find_doc(messages_value):
    messages_value2 = convert_dates(messages_value)
    doc = collection.find_one({"messages": messages_value2})
    return doc

def create_non_retrieval_folder():
    folder_name = "non_retrieval"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}")
    else:
        print(f"Folder already exists: {folder_name}")
    return folder_name

def find_modified_json_files(root_dir="."):
    pattern = os.path.join(root_dir, "**", "messages.modified.json")
    paths = glob.glob(pattern, recursive=True)
    return paths

def has_empty_retrieval(message):
    if message.get("role") == "user" and "retrieval" in message:
        retrieval = message["retrieval"]
        tools = retrieval.get("tools", [])
        faq = retrieval.get("faq", [])
        return len(tools) == 0 and len(faq) == 0
    return False

def should_filter_conversation(farmer_id, messages):
    excluded_farmers = ['priyanshu', 'chaitanyarajwade', 'popatganore', "sinankit"]
    if farmer_id in excluded_farmers:
        return True
    
    # conv_doc = find_doc(messages)
    # if not conv_doc:
    #     return True
    
    # roles = conv_doc.get("roles")
    # if not roles or "farmuser" not in roles:
    #     return True
    
    # if "admin" in roles:
    #     return True
    
    return False

def separate_non_retrieval_objects():
    output_folder = create_non_retrieval_folder()
    file_paths = find_modified_json_files()
    total_separated = 0
    total_filtered_by_farmer = 0
    total_filtered_by_roles = 0
    total_objects = 0
    for path in file_paths:
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            total_objects += len(data)
            non_retrieval_objects = []
            
            if isinstance(data, list):
                for obj in data:
                    if "messages" in obj:
                        farmer_id = obj.get("farmer_id", "")
                        messages = obj["messages"]
                        
                        if should_filter_conversation(farmer_id, messages):
                            continue
                        
                        
                        has_empty_retrieval_user = False
                        for message in messages:
                            if has_empty_retrieval(message):
                                has_empty_retrieval_user = True
                                break
                        
                        if has_empty_retrieval_user:
                            non_retrieval_objects.append(obj)
            
            if non_retrieval_objects:
                folder_name = os.path.basename(os.path.dirname(path))
                file_name = os.path.splitext(os.path.basename(path))[0]
                output_filename = f"{folder_name}_{file_name}.json"
                output_path = os.path.join(output_folder, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    json.dump(non_retrieval_objects, output_file, indent=2, ensure_ascii=False)
                
                print(f"Separated {len(non_retrieval_objects)} objects from {path}")
                print(f"Saved to: {output_path}")
                total_separated += len(non_retrieval_objects)
            else:
                print(f"No non-retrieval objects found in {path}")
                
        except Exception as e:
            print(f"Error processing {path}: {str(e)}")
    
    print(f"\nFiltering Summary:")
    # print(f"Total objects filtered by farmer_id: {total_filtered_by_farmer}")
    # print(f"Total objects filtered by roles: {total_filtered_by_roles}")
    print(f"Total objects separated: {total_separated} out of {total_objects}")
    return total_separated

if __name__ == "__main__":
    separate_non_retrieval_objects()
