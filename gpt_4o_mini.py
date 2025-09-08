import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain import hub
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv("../.env")

rephrase_prompt = hub.pull("langchain-ai/chat-langchain-rephrase")
rephrase_prompt.template = rephrase_prompt.template.replace(
    "standalone question.",
    "standalone question, in English. Translate to English if not so already."
)


openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=os.environ["OPENAI_API_KEY"],
)

def to_standalone_question_openai(chat_history, latest_user_query):
    text_prompt = rephrase_prompt.format(chat_history=chat_history, input=latest_user_query)
    result = openai_llm.invoke([\
#         SystemMessage(content="""- You rephrase follow-up questions into standalone questions.

# Given the chat history and follow-up question, produce a single standalone question that preserves the user’s original intent and wording as much as possible, adding only the missing contextual references from the history needed for clarity. If there’s no clear link to the history, return the follow-up question exactly as given. Do not answer; output only the question.

# Guardrails:

# Minimal transformation: Preserve the user’s intent, terminology, abbreviations, tone, and wording; only add context from the chat history that is strictly necessary to make the question standalone.

# Fallback when context is unclear: If no clear or unambiguous link to the history exists, output the original follow-up question verbatim and nothing else. Avoid adding any new assumptions or specifics.

# Single-purpose: Do not answer the question; only output the single standalone question.

# Additional note: The follow-up user message is authored by the user (not the assistant). Ensure the final question reflects the user’s intent."""), \
                                HumanMessage(content=text_prompt)])
    return result.content

if __name__ == "__main__":
    history = """
        user : किस तरह से ड्रिप इरीगेशन सेटअप करते हैं?,
        assistant : मैं स्टेप्स बता सकता हूँ। आप किस फसल के लिए पूछ रहे हैं?
    """
    latest_q = "गन्ने के लिए बताओ।"
    standalone = to_standalone_question_openai(history, latest_q)
    print(standalone)
