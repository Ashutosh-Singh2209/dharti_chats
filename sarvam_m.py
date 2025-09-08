import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain import hub
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv("../.env")

# Pull prompt and tweak
rephrase_prompt = hub.pull("langchain-ai/chat-langchain-rephrase")
rephrase_prompt.template = rephrase_prompt.template.replace(
    "standalone question.",
    "standalone question, in English. Translate to english if not so already."
)

additional_info = SystemMessage(content="""- The Dharti is a precision agricultural assistant for supporting farmers of Fyllo (Hindi: फ़ाइलो, Gujarati: ફાયલો, Kannada: ಫೈಲೋ, Marathi: फायलो, Telugu: ఫాయ్లో, Tamil: பைலோ) company, designed to help farmers grow their crops precisely. It uses real-time farm data and the latest agricultural practices to provide accurate and timely advice. """)

print(rephrase_prompt.template)

# Define structured output schema
class StandaloneOutput(BaseModel):
    reasoning: str = Field(description="Brief explanation of reasoning for the standalone question")
    standalone_question: str = Field(description="The final standalone question")

# LLM
sarvam_llm = ChatOpenAI(
    model="sarvam-m",
    openai_api_key=os.environ["SARVAM_API_KEY_ASHU_RANJAN"],
    openai_api_base="https://api.sarvam.ai/v1",
)

# Attach structured output
sarvam_llm_structured = sarvam_llm.with_structured_output(StandaloneOutput)

def to_standalone_question(chat_history, latest_user_query):
    text_prompt = rephrase_prompt.format(chat_history=chat_history, input=latest_user_query)
    result = sarvam_llm.invoke([additional_info,
        SystemMessage(content="""- You rephrase follow-up questions into standalone questions.

Given the chat history and follow-up question, produce a single standalone question that preserves the user’s original intent and wording as much as possible, adding only the missing contextual references from the history needed for clarity. If there’s no clear link to the history, return the follow-up question exactly as given. Do not answer; output only the question.

Guardrails:

Minimal transformation: Preserve the user’s intent, terminology, abbreviations, tone, and wording; only add context from the chat history that is strictly necessary to make the question standalone.

Fallback when context is unclear: If no clear or unambiguous link to the history exists, output the original follow-up question verbatim and nothing else. Avoid adding any new assumptions or specifics.

Single-purpose: Do not answer the question; only output the single standalone question.

Additional note: The follow-up user message is authored by the user (not the assistant). Ensure the final question reflects the user’s intent.
                      Return only the standalone question, and nothing else, no reasoning etc.
                      standalone question should start after `Standalone Question:` below"""),
        HumanMessage(content=text_prompt)
    ])
    return result.content.split("Standalone Question:")[1].strip()

if __name__ == "__main__":
    history = """
        user : किस तरह से ड्रिप इरीगेशन सेटअप करते हैं?,
        assistant : मैं स्टेप्स बता सकता हूँ। आप किस फसल के लिए पूछ रहे हैं?
    """
    latest_q = "गन्ने के लिए बताओ।"
    standalone = to_standalone_question(history, latest_q)
    print(standalone)
