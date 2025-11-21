"""Audio capture module for system audio loopback."""

import platform
import numpy as np
import sounddevice as sd
import threading
import queue
from typing import Optional, Callable, Tuple
from collections import deque
import time
import logging


class AudioCapture:
    """Captures system audio using loopback for transcription.
    
    Handles audio capture from system audio (loopback) or microphone,
    with platform-specific handling for Windows (WASAPI) and macOS (BlackHole).
    """
    
    # Audio format requirements for Whisper transcription
    SAMPLE_RATE = 16000  # Whisper requires 16kHz sample rate
    CHANNELS = 1  # Mono audio (Whisper requirement)
    CHUNK_SIZE = 4800  # ~300ms of audio at 16kHz (balance between latency and processing)
    SILENCE_THRESHOLD = 0.01  # RMS threshold for silence detection (normalized audio)
    SILENCE_DURATION = 0.5  # Seconds of silence before flagging as silent
    
    def __init__(
        self,
        device_id: Optional[int] = None,
        on_audio_data: Optional[Callable[[np.ndarray], None]] = None
    ):
        """Initialize audio capture.
        
        Args:
            device_id: Audio device ID. None for default loopback
            on_audio_data: Callback function for audio chunks (numpy array)
        """
        self.device_id = device_id
        self.on_audio_data = on_audio_data
        self.system = platform.system()
        self.logger = logging.getLogger("CallSummarizer.audio")
        
        self._stream: Optional[sd.InputStream] = None
        self._is_capturing = False
        self._audio_queue = queue.Queue()
        self._capture_thread: Optional[threading.Thread] = None
        
        # Silence detection
        self._silence_buffer = deque(maxlen=int(self.SILENCE_DURATION * self.SAMPLE_RATE))
        self._last_audio_time = time.time()
        self._is_silent = False
        self._audio_chunks_received = 0
    
    def start(self) -> bool:
        """Start audio capture.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._is_capturing:
            return True
        
        try:
            # On macOS, explicitly trigger microphone permission request
            # by querying devices - this will show the permission dialog if needed
            if self.system == "Darwin":
                try:
                    # This call will trigger the macOS microphone permission dialog
                    # if permission hasn't been granted yet
                    _ = sd.query_devices(kind='input')
                    self.logger.info("Microphone permission check triggered")
                except Exception as e:
                    self.logger.warning(f"Error querying input devices (may need permission): {e}")
            
            # Configure device
            device_info = None
            if self.device_id is not None:
                device_info = sd.query_devices(self.device_id)
            
            # Platform-specific device selection
            # Windows: Use WASAPI loopback for system audio capture
            if self.system == "Windows" and self.device_id is None:
                # WASAPI loopback devices are output devices that can be used as input
                # This allows capturing system audio (what you hear) rather than microphone
                devices = sd.query_devices()
                for i, device in enumerate(devices):
                    # Look for WASAPI devices that are output-only (loopback capable)
                    device_str = str(device).lower()
                    if (device['max_input_channels'] == 0 and 
                        device['max_output_channels'] > 0 and
                        ('wasapi' in device_str or 'loopback' in device_str)):
                        self.device_id = i
                        break
                
                # Fallback: Try default WASAPI input device if no loopback found
                if self.device_id is None:
                    try:
                        default_device = sd.query_devices(kind='input')
                        if 'wasapi' in str(default_device).lower():
                            self.device_id = default_device['index']
                    except Exception:
                        pass
            
            # macOS: Use default input (typically BlackHole or Multi-Output Device)
            if self.system == "Darwin" and self.device_id is None:
                try:
                    # Try default input device (should be configured as Multi-Output with BlackHole)
                    default_input = sd.query_devices(kind='input')
                    if default_input:
                        self.device_id = default_input['index']
                except Exception:
                    pass
            
            # Verify device has input channels
            if self.device_id is not None:
                device_info = sd.query_devices(self.device_id)
                if device_info['max_input_channels'] == 0:
                    # Device has no input, try default input
                    try:
                        default_input = sd.query_devices(kind='input')
                        if default_input and default_input['max_input_channels'] > 0:
                            self.device_id = default_input['index']
                        else:
                            raise Exception("No input-capable audio device found")
                    except Exception as e:
                        self.logger.error(f"No input-capable audio device available: {e}")
                        self.logger.info("Tip: Install BlackHole for system audio capture, or use a microphone.")
                        return False
            
            # Create stream
            self._stream = sd.InputStream(
                device=self.device_id,
                channels=self.CHANNELS,
                samplerate=self.SAMPLE_RATE,
                blocksize=self.CHUNK_SIZE,
                dtype='float32',
                callback=self._audio_callback,
                latency='low'
            )
            
            self._stream.start()
            self._is_capturing = True
            self._last_audio_time = time.time()
            self._audio_chunks_received = 0
            
            device_name = device_info.get('name', 'Unknown') if device_info else 'Default'
            self.logger.info(f"Audio capture started successfully on device: {device_name} (ID: {self.device_id})")
            
            return True
            
        except Exception as e:
            error_msg = f"Error starting audio capture: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.system == "Darwin":
                self.logger.info("macOS Tip: For system audio, install BlackHole or use a microphone device.")
                self.logger.info("Also check System Settings → Privacy & Security → Microphone permissions")
            return False
    
    def stop(self):
        """Stop audio capture."""
        if not self._is_capturing:
            return
        
        self._is_capturing = False
        
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            finally:
                self._stream = None
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback function called by sounddevice for each audio chunk.
        
        Processes incoming audio: converts to mono, normalizes, detects silence,
        and forwards to the registered callback function.
        
        Args:
            indata: Input audio data (numpy array)
            frames: Number of frames in this chunk
            time_info: Timing information from sounddevice
            status: Status flags (errors, underruns, etc.)
        """
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        
        if not self._is_capturing:
            return
        
        self._audio_chunks_received += 1
        if self._audio_chunks_received == 1:
            self.logger.info("First audio chunk received - audio capture is working")
        
        # Convert multi-channel audio to mono by averaging channels
        audio_data = indata.copy()
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Ensure float32 format (required for Whisper processing)
        audio_data = audio_data.astype(np.float32)
        
        # Silence detection: Calculate RMS (Root Mean Square) to measure audio level
        rms = np.sqrt(np.mean(audio_data**2))
        self._silence_buffer.append(rms)
        
        # Update silence state based on audio level
        if rms > self.SILENCE_THRESHOLD:
            # Audio detected - reset silence tracking
            self._last_audio_time = time.time()
            self._is_silent = False
        else:
            # Check if we've been silent long enough to flag as silent
            avg_rms = np.mean(self._silence_buffer) if self._silence_buffer else 0
            if avg_rms < self.SILENCE_THRESHOLD:
                silence_duration = time.time() - self._last_audio_time
                self._is_silent = silence_duration > self.SILENCE_DURATION
        
        # Forward processed audio to registered callback (typically transcriber)
        if self.on_audio_data:
            try:
                self.on_audio_data(audio_data)
            except Exception as e:
                self.logger.error(f"Error in audio callback: {e}", exc_info=True)
    
    def is_silent(self) -> bool:
        """Check if audio is currently silent.
        
        Returns:
            True if silent, False otherwise
        """
        return self._is_silent
    
    def get_audio_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get next audio chunk from queue (non-blocking).
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Audio chunk as numpy array or None
        """
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def is_capturing(self) -> bool:
        """Check if currently capturing audio.
        
        Returns:
            True if capturing, False otherwise
        """
        return self._is_capturing

