# python3 -m daily_conversation_analysis.google_gai_message_classifier

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
from dotenv import load_dotenv, find_dotenv
import time

env_path = "/Users/ashutosh1/Documents/ATT03251.env"

load_dotenv(env_path, override=True)

configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
    time.sleep(30)
    return json.loads(response.text)

def normalize_question_counts(counts_dict):
    """
    Takes a dictionary of {question: count}, normalizes the questions to their base form using LLM,
    and returns a dictionary with structure: {base_question: {"count": int, "category": str}}
    """
    questions = list(counts_dict.keys())
    
    if not questions:
        return {}

    prompt = """
    You are an expert data analyst. Your task is to normalize a list of user questions into their standard base forms and categorize them.
    Many questions are semantically identical but phrased differently or in different languages/transliterations.
    Group them by mapping each original question to a single, standard English base question and assign a category.
    
    Available categories (You must STRICTLY use ONLY these):
    - water/irrigation
    - nutrient/fertigation
    - disease/pest
    - disease/pest-spray
    - weather/forecast
    - historical data
    - complaints
    - others
    
    Do NOT create any new categories. If a question does not fit any specific category, classify it as "others".
    
    Example:
    Input Questions:
    - "Should I water my crop?"
    - "Should I water my crops? Please provide information in Gujarati."
    - "Is watering needed?"
    - "When should water be given?"
    - "When should I water my avocado crop?"
    - "Is it okay to water the crop now?"
    
    Mapping Examples:
    {
        "Should I water my crop?": {"base_question": "Should I water my crop?", "category": "water/irrigation"},
        "Should I water my crops? Please provide information in Gujarati.": {"base_question": "Should I water my crop?", "category": "water/irrigation"},
        "Is watering needed?": {"base_question": "Should I water my crop?", "category": "water/irrigation"},
        "When should water be given?": {"base_question": "When should I water my crop?", "category": "water/irrigation"},
        "When should I water my avocado crop?": {"base_question": "When should I water my crop?", "category": "water/irrigation"},
        "Is it okay to water the crop now?": {"base_question": "When should I water my crop?", "category": "water/irrigation"},
        "What fertilizers should I use for my crop?": {"base_question": "What fertilizers should I use?", "category": "nutrient/fertigation"},
        "What fertilizer should I use for my crop?": {"base_question": "What fertilizers should I use?", "category": "nutrient/fertigation"},
        "What fertilizers should be applied?": {"base_question": "What fertilizers should I use?", "category": "nutrient/fertigation"},
        "What pests or diseases affected my crop last week?": {"base_question": "What diseases/pests affected my crop?", "category": "historical data"},
        "What diseases or pests affected my crop last week?": {"base_question": "What diseases/pests affected my crop?", "category": "historical data"},
        "What diseases are affecting my crop?": {"base_question": "What diseases/pests are affecting my crop?", "category": "disease/pest"},
        "What pests are affecting my crop?": {"base_question": "What diseases/pests are affecting my crop?", "category": "disease/pest"},
        "What is the weather forecast for my area?": {"base_question": "What is the weather forecast?", "category": "weather/forecast"},
        "What is the weather forecast for my location?": {"base_question": "What is the weather forecast?", "category": "weather/forecast"},
        "What is the weather forecast for the next few days in my location?": {"base_question": "What is the weather forecast?", "category": "weather/forecast"},
        "What spray should be used for Downy mildew?": {"base_question": "What pesticides should I use?", "category": "disease/pest-spray"},
        "What pesticides should be used for thrips during the flowering stage?": {"base_question": "What pesticides should I use?", "category": "disease/pest-spray"}
    }
    
    Now, process the following list of questions and return ONLY the JSON mapping.
    Each question should map to an object with "base_question" and "category" fields.
    
    Questions:
    """
    
    for q in questions:
        prompt += f"- {q}\n"
        
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        
        mapping = json.loads(response.text)

        print(f"mapping predicted by LLM: \n{mapping}\n")
        
        # Aggregate counts by base question
        result = {}
        for original_q, count in counts_dict.items():
            mapped = mapping.get(original_q, {"base_question": original_q, "category": "others"})
            base_q = mapped["base_question"]
            category = mapped["category"]
            
            if base_q not in result:
                result[base_q] = {"count": 0, "category": category}
            result[base_q]["count"] += count
            
        return result
        
    except Exception as e:
        print(f"Error in normalizing questions: {e}")
        # Fallback to original format
        return {q: {"count": c, "category": "others"} for q, c in counts_dict.items()}

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
