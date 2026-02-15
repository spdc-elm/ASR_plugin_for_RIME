import http.server
import socketserver
import threading
import json
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import requests
import tempfile
import os
import sys

# Configuration
# Configuration
PORT = int(os.getenv("DICTATION_PORT", 8081))
# We will detect the sample rate dynamically, but keep 16000 as a target for resampling if needed
TARGET_SAMPLE_RATE = 16000

# API Configuration (OpenAI Compatible)
# Defaults to localhost (e.g. Izwi, Whisper.cpp, LocalAI)
ASR_API_URL = os.getenv("ASR_API_URL", "http://localhost:8080/v1/audio/transcriptions")
ASR_MODEL = os.getenv("ASR_MODEL", "Qwen3-ASR-1.7B") # Generic default

# Global State
is_recording = False
recording_thread = None
stop_event = threading.Event()
audio_buffer = []
device_samplerate = TARGET_SAMPLE_RATE # Will be updated on recording start

def get_default_device_info():
    try:
        device_info = sd.query_devices(kind='input')
        return device_info
    except Exception as e:
        print(f"Error querying input device: {e}")
        return None

def record_audio_task():
    global audio_buffer, device_samplerate
    print("Recording started...")
    
    # Get device default sample rate to avoid "Invalid Property Value" errors
    device_info = get_default_device_info()
    if device_info:
        device_samplerate = int(device_info.get('default_samplerate', TARGET_SAMPLE_RATE))
        print(f"Using device sample rate: {device_samplerate}")
    else:
        device_samplerate = TARGET_SAMPLE_RATE
    
    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        if not stop_event.is_set():
            audio_buffer.append(indata.copy())

    try:
        # Use the device's native or preferred sample rate
        with sd.InputStream(samplerate=device_samplerate, channels=1, callback=callback):
            stop_event.wait()
    except Exception as e:
        print(f"Error recording: {e}")
        # If it fails, try falling back to standard rates
        if device_samplerate != 44100:
            print("Retrying with 44100Hz...")
            try:
                 device_samplerate = 44100
                 with sd.InputStream(samplerate=44100, channels=1, callback=callback):
                    stop_event.wait()
            except Exception as e2:
                 print(f"Retry failed: {e2}")

    print("Recording stopped.")

def transcribe_buffer():
    global audio_buffer, device_samplerate
    if not audio_buffer:
        return ""
    
    # Concatenate audio data
    try:
        audio_data = np.concatenate(audio_buffer, axis=0)
    except ValueError:
        return "" # Empty buffer

    # If the sample rate is different from target (16k), we might want to resample
    # But for simplicity and speed, let's just save it with the captured rate.
    # Most ASR models handle different sample rates fine (or the server handles conversion).
    
    temp_wav_path = ""
    text = ""

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            wav.write(temp_wav_path, device_samplerate, audio_data)
        
        # Reset buffer immediately
        audio_buffer = []

        # Transcribe
        print(f"Transcribing {temp_wav_path} (Rate: {device_samplerate})...")
        
        files = {
            'file': (os.path.basename(temp_wav_path), open(temp_wav_path, 'rb'), 'audio/wav')
        }
        data = {
            'model': ASR_MODEL,
            'language': 'zh'
        }
        
        response = requests.post(ASR_API_URL, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            print(f"Transcription: {text}")
        else:
            error_msg = f"Error: {response.status_code} - {response.text}"
            print(error_msg)
            return f"[{error_msg}]"

    except Exception as e:
        print(f"Exception during transcription: {str(e)}")
        return f"[Error: {str(e)}]"
    
    finally:
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
    
    return text

class DictationHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        global is_recording, recording_thread, stop_event, audio_buffer

        if self.path == '/toggle':
            response_data = {}
            
            try:
                if not is_recording:
                    # START Recording
                    audio_buffer = [] # Clear buffer
                    stop_event.clear()
                    is_recording = True
                    recording_thread = threading.Thread(target=record_audio_task)
                    recording_thread.start()
                    
                    response_data = {"status": "started", "message": "Recording started"}
                else:
                    # STOP Recording
                    stop_event.set()
                    is_recording = False
                    if recording_thread:
                        recording_thread.join()
                    
                    text = transcribe_buffer()
                    response_data = {"status": "stopped", "text": text}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        return # Suppress default logging

class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"Starting Dictation Server on port {PORT}...")
    try:
        with ReuseAddrTCPServer(("", PORT), DictationHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
