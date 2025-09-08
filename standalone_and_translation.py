import os
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ.pop("LANGSMITH_API_KEY", None)
os.environ.pop("LANGCHAIN_API_KEY", None)
os.environ.pop("LANGSMITH_PROJECT", None)
os.environ.pop("LANGCHAIN_ENDPOINT", None)
os.environ.pop("LANGSMITH_ENDPOINT", None)
import json
import pandas as pd
from dotenv import load_dotenv
import time
from tqdm import tqdm

load_dotenv("../.env")

from sarvam_m import to_standalone_question
from gpt_4o_mini import to_standalone_question_openai
from mongo_uri_test import find_doc

from collections import defaultdict

language_count = defaultdict(int)

def build_chat_history(messages):
    if not messages:
        return ""
    parts = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if not role or content is None:
            continue
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def main():
    chats = []
    with open(os.path.join("complaints", "messages.json"), "r", encoding="utf-8") as f:
        chats.extend(json.load(f))
    with open(os.path.join("disease_pest", "messages.json"), "r", encoding="utf-8") as f:
        chats.extend(json.load(f))
    with open(os.path.join("disease_pest-spray", "messages.json"), "r", encoding="utf-8") as f:
        chats.extend(json.load(f))
    with open(os.path.join("historical data", "messages.json"), "r", encoding="utf-8") as f:
        chats.extend(json.load(f))

    rows = []
    for idx, chat in enumerate(tqdm(chats, total=len(chats))):
        # if idx >= 2:
        #     break
        messages = chat.get("messages", [])
        farmer_id = chat.get("farmer_id", "")
        conv_doc = find_doc(messages)
        conv_id = conv_doc.get("_id") if conv_doc else None
        language = conv_doc.get("language") if conv_doc else None
        
        roles = conv_doc.get("roles") if conv_doc else None
        if not roles or "farmuser" not in roles:
            continue
        if "admin" in roles:
            continue
        if farmer_id in ['priyanshu', 'chaitanyarajwade', 'popatganore', "sinankit"]:
            continue

        if language_count and language_count[language] >= 20:
                continue

        for i, m in enumerate(messages):
            if m.get("role") == "user" and i % 2 == 0:
                
                partial_history = messages[:i]
                chat_history = build_chat_history(partial_history)
                latest_user_query = m.get("content", "")

                if not latest_user_query:
                    sarvam_standalone = ""
                    openai_standalone = ""
                else:
                    # try:
                    #     sarvam_standalone = to_standalone_question(chat_history, f"user: {latest_user_query}")
                    #     time.sleep(1)
                    # except Exception as e:
                    #     print(f"sarvam-m error :{e}")
                    #     time.sleep(10)
                    #     try:
                    #         sarvam_standalone = to_standalone_question(chat_history, f"user: {latest_user_query}")
                    #     except:
                    #         print()
                    #         sarvam_standalone = "api error"
                            
                    openai_standalone = to_standalone_question_openai(chat_history, f"user: {latest_user_query}")

                rows.append({
                    "conversation_id": conv_id,
                    "language": language,
                    "chat_history": chat_history,
                    "latest_user_query": latest_user_query,
                    # "sarvam_standalone_question": sarvam_standalone,
                    "openai_standalone_question": openai_standalone,
                })
                language_count[language] += 1
                

    df = pd.DataFrame(
        rows,
        columns=["conversation_id", "language", "chat_history", "latest_user_query", \
                #  "sarvam_standalone_question",\
                 "openai_standalone_question"\
                    ]
    )
    df.to_excel("standalone_questions_openai.xlsx", index=False)
    print(language_count)


if __name__ == "__main__":
    main()
