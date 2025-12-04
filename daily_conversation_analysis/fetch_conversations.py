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
from collections import Counter

original_cwd = os.getcwd()

current_dir = os.path.dirname(os.path.abspath(__file__))
script_dir = current_dir
dharti_chats_dir = os.path.dirname(current_dir)
fyllo_dir = os.path.dirname(dharti_chats_dir)

fyllo_ai_path = os.path.join(fyllo_dir, "new_pull", "fyllo-ai")

if fyllo_ai_path not in sys.path:
    sys.path.insert(0, fyllo_ai_path)

os.chdir(fyllo_ai_path)

print(f"Added to sys.path: {fyllo_ai_path}")
print(f"Temporarily changed to: {fyllo_ai_path}")

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from bot_core.farmer_info import get_farmer_info_2
from bot_core.standalone_query_examples import extract_farmer_context_for_prompt
from bot_core.embed import Embedder
from langchain_core.messages import HumanMessage, AIMessage
from pathlib import Path
from daily_conversation_analysis.google_gai_message_classifier import classify_messages as classify_messages_gai, normalize_question_counts
from daily_conversation_analysis.openai_message_classifier import classify_messages
from daily_conversation_analysis.build_few_shot_examples import build_few_shot_examples
from azure_transliterate_non_retrieval import transliterate_text

os.chdir(original_cwd)
print(f"Restored working directory to: {original_cwd}")
print(f"Output will be saved to: {script_dir}")

start_date_time = None
end_date_time = None
folder_date_str = None
output_dir = None
json_path = None

def set_date_range():
    global start_date_time, end_date_time, folder_date_str, output_dir, json_path
    start_date_time = datetime.now() - timedelta(days=1)
    start_date_time = start_date_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date_time = start_date_time.replace(hour=23, minute=59, second=59, microsecond=0)
    
    folder_date_str = start_date_time.strftime("%d_%b_%Y")
    output_dir = os.path.join(script_dir, folder_date_str)
    json_path = os.path.join(output_dir, "conversations.json")
    
    print(f"\nDate range: {start_date_time} to {end_date_time}")
    print(f"Folder date string: {folder_date_str}")
    print(f"Output directory: {output_dir}")
    print(f"JSON path: {json_path}\n")

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
        farmer_id = conversation.get("farmer_id")
        farmer_name = conversation.get("farmer_name", "Unknown")
        gender = conversation.get("gender", "Male")
        language = conversation.get("language", "en")
        
        plot_ids = conversation.get("farmer_plot_ids", [])
        
        print(f"Processing conversation for farmer: {farmer_name} ({farmer_id})")

        import asyncio
        farmer_info = asyncio.run(get_farmer_info_2(
            farmer_name=farmer_name,
            gender=gender,
            lang=language,
            plot_ids=plot_ids,
            get_next_stages=True
        ))

        conversation["farmer_info"] = farmer_info
        
        processed_farmer_info = extract_farmer_context_for_prompt(farmer_info)
        
        messages = conversation.get("messages", [])
        chat_history = [] 
        
        standalone_generated = 0
        standalone_skipped = 0
        
        for msg in messages:
            role = msg.get("type") or msg.get("role")
            content = msg.get("content", "")
            
            if role == "user":
                if "standalone_question" in msg:
                    standalone_skipped += 1
                    print(f"  Skipping standalone question (already exists)")
                else:
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
                
                chat_history.append(HumanMessage(content=content))
                
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
        
        return standalone_generated, standalone_skipped

    except Exception as e:
        print(f"Error processing conversation: {e}")
        conversation["processing_error"] = str(e)
        return 0, 0

def fetch_and_process_conversations():
    client = get_mongo_client()
    db = client["chat_database"]
    collection = db["conversations"]

    print(f"Fetching conversations for: {start_date_time.date()}")
    print(f"Time range (UTC): {start_date_time} to {end_date_time}")

    os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(json_path):
        print(f"Found existing file: {json_path}")
        print("Loading existing conversations from file...")
        with open(json_path, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        print(f"Loaded {len(conversations)} conversations from file.")
    else:
        print("No existing file found. Fetching from database...")
        query = {
            "messages.timestamp": {
                "$gte": start_date_time,
                "$lt": end_date_time
            }
        }

        cursor = collection.find(query, {"chat_state": 0})
        conversations = list(cursor)
        
        print(f"Found {len(conversations)} conversations from database.")

        if not conversations:
            print("No conversations found for yesterday.")
            return

    print("Initializing Embedder...")
    embedder = Embedder()
    print("Embedder initialized.")

    total_generated = 0
    total_skipped = 0
    for conv in conversations:
        generated, skipped = process_conversation(conv, embedder)
        total_generated += generated
        total_skipped += skipped
    
    print(f"\nTotal: Generated {total_generated} standalone questions, skipped {total_skipped}\n")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"Saved conversations to: {json_path}")

def transliterate_conversations() -> None:
    """Read a conversations JSON file, transliterate each message, and save back.

    The function loads the JSON file, iterates over each conversation's
    messages list and adds a new key 'content_transliterated' containing the
    transliteration of the original content using Azure's transliteration API.
    
    Skips messages that already have 'content_transliterated'.

    Args:
        json_path: Absolute path to the conversations.json file.
    """


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
                
                if "content_transliterated" in msg:
                    total_skipped_existing += 1
                    print(f"  Conv {conv_idx+1}, Msg {msg_idx+1}: Skipped (already transliterated)")
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

def classify_user_messages() -> None:
    """Read conversations JSON file, classify user messages, and save back.
    
    The function loads the JSON file, iterates over each conversation,
    collects all user messages, uses classify_messages to get classifications,
    and stores the results back in the conversation's user messages objects.
    
    Saves after processing each conversation. Skips conversations where all
    user messages are already tagged. Skips individual messages that are already tagged.
    
    Args:
        json_path: Absolute path to the conversations.json file.
    """
    
    path = Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"Conversations file not found: {json_path}")
    
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"\nClassifying user messages in {len(data)} conversations...")
    
    for conv_idx in tqdm(range(len(data)), desc="Classifying conversations", unit="conv"):
        conv = data[conv_idx]
        messages = conv.get("messages", [])
        
        user_messages_to_classify = []
        user_message_indices = []
        
        for msg_idx, msg in enumerate(messages):
            role = msg.get("type") or msg.get("role")
            if role == "user":
                if "is_query_common" in msg:
                    continue

                content = msg.get("content", "")
                if content and content.strip():
                    user_messages_to_classify.append(content)
                    user_message_indices.append(msg_idx)
        
        if not user_messages_to_classify:
            continue
        
        try:
            classifications = classify_messages(user_messages_to_classify)
            
            for i, msg_idx in enumerate(user_message_indices):
                messages[msg_idx]["is_query_common"] = (classifications[i] == "common")
            
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
        except Exception as e:
            print(f"\n  Conv {conv_idx+1}: Classification error - {e}")
            for msg_idx in user_message_indices:
                messages[msg_idx]["is_query_common_error"] = str(e)
    
    print(f"\nCompleted classification.")
    print(f"Results saved to: {json_path}")

def analyze_most_asked_questions() -> None:
    """Read conversations JSON file and print value counts of standalone questions.
    
    The function loads the JSON file, collects all standalone questions from
    user messages, calculates their frequency, and prints them sorted by
    frequency in descending order.
    """
    
    if not json_path:
        print("JSON path not set.")
        return

    path = Path(json_path)
    if not path.is_file():
        print(f"Conversations file not found: {json_path}")
        return
    
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    standalone_questions = []
    
    for conv in data:
        messages = conv.get("messages", [])
        for msg in messages:
            role = msg.get("type") or msg.get("role")
            if role == "user":
                sq = msg.get("standalone_question")
                if sq:
                    standalone_questions.append(sq)
    
    if not standalone_questions:
        print("\nNo standalone questions found.")
        return
        
    counts = Counter(standalone_questions)
    
    # Print original counts
    print(f"\nOriginal Questions ({len(standalone_questions)} total):")
    print("-" * 80)
    for question, count in counts.most_common():
        print(f"{count:4d} | {question}")
    print("-" * 80)
    
    print("\nNormalizing questions...")
    normalized_counts = normalize_question_counts(dict(counts))
    
    # Sort by count descending
    sorted_questions = sorted(normalized_counts.items(), key=lambda item: item[1]["count"], reverse=True)
    
    print(f"\nMost Asked Questions Analysis ({len(standalone_questions)} total, normalized):")
    print("-" * 120)
    print(f"{'Category':<25} | {'Count':>5} | {'Question'}")
    print("-" * 120)
    for question, data in sorted_questions:
        category = data["category"]
        count = data["count"]
        print(f"{category:<25} | {count:>5} | {question}")
    print("-" * 120)

if __name__ == "__main__":
    set_date_range()
    
    fetch_and_process_conversations()
    
    if os.path.exists(json_path):
        print(f"\nStarting transliteration for {json_path}...")
        transliterate_conversations()
        print(f"\nStarting classification for {json_path}...")
        
        classify_user_messages()
        
        analyze_most_asked_questions()
        # pass
    else:
        print(f"No conversations file found at {json_path}")
