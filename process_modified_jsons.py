import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm
from dotenv import load_dotenv
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from mongo_uri_test import find_doc
from gpt_4o_mini import to_standalone_question_openai
from azure_translation import translate_to_en


load_dotenv("../.env")


STATE_FILE = Path(".processed_conversations.json")


def load_state() -> Dict[str, List[str]]:
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {k: list(v) for k, v in data.items()}
            return {}
    except Exception:
        return {}


def save_state(state: Dict[str, List[str]]) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def discover_message_files() -> List[Path]:
    root = Path(".")
    candidates: List[Path] = []
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        target = directory / "messages.json"
        if target.exists() and target.is_file():
            candidates.append(target)
    return candidates


def build_chat_history(messages: List[Dict]) -> str:
    if not messages:
        return ""
    parts: List[str] = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if not role or content is None:
            continue
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def ensure_standalone_question_for_messages(messages: List[Dict]) -> None:
    for idx, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        if idx % 2 != 0:
            continue
        if isinstance(m.get("standalone_question"), str) and len(m["standalone_question"].strip()) > 0:
            continue
        latest_user_query = m.get("content", "")
        if not isinstance(latest_user_query, str) or len(latest_user_query.strip()) == 0:
            m["standalone_question"] = "message is empty"
            continue
        chat_history = build_chat_history(messages[:idx])
        standalone = to_standalone_question_openai(chat_history, f"user: {latest_user_query}")
        if isinstance(standalone, str) and len(standalone.strip()) > 0:
            m["standalone_question"] = standalone
        else:
            m["standalone_question"] = ""


def ensure_en_translation_for_messages(messages: List[Dict]) -> None:
    for m in messages:
        if "standalone_en" in m and isinstance(m["standalone_en"], str) and len(m["standalone_en"].strip()) > 0:
            continue
        content = m.get("standalone_question", "")
        if content == "message is empty":
            m["standalone_en"] = "message is empty"
            continue
        if content == "":
            m["standalone_en"] = "message is empty"
            continue
        if not isinstance(content, str) or len(content.strip()) == 0:
            continue
        try:
            translated = translate_to_en(content).strip()
            if translated:
                m["standalone_en"] = translated
            else:
                m["standalone_en"] = ""
        except Exception as e:
            print(f"Error translating to English: {e}")
            m["standalone_en"] = ""


def load_vstores() -> Tuple[FAISS, FAISS]:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)
    tools_store: Optional[FAISS] = None
    faq_store: Optional[FAISS] = None
    # try:
    tools_store = FAISS.load_local("vstore", index_name="tools", embeddings=embeddings, allow_dangerous_deserialization=True)
    # except Exception:
    #     tools_store = None
    # try:
    faq_store = FAISS.load_local("vstore", index_name="irrigation", embeddings=embeddings, allow_dangerous_deserialization=True)
    # except Exception:
    #     faq_store = None
    return tools_store, faq_store


def retrieve_from_stores(query: str, tools_store: Optional[FAISS], faq_store: Optional[FAISS], threshold: float = 1.0, k: int = 5) -> Dict[str, List[str]]:
    results: Dict[str, List[str]] = {"tools": [], "faq": []}
    if tools_store is not None:
        docs_scores = tools_store.similarity_search_with_score(query, k=k)
        results["tools"] = [d.page_content for d, s in docs_scores if s <= threshold]
    if faq_store is not None:
        docs_scores = faq_store.similarity_search_with_score(query, k=k)
        results["faq"] = [d.page_content for d, s in docs_scores if s <= threshold]
    return results


def process_file(file_path: Path, state: Dict[str, List[str]], tools_store: FAISS, faq_store: FAISS) -> int:
    modified_path = file_path.with_name(f"{file_path.stem}.modified.json")
    read_path = modified_path if modified_path.exists() else file_path
    with read_path.open("r", encoding="utf-8") as f:
        conversations = json.load(f)

    processed_for_file = set(state.get(str(file_path), []))
    new_processed = []
    updated_count = 0

    for conv in tqdm(conversations):
        messages = conv.get("messages", [])
        doc = find_doc(messages)
        conv_id = None if doc is None else doc.get("_id")
        if conv_id is None:
            continue
        conv_id_str = str(conv_id)
        if conv_id_str in processed_for_file:
            continue

        ensure_standalone_question_for_messages(messages)
        ensure_en_translation_for_messages(messages)

        for idx, m in enumerate(messages):
            if "retrieval" in m and m["retrieval"]:
                continue
            if m.get("role") != "user":
                continue
            if idx % 2 != 0:
                continue
            latest_user_query = m.get("content", "")
            if not isinstance(latest_user_query, str) or len(latest_user_query.strip()) == 0:
                continue
            text_for_retrieval = m.get("standalone_en") or m.get("standalone_question") or latest_user_query or ""
            text_for_retrieval = text_for_retrieval.strip()
            retrieval = retrieve_from_stores(text_for_retrieval, tools_store, faq_store, threshold=1.0, k=5)
            m["retrieval"] = retrieval

        conv["conversation_id"] = conv_id_str

        new_processed.append(conv_id_str)
        updated_count += 1

    if updated_count > 0:
        with modified_path.open("w", encoding="utf-8") as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)

    if new_processed:
        existing = set(state.get(str(file_path), []))
        existing.update(new_processed)
        state[str(file_path)] = sorted(existing)

    return updated_count


def main() -> None:
    files = discover_message_files()
    state = load_state()
    tools_store, faq_store = load_vstores()
    total_updated = 0
    for fpath in files:
        updated = process_file(fpath, state, tools_store, faq_store)
        total_updated += updated

    save_state(state)
    print(json.dumps({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "files_processed": len(files),
        "conversations_updated": total_updated
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

