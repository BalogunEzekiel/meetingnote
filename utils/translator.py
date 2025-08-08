
# utils/translator.py

from deep_translator import GoogleTranslator
from gtts import gTTS
from gtts.lang import tts_langs
import os
import uuid
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported languages for TTS
tts_supported = tts_langs().keys()

# Explicitly verify Swahili is supported
if 'sw' not in tts_supported:
    logger.warning("Swahili ('sw') is not supported in gTTS on this setup.")

def translate_text(text, src_lang='auto', target_lang='en'):
    """
    Translates text from source language to target language using GoogleTranslator.
    """
    try:
        translated = GoogleTranslator(source=src_lang, target=target_lang).translate(text)
        logger.info(f"Translation successful: {src_lang} → {target_lang}")
        return translated
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return f"[Translation Error: {str(e)}]"

def generate_tts_audio(text, lang_code):
    """
    Generates an MP3 audio file from text using gTTS, if language is supported.
    """
    try:
        if lang_code in tts_supported:
            tts = gTTS(text, lang=lang_code)
            filename = f"{uuid.uuid4().hex}.mp3"
            tts.save(filename)
            logger.info(f"TTS audio generated: {filename}")
            return filename
        else:
            logger.warning(f"TTS not supported for language code: {lang_code}")
            return None
    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return None
