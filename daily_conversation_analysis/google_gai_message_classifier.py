"""
This script performs batch classification of user messages to a chatbot in multiple regional languages and scripts.

It uses a few-shot learning approach with a predefined list of common (most repeated) and uncommon user messages as examples.
Using these few-shot examples, it builds a master prompt and classifies any new batch of incoming messages as either "common" or "uncommon."

Classification is done by leveraging Google Gemini's generative AI models with LangChain's structured output capabilities,
producing an output list of classification keys that exactly matches the size and order of the input message list.

This batch processing design helps minimize token usage and optimize classification costs.

- Uses the latest fast mini Gemini model suitable for text classification with few-shot examples.
- The code is clean and comment-free as per project requirements.

"""


from google.generativeai import configure, GenerativeModel, types
import json
import os
# from dotenv import load_dotenv, find_dotenv

# env_path = "/Users/ashutosh1/Documents/ATT03241.env"

# load_dotenv(env_path)

configure(api_key="dummy_key")

model = GenerativeModel("gemini-2.5-pro")

def load_few_shot_examples(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt(messages, few_shot_examples):
    prompt_parts = [
        "Classify each message as 'common' or 'uncommon' based on the following examples:\n"
    ]
    for ex in few_shot_examples:
        prompt_parts.append(f"Input: {ex['input']}\nOutput: {ex['output']}\n")
    prompt_parts.append("Now classify these messages:\n")
    for msg in messages:
        prompt_parts.append(f"Input: {msg}\n")
    prompt_parts.append("Respond only with a JSON list of classification keys (strings: 'common' or 'uncommon'), matching the input order.")
    return "\n".join(prompt_parts)

def classify_messages(messages, few_shot_examples=None):
    if not few_shot_examples:
        few_shot_examples = load_few_shot_examples(os.path.join(os.path.dirname(os.path.abspath(__file__)), "few_shot_examples", "few_shot_examples.json"))
    prompt = build_prompt(messages, few_shot_examples)
    response = model.generate_content(
        prompt,
        generation_config={
                                "response_mime_type": "application/json",
                                "response_schema": {"type": "array", "items": {"type": "string", "enum": ["common", "uncommon"]}}
                            }
    )
    return json.loads(response.text)

if __name__ == "__main__":
    few_shot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "few_shot_examples", "few_shot_examples.json")
    few_shot_examples = load_few_shot_examples(few_shot_path)

    user_messages = [
        "नमस्ते, कैसे हो?",
        "मैं आज बहुत खुश हूँ!",
        "मेरा पसंदीदा रंग नीला है।",
        "कृपया आप मेरी मदद कर सकते हैं?",
        "मैंने आज एक नया गाना सुना।"
    ]

    results = classify_messages(user_messages, few_shot_examples)
    print(results)
