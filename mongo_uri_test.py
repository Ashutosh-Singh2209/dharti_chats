from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("../.env")
import os

client = MongoClient(os.getenv("FYLLO_MONGO_URI"))
db = client["chat_database"]
collection = db["conversations"]

from datetime import datetime, timezone

def convert_dates(obj):
    if isinstance(obj, dict):
        if "$date" in obj and isinstance(obj["$date"], str):
            # Convert string to datetime
            return datetime.strptime(obj["$date"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        else:
            # Recursively process nested dicts
            return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Recursively process lists
        return [convert_dates(i) for i in obj]
    else:
        return obj

messages_value = [
            {
                "role": "user",
                "content": "\n\nठीक ह भा रद्द करने को स्लाइड करें ठीक है",
                "en": "\nOk, slide to cancel",
                "timestamp": {
                    "$date": "2025-07-29T06:52:19.040Z"
                }
            },
            {
                "role": "assistant",
                "content": "आपको फसल की स्टेज को अपडेट करने के लिए ऐप में दिए गए निर्देशों का पालन करना होगा। इसके लिए, कृपया निम्नलिखित वीडियो देखें:\n\n- हिंदी में निर्देश: [फसल की स्टेज कैसे अपडेट करे ?](https://youtu.be/Gx2XUOGqNoA) (Thumbnail: ![फसल की स्टेज कैसे अपडेट करे ?](https://img.youtube.com/vi/Gx2XUOGqNoA/mqdefault.jpg))\n- अंग्रेजी में निर्देश: [How to update crop stages in App?](https://youtu.be/knCXf0vdN7k) (Thumbnail: ![How to update crop stages in App?](https://img.youtube.com/vi/knCXf0vdN7k/mqdefault.jpg))\n\nयदि आपको और सहायता की आवश्यकता है, तो आप ग्राहक सहायता से संपर्क कर सकते हैं: हेल्पलाइन नंबर (+91) 9380908040 पर कॉल करें या contact@fyllo.in पर ईमेल करें।",
                "en": "You need to follow the instructions in the app to update the harvest stage. For this, please watch the following video:\n\n- Instructions in Hindi: [How to update the crop stage?](https://youtu.be/Gx2XUOGqNoA) (Thumbnail: ! [How to update the harvest stage?](https://img.youtube.com/vi/Gx2XUOGqNoA/mqdefault.jpg))\n- Instructions in English: [How to update crop stages in App?](https://youtu.be/knCXf0vdN7k) (Thumbnail: ! [How to update crop stages in App?](https://img.youtube.com/vi/knCXf0vdN7k/mqdefault.jpg))\n\nIf you need further assistance, you can contact customer support: call the helpline number 9380908040 (+91) or email contact@fyllo.in.",
                "timestamp": {
                    "$date": "2025-07-29T06:52:24.032Z"
                }
            },
            {
                "role": "user",
                "content": "\n\nय किया वापिस लाया वापिस ला कर छोड़ दिया",
                "en": "\nWhat did you bring back, brought it back and left it?",
                "timestamp": {
                    "$date": "2025-07-29T06:52:45.607Z"
                }
            },
            {
                "role": "assistant",
                "content": "आपकी समस्या को समझने में मदद करने के लिए, कृपया स्पष्ट करें कि आपको किस चीज़ की आवश्यकता है या किस समस्या का सामना कर रहे हैं। क्या आप किसी विशेष उपकरण या सेवा के बारे में बात कर रहे हैं?",
                "en": "To help you understand your problem, please clarify what you need or what problem you are facing. Are you talking about any particular equipment or service?",
                "timestamp": {
                    "$date": "2025-07-29T06:52:49.656Z"
                }
            },
            {
                "role": "user",
                "content": "\n\nकर लो ये एंड वाला केस में करना क्या है तुमको या तो भेज देना है जो फ्लो वाला जो तुम्हारा छोड़ने पर होता है",
                "en": "\nDo this end case, what is to be done in this case, you either have to send the flow which happens when you leave.",
                "timestamp": {
                    "$date": "2025-07-29T06:54:02.708Z"
                }
            },
            {
                "role": "assistant",
                "content": "आपकी समस्या को समझने में मदद करने के लिए, कृपया स्पष्ट करें कि आप किस विशेष कार्य या प्रक्रिया के बारे में बात कर रहे हैं। क्या आप किसी फसल की देखभाल, सिंचाई, या कीटनाशक छिड़काव के बारे में जानकारी चाहते हैं? कृपया अधिक जानकारी दें ताकि मैं आपकी सहायता कर सकूं।",
                "en": "To help understand your problem, please clarify what particular task or process you are talking about. Are you looking for information on crop care, irrigation, or pesticide spraying? Please provide more information so I can help you.",
                "timestamp": {
                    "$date": "2025-07-29T06:54:06.131Z"
                }
            },
            {
                "role": "user",
                "content": "\n\nरो सकल ख",
                "en": "\nCry Gross B",
                "timestamp": {
                    "$date": "2025-07-29T06:54:16.147Z"
                }
            },
            {
                "role": "assistant",
                "content": "आपकी समस्या को समझने में मदद करने के लिए, कृपया स्पष्ट करें कि आप किस चीज़ के बारे में बात कर रहे हैं। क्या आप किसी विशेष फसल, सिंचाई, या कीटनाशक छिड़काव के बारे में जानकारी चाहते हैं? आपकी सहायता के लिए मैं यहाँ हूँ।",
                "en": "To help you understand your problem, please clarify what you're talking about. Are you looking for information about a particular crop, irrigation, or pesticide spraying? I'm here to help you.",
                "timestamp": {
                    "$date": "2025-07-29T06:54:21.145Z"
                }
            }
        ]

def find_doc(messages_value):
    for message in messages_value:
        keys_to_remove = []
        keys = message.keys()
        for key in keys:
            if key not in ["role", "content", "timestamp", "en"]:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del message[key]
    messages_value2 = convert_dates(messages_value)
    doc = collection.find_one({"messages": messages_value2})
    return doc

def find_doc_by_id(id):
    if id is None:
        return None
    doc = collection.find_one({"_id": id})
    return doc

if __name__=="__main__":
    doc = find_doc(messages_value)

    if doc is None:
        print(f"doc not found\n")
    else:
        print(doc.get("_id"))
