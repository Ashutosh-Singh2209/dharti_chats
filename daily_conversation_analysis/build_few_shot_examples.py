#!/usr/bin/env python3
# python3 -m daily_conversation_analysis.build_few_shot_examples

"""
Build Few-Shot Examples from Historical Conversations

This script reads all conversation files from November 20, 2025 up to 1 day before yesterday,
extracts user messages that have been tagged with the 'is_query_common' classification,
and builds a comprehensive few-shot examples file for the message classifier.

The script:
1. Scans all conversation JSON files within the specified date range
2. Extracts user messages that have 'is_query_common' field (tagged as common or uncommon)
3. Maintains uniqueness by tracking message content in a set
4. Rebuilds the few_shot_examples.json file from scratch each run
5. Preserves the required JSON structure with conversation_id, user_message_index, input, and output

Usage:
    python3 -m daily_conversation_analysis.build_few_shot_examples
"""

import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tqdm import tqdm


def build_few_shot_examples():
    """Build few-shot examples from historical conversation files."""
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Calculate date range: from Nov 19, 2025 to 1 day before yesterday
    start_date = datetime(2025, 11, 19, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)
    end_date = yesterday_utc - timedelta(days=1)  # 1 day before yesterday
    end_date = datetime(2025, 11, 22, tzinfo=timezone.utc)
    
    print(f"Building few-shot examples from {start_date.date()} to {end_date.date()}")
    
    # Collect all conversation files in the date range
    conversation_files = []
    current_date = start_date
    
    while current_date <= end_date:
        folder_name = current_date.strftime("%d_%b_%Y")
        conversations_path = os.path.join(script_dir, folder_name, "conversations.json")
        
        if os.path.exists(conversations_path):
            conversation_files.append(conversations_path)
            print(f"Found: {folder_name}/conversations.json")
        
        current_date += timedelta(days=1)
    
    if not conversation_files:
        print("No conversation files found in the specified date range.")
        return
    
    print(f"\nProcessing {len(conversation_files)} conversation files...")
    
    # Track unique messages and build examples
    seen_messages = set()
    few_shot_examples = []
    
    # Process each conversation file
    for file_path in tqdm(conversation_files, desc="Processing files", unit="file"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                conversations = json.load(f)
            
            # Process each conversation
            for conv in conversations:
                conversation_id = conv.get("_id", "unknown")
                messages = conv.get("messages", [])
                
                # Track user message index for this conversation
                user_msg_idx = -1
                
                # Process each message
                for msg in messages:
                    role = msg.get("role")
                    
                    if role == "user":
                        user_msg_idx += 1
                        
                        content = msg.get("content", "").strip()
                        is_common = msg.get("is_query_common")
                        
                        # Skip if message is empty or already seen
                        if not content or content in seen_messages:
                            continue
                        
                        # Add to few-shot examples
                        # Treat missing or null is_query_common as uncommon
                        seen_messages.add(content)
                        few_shot_examples.append({
                            "conversation_id": conversation_id,
                            "user_message_index": user_msg_idx,
                            "input": content,
                            "output": "common" if is_common is True else "uncommon"
                        })
        
        except Exception as e:
            print(f"\nError processing {file_path}: {e}")
            continue
    
    # Save few-shot examples
    few_shot_path = os.path.join(script_dir, "few_shot_examples", "few_shot_examples.json")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(few_shot_path), exist_ok=True)
    
    # Write the few-shot examples file
    with open(few_shot_path, "w", encoding="utf-8") as f:
        json.dump(few_shot_examples, f, ensure_ascii=False, indent=4)
    
    print(f"\n✓ Built {len(few_shot_examples)} unique few-shot examples")
    print(f"✓ Saved to: {few_shot_path}")
    
    # Print distribution
    common_count = sum(1 for ex in few_shot_examples if ex["output"] == "common")
    uncommon_count = len(few_shot_examples) - common_count
    print(f"\nDistribution:")
    print(f"  Common: {common_count}")
    print(f"  Uncommon: {uncommon_count}")


if __name__ == "__main__":
    build_few_shot_examples()
