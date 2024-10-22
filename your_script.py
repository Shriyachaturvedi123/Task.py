import streamlit as st
from moviepy.editor import VideoFileClip, AudioFileClip
from google.cloud import speech_v1p1beta1 as speech
import requests
from gtts import gTTS
import os

# Set up API keys and credentials
api_key = "22ec84421ec24230a3638d1b51e3a7dc"
endpoint_url = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"
google_credentials = 'path-to-google-credentials.json'

# Streamlit UI
st.title("AI-Powered Video Audio Replacement")
st.write("Upload a video and replace its audio with an AI-generated voice.")
video_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi"])

if video_file:
    # Step 1: Extract audio from video
    video_clip = VideoFileClip(video_file.name)
    audio_file_path = "extracted_audio.wav"
    video_clip.audio.write_audiofile(audio_file_path)
    
    # Step 2: Transcribe audio using Google Speech-to-Text
    def transcribe_audio(audio_path):
        client = speech.SpeechClient.from_service_account_file(google_credentials)
        with open(audio_path, "rb") as audio_file:
            audio_content = audio_file.read()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        response = client.recognize(config=config, audio=audio)
        transcription = " ".join([result.alternatives[0].transcript for result in response.results])
        return transcription
    
    transcription = transcribe_audio(audio_file_path)
    st.write("Original Transcription:", transcription)
    
    # Step 3: Pass transcription to GPT-4o for correction
    def correct_transcription_azure(transcription):
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Correct this transcription by removing any grammatical mistakes or filler words: {transcription}"}
            ],
            "max_tokens": 500
        }
        
        response = requests.post(endpoint_url, json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None

    corrected_transcription = correct_transcription_azure(transcription)
    if corrected_transcription:
        st.write("Corrected Transcription:", corrected_transcription)
        
        # Step 4: Convert corrected transcription to speech (Google TTS)
        tts = gTTS(text=corrected_transcription, lang='en', slow=False)
        corrected_audio_file_path = "corrected_audio.mp3"
        tts.save(corrected_audio_file_path)
        
        # Step 5: Replace audio in original video
        corrected_audio_clip = AudioFileClip(corrected_audio_file_path)
        final_video = video_clip.set_audio(corrected_audio_clip)
        
        # Save final video
        final_video_file = "final_video_with_new_audio.mp4"
        final_video.write_videofile(final_video_file)
        
        # Display final video
        st.video(final_video_file)

        # Provide download link
        with open(final_video_file, "rb") as file:
            st.download_button("Download Video", data=file, file_name="final_video_with_new_audio.mp4")
    else:
        st.write("Failed to correct transcription")
