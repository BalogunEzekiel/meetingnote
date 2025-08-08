import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, RTCConfiguration
from utils.translator import translate_text, generate_tts_audio
import tempfile
import os
import av
import queue
import numpy as np
import wave
from pydub import AudioSegment
import whisper

# Page setup
st.set_page_config(page_title="🎙️ Gisting", layout="centered")
st.image("assets/gistinglogo.png", width=150)
st.subheader("Real-Time Voice-to-Voice Translator")

# Language dictionary
languages = {
    "English": "en", "French": "fr", "Spanish": "es", "German": "de", 
    "Hindi": "hi", "Tamil": "ta", "Telugu": "te", "Japanese": "ja", 
    "Russian": "ru", "Yoruba": "yo", "Igbo": "ig", "Chinese": "zh-cn",
    "Swahili": "sw"
}

# Language selection
source_lang = st.selectbox("🎤 Select Spoken Language", options=list(languages.keys()))
target_lang = st.selectbox("🗣️ Translate To", options=list(languages.keys()), index=1)
st.markdown("💡 Speak clearly into your microphone...")

# TURN/STUN Configuration
rtc_configuration = RTCConfiguration(
    {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {
                "urls": ["turn:openrelay.metered.ca:80?transport=tcp"],
                "username": "openrelayproject",
                "credential": "openrelayproject"
            }
        ]
    }
)

# Load Whisper model
@st.cache_resource
def load_model():
    return whisper.load_model("base")  # or "small", "medium", "large"

whisper_model = load_model()

# Audio processor class
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.result_queue = queue.Queue()

    def recv(self, frame: av.AudioFrame):
        audio_np = frame.to_ndarray()
        sample_rate = frame.sample_rate
        channels = frame.layout.channels

        if channels > 1:
            audio_np = np.mean(audio_np, axis=1)

        audio_int16 = np.int16(audio_np * 32767)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            audio_path = f.name

        try:
            result = whisper_model.transcribe(audio_path, language=languages[source_lang])
            text = result.get("text", "[No speech detected]")
            self.result_queue.put(text)
        except Exception as e:
            self.result_queue.put(f"[Could not transcribe speech: {e}]")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

        return frame

# Initialize session state
if "transcribed" not in st.session_state:
    st.session_state.transcribed = ""

# WebRTC audio stream
webrtc_ctx = webrtc_streamer(
    key="voice-translator",
    mode=WebRtcMode.SENDRECV,
    audio_processor_factory=AudioProcessor,
    rtc_configuration=rtc_configuration,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True
)

# Retrieve transcription from real-time input
if webrtc_ctx and webrtc_ctx.state.playing:
    if webrtc_ctx.audio_processor:
        try:
            result_text = webrtc_ctx.audio_processor.result_queue.get(timeout=1)
            if result_text and result_text != st.session_state.transcribed:
                st.session_state.transcribed = result_text
        except queue.Empty:
            pass

# Display transcription and translation
if st.session_state.transcribed:
    st.markdown("### ✏️ Transcribed Text")
    st.write(st.session_state.transcribed)

    translated = translate_text(
        st.session_state.transcribed,
        src_lang=languages[source_lang],
        target_lang=languages[target_lang]
    )

    st.markdown("### 🌍 Translated Text")
    st.success(translated)

    audio_file = generate_tts_audio(translated, lang_code=languages[target_lang])
    if audio_file:
        st.markdown("### 🔊 Translated Audio")
        with open(audio_file, "rb") as f:
            st.audio(f.read(), format="audio/mp3")
        os.remove(audio_file)
    else:
        st.warning(f"Speech not supported for language: {target_lang}")

# Upload section
st.markdown("### 📤 Or Upload an .aac File for Transcription")
uploaded_file = st.file_uploader("Upload an AAC audio file", type=["aac"])

if uploaded_file:
    try:
        # Save uploaded .aac file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".aac") as temp_aac:
            temp_aac.write(uploaded_file.read())
            temp_aac_path = temp_aac.name

        # Convert to .wav
        audio = AudioSegment.from_file(temp_aac_path, format="aac")
        temp_wav_path = temp_aac_path.replace(".aac", ".wav")
        audio.export(temp_wav_path, format="wav")

        # Transcribe with Whisper
        result = whisper_model.transcribe(temp_wav_path, language=languages[source_lang])
        uploaded_transcript = result.get("text", "[No speech detected]")

        st.markdown("### ✏️ Transcribed Text from Upload")
        st.write(uploaded_transcript)

        # Translate and synthesize
        translated = translate_text(
            uploaded_transcript,
            src_lang=languages[source_lang],
            target_lang=languages[target_lang]
        )

        st.markdown("### 🌍 Translated Text")
        st.success(translated)

        audio_file = generate_tts_audio(translated, lang_code=languages[target_lang])
        if audio_file:
            st.markdown("### 🔊 Translated Audio")
            with open(audio_file, "rb") as f:
                st.audio(f.read(), format="audio/mp3")
            os.remove(audio_file)
        else:
            st.warning(f"Speech not supported for language: {target_lang}")

    except Exception as e:
        st.error("Error processing uploaded audio.")
        st.exception(e)

    finally:
        if 'temp_aac_path' in locals() and os.path.exists(temp_aac_path):
            os.remove(temp_aac_path)
        if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
