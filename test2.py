from pathlib import Path
from datetime import datetime
import json
from mongo_uri_test import find_doc, find_doc_by_id

def datetime_handler(obj):
    if isinstance(obj, datetime):
        return {"$date": obj.isoformat() + "Z"}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

paths = list(Path('.').glob('transliterated_non_retrieval/*.json'))
global_count = 0
global_count_1 = 0

for path in paths:
    print(f"Processing file: {path}")
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    for conv in data:
        # messages = []
        # for msg in conv['messages']:
        #     new_message = {
        #         'role': msg.get('role'),
        #         'content': msg.get('content'),
        #         'en': msg.get('en'),
        #         'timestamp': msg.get('timestamp')
        #     }
        #     messages.append(new_message)
        
        # corr_doc = find_doc(messages)
        corr_doc = find_doc_by_id(conv['_id'] if '_id' in conv else None)
        if corr_doc:
            conv['_id'] = corr_doc.get('_id')
            conv['language'] = corr_doc.get('language')
            conv['expiry'] = corr_doc.get('expiry')
            global_count_1 += 1
        else:
            global_count += 1

    # Create new path for output file
    # output_path = str(path.resolve()).replace('messages.modified.json', 'messages.modified_2.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=datetime_handler)

print(f"\n\nnumber of id not found: {global_count}")
print(f"\nnumber of id found: {global_count_1}")