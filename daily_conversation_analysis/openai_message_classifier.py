# python3 -m daily_conversation_analysis.openai_message_classifier

"""
This script performs batch classification of user messages to a chatbot in multiple regional languages and scripts.

It uses a few-shot learning approach with a predefined list of common (most repeated) and uncommon user messages as examples.
Using these few-shot examples, it builds a master prompt and classifies any new batch of incoming messages as either "common" or "uncommon."

Classification is done by leveraging OpenAI's GPT-4o model with LangChain's structured output capabilities,
producing an output list of classification keys that exactly matches the size and order of the input message list.

This batch processing design helps minimize token usage and optimize classification costs.

- Uses GPT-4o model with LangChain for structured outputs.
- The code is clean and comment-free as per project requirements.

"""


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Literal
import json
import os
from dotenv import load_dotenv, find_dotenv
import time

env_path = "/Users/ashutosh1/Documents/ATT03251.env"

load_dotenv(env_path, override=True)

class MessageClassifications(BaseModel):
    classifications: List[Literal["common", "uncommon"]] = Field(
        description="List of classifications for each message, in order"
    )

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

structured_llm = llm.with_structured_output(MessageClassifications)

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
    for i, msg in enumerate(messages, 1):
        prompt_parts.append(f"{i}. {msg}\n")
    prompt_parts.append("\nReturn classifications in the same order as the input messages.")
    return "\n".join(prompt_parts)

def classify_messages(messages, few_shot_examples=None):
    if not few_shot_examples:
        few_shot_examples = load_few_shot_examples(os.path.join(os.path.dirname(os.path.abspath(__file__)), "few_shot_examples", "few_shot_examples.json"))
    
    prompt = build_prompt(messages, few_shot_examples)
    response = structured_llm.invoke(prompt)
    time.sleep(10)
    
    return response.classifications

if __name__ == "__main__":
    few_shot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "few_shot_examples", "few_shot_examples.json")
    few_shot_examples = load_few_shot_examples(few_shot_path)
    print(f"\n\n{few_shot_examples}\n\n")

    user_messages = [
        "नमस्ते, कैसे हो?",
        "मैं आज बहुत खुश हूँ!",
        "मेरा पसंदीदा रंग नीला है।",
        "कृपया आप मेरी मदद कर सकते हैं?",
        "मैंने आज एक नया गाना सुना।"
    ]

    results = classify_messages(user_messages, few_shot_examples)
    print(results)
