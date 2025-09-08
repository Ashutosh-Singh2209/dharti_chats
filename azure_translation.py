import os
from typing import Optional, Dict
from azure.ai.translation.text import TextTranslationClient, TranslatorCredential
from azure.ai.translation.text.models import InputTextItem
from azure.core.exceptions import HttpResponseError
from bot_core.logger import logger
from dotenv import load_dotenv

load_dotenv("../.env")

key = os.environ.get("AZURE_TRANSLATION_KEY", None)
endpoint = os.environ.get("AZURE_TRANSLATION_ENDPOINT", None)
region = os.environ.get("AZURE_TRANSLATION_REGION", None)

credential: Optional[TranslatorCredential] = None
if key and region:
    credential = TranslatorCredential(key, region)

def translate_to_en(text: str) -> str:
    try:
        target_languages = ["en"]
        input_text_elements = [InputTextItem(text=text)]
        if not endpoint or not credential:
            raise RuntimeError("Azure translation not configured")
        text_translator = TextTranslationClient(endpoint=endpoint, credential=credential)
        response = text_translator.translate(content=input_text_elements, to=target_languages)
        translation = response[0] if response else None
        if translation:
            for translated_text in translation.translations:
                logger.info(f"Translated to: '{translated_text.to}' -> '{translated_text.text}'")
                return translated_text.text
        logger.error(f"Text was not translated: {text}")
        raise RuntimeError("Text was not translated")
    except HttpResponseError as exception:
        logger.error(f"Error Code: {exception.error.code}")
        logger.error(f"Message: {exception.error.message}")
        raise
    except Exception as e:
        logger.error(f"Azure translation failed: {e}")
        raise

def translate_to_en_with_orig(text: str) -> Optional[Dict[str, str]]:
    en_text = translate_to_en(text)
    if en_text:
        return {"orig": text, "translated": en_text}
    return None