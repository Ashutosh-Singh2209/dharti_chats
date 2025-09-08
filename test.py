import json
import os

with open('chat_database.conversations 1.json', 'r') as f:
    dict_obj = json.load(f)

ids = []
for obj in dict_obj:
    _id = obj.get('_id').replace("/", "_")
    os.makedirs(_id, exist_ok=True)
    file_path = os.path.join(_id, "messages.json")
    with open(file_path, "w") as f: json.dump(obj.get("msgs"), f, indent=4,\
                                              ensure_ascii=False)

print(ids)