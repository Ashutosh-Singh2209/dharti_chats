import os
import json
import glob
import requests
from dotenv import load_dotenv
from typing import Optional
import time
from pathlib import Path

load_dotenv("../.env")

subscription_key = os.getenv("AZURE_TRANSLATION_KEY")
endpoint = os.getenv("AZURE_TRANSLATION_ENDPOINT")
region = os.getenv("AZURE_TRANSLATION_REGION")

headers = {
    'Ocp-Apim-Subscription-Key': subscription_key,
    'Ocp-Apim-Subscription-Region': region,
    'Content-type': 'application/json'
}

language_code_map = {
    'hi': ('hi', 'Deva', 'Latn'),
    'gu': ('gu', 'Gujr', 'Latn'),
    'mr': ('mr', 'Deva', 'Latn'),
    'ma': ('mr', 'Deva', 'Latn'),
    'ta': ('ta', 'Taml', 'Latn'),
    'te': ('te', 'Telu', 'Latn'),
    'kn': ('kn', 'Knda', 'Latn'),
    'ml': ('ml', 'Mlym', 'Latn'),
    'bn': ('bn', 'Beng', 'Latn'),
    'pa': ('pa', 'Guru', 'Latn'),
    'or': ('or', 'Orya', 'Latn'),
    'en': None
}

def detect_language_with_azure(text: str) -> Optional[str]:
    try:
        if not endpoint:
            return None
        path = '/detect'
        params = '?api-version=3.0'
        url = endpoint + path + params
        
        body = [{'Text': text}]
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                detected_lang = result[0]['language']
                confidence = result[0]['score']
                print(f"    Detected language: {detected_lang} (confidence: {confidence:.2f})")
                return detected_lang
        else:
            print(f"Language detection API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Language detection error: {str(e)}")
        return None

def transliterate_text(text: str) -> Optional[str]:
    if not text or not text.strip():
        return text
    
    try:
        detected_language = detect_language_with_azure(text)
        if not detected_language or detected_language == 'en':
            return None
        if detected_language not in language_code_map:
            return None
        lang_config = language_code_map[detected_language]
        if lang_config is None:
            return None
        language, from_script, to_script = lang_config
        
        if not endpoint:
            return text
        
        path = '/transliterate'
        params = f'?api-version=3.0&language={language}&fromScript={from_script}&toScript={to_script}'
        url = endpoint + path + params
        
        body = [{'Text': text}]
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                return result[0]['text']
            else:
                print(f"    Empty response for text: {text[:50]}...")
                return text
        else:
            print(f"    Transliteration API Error: {response.status_code}, {response.text}")
            return text
            
    except Exception as e:
        print(f"    Transliteration error for text '{text[:50]}...': {str(e)}")
        return text

def process_json_files_in_folder(folder_path: str = "non_retrieval"):
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist!")
        return
    
    json_files = glob.glob(os.path.join(folder_path, "*_messages.modified_2.json"))
    if not json_files:
        print(f"No JSON files found in {folder_path}")
        return
    
    total_files = len(json_files)
    total_messages_processed = 0
    total_transliterations = 0
    
    print(f"Found {total_files} JSON files to process...")
    
    for file_index, file_path in enumerate(json_files, 1):
        if "complaints" in file_path or "disease_pest-spray" in file_path:
            continue
        print(f"\nProcessing file {file_index}/{total_files}: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            file_transliterations = 0
            
            if isinstance(data, list):
                for obj_index, obj in enumerate(data):
                    if "messages" in obj:
                        print(f"  Processing conversation {obj_index + 1}...")
                        for message_index, message in enumerate(obj["messages"]):
                            if message.get("role") == "user":
                                total_messages_processed += 1
                                content = message.get("content", "")
                                if content and content.strip():
                                    print(f"    Processing user message {message_index + 1}...")
                                    transliterated = transliterate_text(content)
                                    if transliterated and transliterated != content:
                                        message["content_transliterated"] = transliterated
                                        file_transliterations += 1
                                        total_transliterations += 1
                                        print(f"      Original: {content[:100]}...")
                                        print(f"      Transliterated: {transliterated[:100]}...")
                                    elif transliterated is None:
                                        print(f"      Skipped (English or unsupported language)")
                                    time.sleep(0.2)
            
            output_filename = f"transliterated_{os.path.basename(file_path)}"
            path = Path("transliterated_non_retrieval")
            path.mkdir(parents=True, exist_ok=True)
            output_path = os.path.join(path, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as output_file:
                json.dump(data, output_file, indent=2, ensure_ascii=False)
            
            print(f"  Saved {file_transliterations} transliterations to: {output_filename}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            continue
    
    print(f"\n=== SUMMARY ===")
    print(f"Total files processed: {total_files}")
    print(f"Total user messages processed: {total_messages_processed}")
    print(f"Total transliterations completed: {total_transliterations}")

def main():
    if not subscription_key or not endpoint or not region:
        print("Error: Azure translation credentials not found in environment variables.")
        print("Please check AZURE_TRANSLATION_KEY, AZURE_TRANSLATION_ENDPOINT, and AZURE_TRANSLATION_REGION")
        return
    
    print("Starting Azure transliteration for non-retrieval files...")
    print("This will:")
    print("1. Detect language using Azure for each user message")
    print("2. Transliterate only if detected language is an Indian language")
    print("3. Skip transliteration for English or unsupported languages")
    print("4. Output saved alongside input as transliterated_*.json")
    print()
    process_json_files_in_folder("non_retrieval")

if __name__ == "__main__":
    main()
