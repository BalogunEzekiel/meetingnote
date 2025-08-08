import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode, RTCConfiguration
import speech_recognition as sr
from utils.translator import translate_text, generate_tts_audio
import tempfile
import os
import av
import queue
import numpy as np
import wave
from pydub import AudioSegment

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

# Audio processor class
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()
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
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=languages[source_lang])
                self.result_queue.put(text)
        except Exception:
            self.result_queue.put("[Could not transcribe speech]")
        finally:
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

if webrtc_ctx and webrtc_ctx.state.playing:
    if webrtc_ctx.audio_processor:
        try:
            result_text = webrtc_ctx.audio_processor.result_queue.get(timeout=1)
            if result_text and result_text != st.session_state.transcribed:
                st.session_state.transcribed = result_text
        except queue.Empty:
            pass

# Display transcription & translation from live input
if st.session_state.transcribed:
    st.markdown("### ✏️ Transcribed Text")
    st.write(st.session_state.transcribed)

    target_code = languages[target_lang]
    translated = translate_text(
        st.session_state.transcribed,
        src_lang=languages[source_lang],
        target_lang=target_code
    )

    st.markdown("### 🌍 Translated Text")
    st.success(translated)

    audio_file = generate_tts_audio(translated, lang_code=target_code)
    if audio_file:
        st.markdown("### 🔊 Translated Audio")
        with open(audio_file, "rb") as f:
            st.audio(f.read(), format="audio/mp3")
        os.remove(audio_file)
    else:
        st.warning(f"Speech not supported for language: {target_lang}")

# Upload .aac file for transcription
st.markdown("### 📤 Or Upload an .aac File for Transcription")
uploaded_file = st.file_uploader("Upload an AAC audio file", type=["aac"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".aac") as temp_aac:
        temp_aac.write(uploaded_file.read())
        temp_aac_path = temp_aac.name

    try:
        audio = AudioSegment.from_file(temp_aac_path, format="aac")
        temp_wav_path = temp_aac_path.replace(".aac", ".wav")
        audio.export(temp_wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            uploaded_transcript = recognizer.recognize_google(audio_data, language=languages[source_lang])

        st.markdown("### ✏️ Transcribed Text from Upload")
        st.write(uploaded_transcript)

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
        st.error(f"Error processing uploaded audio: {e}")
    finally:
        os.remove(temp_aac_path)
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
