# RIME Voice Dictation Plugin (Double-Ctrl)

A voice dictation plugin for RIME (Squirrel/Weasel) input methods. It triggers recording when you double-click the **Control** key and uses a local Python server to communicate with any OpenAI-compatible Speech-to-Text API (like Izwi, Whisper.cpp, etc.).

## Features

*   **Double-Ctrl Trigger**: Tap Left or Right Control twice quickly to start/stop dictation.
*   **Non-Blocking UI**: Uses RIME's Preedit area to show "Listening" status without polluting your undo history.
*   **Universal Backend**: Works with any ASR service that supports the OpenAI `v1/audio/transcriptions` API.
*   **Robust Audio**: Automatically handles microphone sample rates (fixes common macOS PortAudio errors).
*   **Undo/Cancel**: Supports `Ctrl+Z` to cleanly cancel a recording.

## Requirements

*   **RIME Input Method**: Squirrel (macOS) or Weasel (Windows).
*   **Python 3.x**: For the helper server.
*   **ASR Backend**: A running speech-to-text service (e.g., [Izwi](https://github.com/agentem-ai/izwi), LocalAI, or just OpenAI API).

## Installation

### 1. Install Python Dependencies
Install the required libraries for the helper server:

```bash
pip install sounddevice numpy scipy requests
```

### 2. Setup RIME Lua Script
Copy `lua/rime_dictation.lua` to your RIME user directory (e.g., `~/Library/Rime/lua/`).


### 3. Configure RIME Processor
Add the Lua processor to your schema's `custom.yaml` (e.g., `rime_mint.custom.yaml` or `default.custom.yaml`).

```yaml
patch:
  engine/processors/@before 0: lua_processor@*rime_dictation
```

**Redeploy RIME** after making these changes.

### 4. Run the Helper Server
Run the Python server that bridges RIME and your ASR backend.

```bash
# Default (Connects to localhost:8080)
python dictation_server.py

# Custom Backend Configuration
export ASR_API_URL="http://127.0.0.1:9000/v1/audio/transcriptions"
export ASR_MODEL="whisper-1"
python dictation_server.py
```

## Usage

1.  **Start**: Double-tap `Ctrl`. You will see "🎤 Listening" in the input bar.
2.  **Speak**: Say what you want to type.
3.  **Stop**: Double-tap `Ctrl` again.

**Cancellation**: 
If you started recording by mistake, press `Ctrl+Z` or `Alt+Z` to cancel immediately.

## Configuration

You can configure the server using environment variables:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DICTATION_PORT` | `8081` | Port for the local RIME helper server. |
| `ASR_API_URL` | `http://localhost:8080...` | The endpoint for the ASR service. |
| `ASR_MODEL` | `qwen3-asr-0.6b` | Model name to send in the API request. |

## Troubleshooting

*   **"Internal PortAudio error"**: The server now auto-detects your microphone's sample rate. Restart `dictation_server.py` if you change audio devices.
*   **Text not appearing**: Check the python server logs. If the ASR backend returns an error (e.g., 400 or 500), it will be displayed in the RIME input bar as `[Error: ...]`.
