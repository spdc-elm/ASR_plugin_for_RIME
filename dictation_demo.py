import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import requests
import tempfile
import os
import sys
import threading
import time

# Constants
SAMPLE_RATE = 16000
API_URL = "http://localhost:8080/v1/audio/transcriptions"
MODEL = "Qwen3-ASR-1.7B"

def record_audio():
    print("Recording... Press Enter to stop.")
    audio_data = []
    
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        audio_data.append(indata.copy())

    # Start recording stream
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
        input()  # Wait for Enter to stop

    return np.concatenate(audio_data, axis=0)

def transcribe_audio(file_path):
    print("Transcribing...")
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                API_URL,
                files={'file': f},
                data={'model': MODEL}
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('text', '')
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Exception: {str(e)}"

def main():
    print("=== Rime Voice Dictation Demo ===")
    print(f"API URL: {API_URL}")
    print(f"Model: {MODEL}")
    print("===========================")

    while True:
        user_input = input("\nPress Enter to start recording (or 'q' to quit): ")
        if user_input.lower() == 'q':
            break

        # Record
        audio_data = record_audio()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            wav.write(temp_wav_path, SAMPLE_RATE, audio_data)
        
        # Transcribe
        text = transcribe_audio(temp_wav_path)
        print(f"\nRecognized: {text}")

        # Cleanup
        os.remove(temp_wav_path)

    print("Goodbye!")

if __name__ == "__main__":
    main()
