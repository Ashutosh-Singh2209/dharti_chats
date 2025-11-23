# python3 -m daily_conversation_analysis.fetch_conversations

import os
import asyncio
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import json
from bson import json_util
import time
import sys
from tqdm import tqdm

# Add specific paths to allow imports
# Structure:
# .../fyllo/dharti_chats/daily_conversation_analysis/fetch_conversations.py
# .../fyllo/new_pull/fyllo-ai/bot_core/

# Save the original working directory
original_cwd = os.getcwd()

# Get the fyllo directory (parent of dharti_chats)
current_dir = os.path.dirname(os.path.abspath(__file__))  # daily_conversation_analysis
script_dir = current_dir  # Store original script directory for output paths
dharti_chats_dir = os.path.dirname(current_dir)  # dharti_chats
fyllo_dir = os.path.dirname(dharti_chats_dir)  # fyllo

# Path to fyllo-ai which contains bot_core
fyllo_ai_path = os.path.join(fyllo_dir, "new_pull", "fyllo-ai")

# Add fyllo-ai to sys.path so we can import bot_core
if fyllo_ai_path not in sys.path:
    sys.path.insert(0, fyllo_ai_path)

# Temporarily change working directory to fyllo-ai for imports
os.chdir(fyllo_ai_path)

print(f"Added to sys.path: {fyllo_ai_path}")
print(f"Temporarily changed to: {fyllo_ai_path}")

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from bot_core.farmer_info import get_farmer_info_2
from bot_core.standalone_query_examples import extract_farmer_context_for_prompt
from bot_core.embed import Embedder
from langchain_core.messages import HumanMessage, AIMessage

# Restore original working directory
os.chdir(original_cwd)
print(f"Restored working directory to: {original_cwd}")
print(f"Output will be saved to: {script_dir}")

def get_mongo_client():
    mongo_uri = os.getenv("FYLLO_MONGO_URI")
    if not mongo_uri:
        raise ValueError("FYLLO_MONGO_URI environment variable not set")
    return MongoClient(mongo_uri)

def process_conversation(conversation, embedder):
    """
    Process a single conversation: fetch farmer info, preprocess it, 
    and generate standalone questions for user messages.
    
    Skips standalone question generation if it already exists.
    """
    try:
        # Extract necessary details from conversation (actual JSON structure)
        farmer_id = conversation.get("farmer_id")
        farmer_name = conversation.get("farmer_name", "Unknown")
        gender = conversation.get("gender", "Male")
        language = conversation.get("language", "en")
        
        # Extract plot_ids from farmer_plot_ids array
        plot_ids = conversation.get("farmer_plot_ids", [])
        
        print(f"Processing conversation for farmer: {farmer_name} ({farmer_id})")

        # Fetch fresh farmer info (using asyncio.run for sync context)
        import asyncio
        farmer_info = asyncio.run(get_farmer_info_2(
            farmer_name=farmer_name,
            gender=gender,
            lang=language,
            plot_ids=plot_ids,
            get_next_stages=True
        ))
        
        # Preprocess farmer info
        processed_farmer_info = extract_farmer_context_for_prompt(farmer_info)
        # conversation["processed_farmer_info"] = processed_farmer_info
        
        # Process messages for standalone questions
        messages = conversation.get("messages", [])
        chat_history = [] 
        
        standalone_generated = 0
        standalone_skipped = 0
        
        for msg in messages:
            role = msg.get("type") or msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                # Skip if standalone question already exists or if there was a previous error
                if "standalone_question" in msg:
                    standalone_skipped += 1
                    print(f"  Skipping standalone question (already exists)")
                elif "standalone_question_error" in msg:
                    standalone_skipped += 1
                    print(f"  Skipping standalone question (previous error)")
                else:
                    # Generate standalone question
                    try:
                        standalone_question = embedder.generate_standalone_question(
                            query=content,
                            conversational_history=chat_history,
                            language_code=language,
                            FarmInfo=processed_farmer_info
                        )
                        msg["standalone_question"] = standalone_question
                        standalone_generated += 1
                        time.sleep(1)
                    except Exception as e:
                        print(f"Error generating standalone question: {e}")
                        msg["standalone_question_error"] = ""
                
                # Add to history
                chat_history.append(HumanMessage(content=content))
                
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        
        print(f"  Generated {standalone_generated} standalone questions, skipped {standalone_skipped}")

    except Exception as e:
        print(f"Error processing conversation: {e}")
        conversation["processing_error"] = str(e)

def fetch_and_process_conversations():
    client = get_mongo_client()
    db = client["chat_database"]
    collection = db["conversations"]

    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)
    
    start_of_day = yesterday_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now_utc

    print(f"Fetching conversations for: {start_of_day.date()}")
    print(f"Time range (UTC): {start_of_day} to {end_of_day}")

    folder_date_str = start_of_day.strftime("%d_%b_%Y")
    output_dir = os.path.join(script_dir, folder_date_str)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "conversations.json")

    # Check if file already exists
    if os.path.exists(output_file):
        print(f"Found existing file: {output_file}")
        print("Loading existing conversations from file...")
        with open(output_file, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        print(f"Loaded {len(conversations)} conversations from file.")
    else:
        print("No existing file found. Fetching from database...")
        query = {
            "messages.timestamp": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }

        cursor = collection.find(query, {"chat_state": 0})
        conversations = list(cursor)
        
        print(f"Found {len(conversations)} conversations from database.")

        if not conversations:
            print("No conversations found for yesterday.")
            return

    # Initialize Embedder once
    print("Initializing Embedder...")
    embedder = Embedder()
    print("Embedder initialized.")

    # Process conversations sequentially
    for conv in conversations:
        process_conversation(conv, embedder)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"Saved conversations to: {output_file}")

def transliterate_conversations(json_path: str) -> None:
    """Read a conversations JSON file, transliterate each message, and save back.

    The function loads the JSON file, iterates over each conversation's
    messages list and adds a new key 'content_transliterated' containing the
    transliteration of the original content using Azure's transliteration API.
    
    Skips messages that already have 'content_transliterated'.

    Args:
        json_path: Absolute path to the conversations.json file.
    """
    from pathlib import Path
    from azure_transliterate_non_retrieval import transliterate_text

    path = Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"Conversations file not found: {json_path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    total_messages = 0
    total_transliterated = 0
    total_skipped_existing = 0

    for conv_idx, conv in enumerate(data):
        messages = conv.get("messages", [])
        for msg_idx, msg in enumerate(messages):
            original = msg.get("content", "")
            if original and original.strip():
                total_messages += 1
                
                # Skip if already transliterated or if there was a previous error
                if "content_transliterated" in msg:
                    total_skipped_existing += 1
                    print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Skipped (already transliterated)")
                    continue
                
                if "transliteration_error" in msg:
                    total_skipped_existing += 1
                    print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Skipped (previous error)")
                    continue
                
                try:
                    transliterated = transliterate_text(original)
                    time.sleep(1)
                    if transliterated and transliterated != original:
                        msg["content_transliterated"] = transliterated
                        total_transliterated += 1
                        print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Transliterated")
                    elif transliterated is None:
                        print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Skipped (English/unsupported)")
                except Exception as e:
                    msg["transliteration_error"] = ""
                    print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Error - {e}")

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nCompleted: {total_transliterated}/{total_messages} messages transliterated")
    print(f"Skipped {total_skipped_existing} messages (already transliterated)")
    print(f"Saved to: {json_path}")

def classify_user_messages(json_path: str) -> None:
    """Read conversations JSON file, classify user messages, and save back.
    
    The function loads the JSON file, iterates over each conversation,
    collects all user messages, uses classify_messages to get classifications,
    and stores the results back in the conversation's user messages objects.
    
    Saves after processing each conversation. Skips conversations where all
    user messages are already tagged. Skips individual messages that are already tagged.
    
    Args:
        json_path: Absolute path to the conversations.json file.
    """
    from pathlib import Path
    from daily_conversation_analysis.google_gai_message_classifier import classify_messages
    
    path = Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"Conversations file not found: {json_path}")
    
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"\nClassifying user messages in {len(data)} conversations...")
    
    # Process each conversation with progress bar
    for conv_idx in tqdm(range(len(data)), desc="Classifying conversations", unit="conv"):
        conv = data[conv_idx]
        messages = conv.get("messages", [])
        
        # Collect user messages that need classification
        user_messages_to_classify = []
        user_message_indices = []
        
        for msg_idx, msg in enumerate(messages):
            role = msg.get("type") or msg.get("role")
            if role == "user":
                # Skip if already classified or if there was a previous error
                # if "is_query_common" in msg:
                #     continue
                # elif "is_query_common_error" in msg:
                #     continue
                # else:
                    content = msg.get("content", "")
                    if content and content.strip():
                        user_messages_to_classify.append(content)
                        user_message_indices.append(msg_idx)
        
        # Skip this conversation if no messages need classification
        if not user_messages_to_classify:
            continue
        
        # Classify the batch of user messages
        try:
            classifications = classify_messages(user_messages_to_classify)
            
            # Store classifications back in the message objects
            # Convert "common"/"uncommon" to boolean (True if common, False if uncommon)
            for i, msg_idx in enumerate(user_message_indices):
                messages[msg_idx]["is_query_common"] = (classifications[i] == "common")
            
            # Save after processing each conversation
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"\n  Conv {conv_idx+1}: Classification error - {e}")
            # Mark messages with error
            for msg_idx in user_message_indices:
                messages[msg_idx]["is_query_common_error"] = str(e)
    
    print(f"\nCompleted classification.")
    print(f"Results saved to: {json_path}")

if __name__ == "__main__":
    # fetch_and_process_conversations()
    
    # # Transliterate and classify the fetched conversations
    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)
    # yesterday_utc = yesterday_utc - timedelta(days=1)
    print(f"\nYesterday UTC: {yesterday_utc}\n")
    folder_date_str = yesterday_utc.strftime("%d_%b_%Y")
    output_dir = os.path.join(os.path.dirname(__file__), folder_date_str)
    json_path = os.path.join(output_dir, "conversations.json")
    print(f"\nJSON Path: {json_path}\n")
    
    if os.path.exists(json_path):
        # print(f"\nStarting transliteration for {json_path}...")
        # transliterate_conversations(json_path)
        print(f"\nStarting classification for {json_path}...")
        classify_user_messages(json_path)
    else:
        print(f"No conversations file found at {json_path}")


