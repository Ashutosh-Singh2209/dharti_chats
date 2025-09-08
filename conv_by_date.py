import json
import os
from datetime import datetime
from collections import defaultdict

def process_conversations():
    input_file = 'conversations_sorted_by_date.json'
    output_folder = 'conversations_by_date'
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    date_conversations = defaultdict(list)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        conversations = json.load(f)
        
    for conv in conversations:
        if 'conv_date' in conv:
            date_str = conv['conv_date'].split('T')[0]
            date_conversations[date_str].append(conv)
    
    for date, convs in date_conversations.items():
        output_file = os.path.join(output_folder, f'conversations_{date}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(convs, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    process_conversations()