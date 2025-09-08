import pandas as pd
import time
from tqdm import tqdm
from sarvam_m import to_standalone_question

df = pd.read_excel("standalone_questions_final.xlsx")

def clean_text(text):
    if not isinstance(text, str):
        return text
    text = text.replace("Standalone Question", "").strip()
    text = text.strip('":* ')
    return text

sarvam_questions = []
for _, row in tqdm(df.iterrows(), total=len(df)):
    current_val = row.get("sarvam_standalone_question", "")
    chat_history = row.get("chat_history", "")
    latest_user_query = row.get("latest_user_query", "")

    # if "api error" in current_val and latest_user_query:
    try:
        sarvam_q = clean_text(to_standalone_question(chat_history, f"user: {latest_user_query}"))
        time.sleep(1)
    except:
        time.sleep(10)
        try:
            sarvam_q = clean_text(to_standalone_question(chat_history, f"user: {latest_user_query}"))
        except:
            sarvam_q = "api error"
    # else:
    #     sarvam_q = clean_text(current_val)

    sarvam_questions.append(sarvam_q)

df["sarvam_standalone_question"] = sarvam_questions
df.to_excel("standalone_questions_final.xlsx", index=False)
