# Call Summarizer

A cross-platform Python desktop application that automatically detects Zoom/Google Meet/Teams calls, captures system audio, transcribes it in real-time, and generates meeting summaries.

## Features

- 🎤 **Automatic Meeting Detection**: Detects active Zoom, Google Meet, or Microsoft Teams calls
- 🔊 **System Audio Capture**: Captures loopback audio on Windows (WASAPI) and macOS (BlackHole/Multi-Output)
- 📝 **Real-Time Transcription**: Transcribes audio using OpenAI Whisper API or local Whisper
- 📊 **Live Summarization**: Generates mini-summaries every 30 seconds and comprehensive final summaries
- 💾 **Multiple Export Formats**: Saves transcripts and summaries as TXT, Markdown, and PDF
- 🎨 **Modern UI**: Clean, dark-themed interface built with PySide6

## Requirements

- Python 3.10 or higher
- Windows 10+ or macOS 10.14+
- Audio device with loopback support

### macOS Additional Requirements

For system audio capture on macOS, you need to install **BlackHole**:

1. Download from: https://github.com/ExistentialAudio/BlackHole
2. Install the virtual audio driver
3. Create a Multi-Output Device in Audio MIDI Setup that includes:
   - Your speakers/headphones
   - BlackHole 16ch

Alternatively, you can use the built-in Multi-Output Device feature in macOS.

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment (recommended)**:
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **For Windows (optional, for better process detection)**:
   ```bash
   pip install pywin32
   ```

5. **For local Whisper transcription (optional)**:
   ```bash
   pip install openai-whisper
   ```

## Configuration

### API Keys

You'll need an API key for summarization (transcription is free):

1. **Gemini API Key** (for summarization - Recommended):
   - Get from https://makersuite.google.com/app/apikey
   - Sign in with your Google account
   - Create an API key
   - Add it in Settings → Summarization Settings → Gemini API Key

2. **OpenAI API Key** (optional, for alternative transcription/summarization):
   - Sign up at https://platform.openai.com/
   - Create an API key
   - Add it in Settings if you want to use OpenAI instead

**Note**: By default, the app uses:
- **Local Whisper** for transcription (free, no API key needed)
- **Gemini** for summarization (requires Gemini API key)

### First Run

1. Launch the application:
   ```bash
   python app.py
   ```

2. Go to **Settings** and configure:
   - Audio device (select your loopback device)
   - Transcription method and API key
   - Summarization provider and API key
   - Output directory (default: `~/CallSummaries`)

3. Enable **Auto-detect meetings** if you want automatic transcription

## Usage

### Manual Transcription

1. Click **Start Transcription** to begin capturing and transcribing audio
2. The live transcript appears in the left panel
3. Mini-summaries appear in the right panel every 30 seconds
4. Click **Stop Transcription** when done
5. A final comprehensive summary is generated automatically

### Automatic Meeting Detection

1. Enable **Auto-detect meetings** in Settings
2. Start a Zoom/Google Meet/Teams call
3. The app automatically detects the meeting and starts transcription
4. Transcription stops automatically after 20 seconds of silence

### Exporting

- Transcripts and summaries are automatically saved when transcription stops
- Files are saved in the configured output directory (default: `~/CallSummaries`)
- Format: `YYYYMMDD_HHMMSS_transcript.txt`, `YYYYMMDD_HHMMSS_summary.md`, `YYYYMMDD_HHMMSS_summary.pdf`
- You can also manually export via File menu

## Project Structure

```
call_summarizer/
├── app.py                 # Main entry point
├── ui/                    # UI components
│   ├── main_window.py     # Main window
│   ├── settings_window.py # Settings dialog
│   └── theme.qss          # Stylesheet
├── audio/                 # Audio capture
│   ├── audio_capture.py  # Audio capture engine
│   └── device_utils.py    # Device management
├── transcription/        # Transcription
│   ├── transcriber.py    # Main transcription engine
│   └── whisper_local.py  # Local Whisper support
├── summaries/            # Summarization
│   ├── summarizer.py     # Summarization engine
│   └── exporter.py       # File export
└── utils/                # Utilities
    ├── process_detector.py # Meeting detection
    └── logger.py          # Logging
```

## Building Executables

### Windows

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build:
   ```bash
   pyinstaller --name="CallSummarizer" --windowed --onefile --icon=icon.ico app.py
   ```

3. Executable will be in `dist/CallSummarizer.exe`

### macOS

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build:
   ```bash
   pyinstaller --name="CallSummarizer" --windowed --onefile app.py
   ```

3. Create .app bundle:
   ```bash
   # PyInstaller creates .app automatically on macOS
   # Located in dist/CallSummarizer.app
   ```

### PyInstaller Spec File

For advanced builds, create a `CallSummarizer.spec` file:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('call_summarizer/ui/theme.qss', 'call_summarizer/ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CallSummarizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

Then build with:
```bash
pyinstaller CallSummarizer.spec
```

## Troubleshooting

### Audio Not Capturing

- **Windows**: Ensure you're using a WASAPI loopback device. Check Settings → Audio Device
- **macOS**: Install BlackHole and configure Multi-Output Device. See macOS Additional Requirements above
- Check that your audio device is not muted
- Try selecting a different audio device in Settings

### Transcription Not Working

- Verify your API key is correct in Settings
- Check your internet connection (for API-based transcription)
- For local Whisper, ensure `openai-whisper` is installed
- Check the console/logs for error messages

### Meeting Detection Not Working

- Ensure the meeting application (Zoom/Teams/Meet) is running
- Check that auto-detect is enabled in Settings
- On macOS, browser tab detection requires Chrome/Safari to be running
- Try manually starting transcription instead

### Summary Generation Fails

- Verify your API key (OpenAI or Gemini) is correct
- Check your API quota/limits
- Ensure you have sufficient transcript content (at least a few sentences)

## License

This project is provided as-is for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- Built with PySide6
- Audio capture using sounddevice
- Transcription powered by OpenAI Whisper
- Summarization using OpenAI GPT and Google Gemini

