import streamlit as st
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
from gtts.lang import tts_langs
from pydub import AudioSegment
from pydub.utils import which
import tempfile
import os
import uuid
import subprocess

# Supported languages
languages = {
    "Telugu": "te",
    "Tamil": "ta",
    "Hindi": "hi",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Japanese": "ja",
    "Russian": "ru"
}

tts_supported = tts_langs().keys()

# Streamlit UI
st.set_page_config(page_title="🎙️ Strategic Meeting", layout="centered")
st.title("🎙️ Strategic Meeting Translator App")

# Detect ffmpeg and ffprobe
ffmpeg_path = which("ffmpeg")
ffprobe_path = which("ffprobe")

if not ffmpeg_path or not ffprobe_path:
    st.error("❌ ffmpeg or ffprobe not found. Make sure 'ffmpeg' is in packages.txt")
else:
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffprobe = ffprobe_path
    st.success("✅ ffmpeg and ffprobe configured successfully.")

mode = st.radio("Choose Mode", ["📝 Text → Voice", "🎤 Voice (Audio File) → Text"])

selected_languages = st.multiselect(
    "🌍 Select languages to translate to",
    list(languages.keys()),
    default=["Telugu", "Tamil", "Hindi"]
)

# TEXT TO VOICE
if mode == "📝 Text → Voice":
    input_text = st.text_area("✏️ Enter English Text")

    if st.button("🔊 Translate & Speak"):
        if not input_text.strip():
            st.warning("Please type something!")
        else:
            for lang in selected_languages:
                code = languages[lang]
                try:
                    translated = GoogleTranslator(source='en', target=code).translate(input_text)

                    if code in tts_supported:
                        tts = gTTS(translated, lang=code)
                        filename = f"{uuid.uuid4().hex}.mp3"
                        tts.save(filename)

                        st.markdown(f"### {lang}")
                        with open(filename, "rb") as audio_file:
                            st.audio(audio_file.read(), format="audio/mp3")
                        os.remove(filename)
                    else:
                        st.warning(f"⚠ Audio not supported for {lang} ({code})")

                except Exception as e:
                    st.error(f"❌ Error for {lang}: {e}")

# VOICE TO TEXT
else:
    st.info("🎧 Upload an audio file (.mp3, .wav, or .aac) of your voice")
    uploaded_file = st.file_uploader("Upload Audio", type=["mp3", "wav", "aac"])

    if uploaded_file is not None:
        try:
            # Save uploaded audio temporarily
            file_suffix = "." + uploaded_file.name.split(".")[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_audio_file:
                temp_audio_file.write(uploaded_file.read())
                temp_input_path = temp_audio_file.name

            # Convert to WAV
            audio = AudioSegment.from_file(temp_input_path)
            wav_path = temp_input_path.replace(file_suffix, ".wav")
            audio.export(wav_path, format="wav")

            # Speech recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                detected_text = recognizer.recognize_google(audio_data)

            st.success("📝 Detected Speech:")
            st.write(detected_text)

            for lang in selected_languages:
                code = languages[lang]
                translated = GoogleTranslator(source='auto', target=code).translate(detected_text)
                st.markdown(f"### {lang}")
                st.success(translated)

            # Cleanup
            os.remove(temp_input_path)
            os.remove(wav_path)

        except sr.UnknownValueError:
            st.error("❌ Could not understand your voice.")
        except sr.RequestError:
            st.error("❌ Google Speech API is unavailable.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
