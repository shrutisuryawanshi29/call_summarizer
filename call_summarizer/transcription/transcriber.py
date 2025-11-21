"""Main transcription engine with OpenAI and local Whisper support."""

import numpy as np
import threading
import queue
import time
import logging
from typing import Optional, Callable, List
from enum import Enum

from .whisper_local import WhisperLocalTranscriber
from ..utils.transcript_filter import TranscriptFilter


class TranscriptionMethod(Enum):
    """Transcription method options."""
    OPENAI_WHISPER_API = "openai_whisper_api"
    OPENAI_REALTIME = "openai_realtime"
    LOCAL_WHISPER = "local_whisper"


class Transcriber:
    """Main transcription engine."""
    
    def __init__(
        self,
        method: TranscriptionMethod = TranscriptionMethod.OPENAI_WHISPER_API,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
        on_transcription: Optional[Callable[[str, float], None]] = None
    ):
        """Initialize transcriber.
        
        Args:
            method: Transcription method to use
            api_key: OpenAI API key (required for API methods)
            model: Model name (for API) or local model size (for local)
            on_transcription: Callback function(text, timestamp)
        """
        self.method = method
        self.api_key = api_key
        self.model = model
        self.on_transcription = on_transcription
        self.logger = logging.getLogger("CallSummarizer.transcription")
        
        self._is_running = False
        self._audio_queue = queue.Queue()
        self._transcription_thread: Optional[threading.Thread] = None
        self._audio_buffer: List[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        
        # Audio buffering settings for transcription
        self._buffer_duration = 3.0  # Buffer 3 seconds of audio before transcribing (better accuracy)
        self._sample_rate = 16000  # Whisper requires 16kHz sample rate
        self._chunk_size = int(self._buffer_duration * self._sample_rate)  # Total samples per chunk
        
        # Local transcriber
        self._local_transcriber: Optional[WhisperLocalTranscriber] = None
        if method == TranscriptionMethod.LOCAL_WHISPER:
            self._local_transcriber = WhisperLocalTranscriber(model_name=model)
        
        # Transcript filter for cleaning
        self._filter = TranscriptFilter()
    
    def start(self) -> bool:
        """Start transcription engine.
        
        Returns:
            True if started successfully
        """
        if self._is_running:
            return True
        
        # Initialize local transcriber if needed
        if self._local_transcriber:
            self.logger.info(f"Initializing local Whisper transcriber with model: {self.model}")
            if not self._local_transcriber.initialize():
                self.logger.error("Failed to initialize local Whisper transcriber")
                return False
            self.logger.info("Local Whisper transcriber initialized successfully")
        
        self._is_running = True
        self._transcription_thread = threading.Thread(
            target=self._transcription_worker,
            daemon=True
        )
        self._transcription_thread.start()
        self.logger.info(f"Transcription worker thread started (method: {self.method.value})")
        return True
    
    def stop(self):
        """Stop transcription engine."""
        self._is_running = False
        if self._transcription_thread:
            self._transcription_thread.join(timeout=2.0)
    
    def add_audio(self, audio: np.ndarray):
        """Add audio chunk for transcription.
        
        Buffers audio chunks until we have enough for transcription (3 seconds).
        This improves transcription accuracy by providing more context.
        
        Args:
            audio: Audio data as numpy array (16kHz mono float32)
        """
        if not self._is_running:
            return
        
        with self._buffer_lock:
            self._audio_buffer.append(audio)
            
            # Check if we've accumulated enough audio (3 seconds worth)
            total_samples = sum(len(chunk) for chunk in self._audio_buffer)
            if total_samples >= self._chunk_size:
                # Concatenate all buffered chunks and send to transcription queue
                audio_to_process = np.concatenate(self._audio_buffer)
                self._audio_buffer = []  # Clear buffer for next batch
                self._audio_queue.put(audio_to_process)
                self.logger.debug(f"Audio chunk queued for transcription ({len(audio_to_process)} samples)")
    
    def _transcription_worker(self):
        """Worker thread that processes audio chunks from the queue.
        
        Runs in a separate thread to avoid blocking the main audio capture.
        Continuously processes audio chunks and calls the transcription callback.
        """
        while self._is_running:
            try:
                # Get next audio chunk from queue (non-blocking with timeout)
                audio = self._audio_queue.get(timeout=0.5)
                timestamp = time.time()  # Record when transcription started
                
                # Route to appropriate transcription method based on configuration
                text = None
                if self.method == TranscriptionMethod.OPENAI_WHISPER_API:
                    text = self._transcribe_openai_api(audio)
                elif self.method == TranscriptionMethod.OPENAI_REALTIME:
                    text = self._transcribe_openai_realtime(audio)
                elif self.method == TranscriptionMethod.LOCAL_WHISPER:
                    text = self._transcribe_local(audio)
                
                # Filter out noise, duplicates, and clean up the text
                if text:
                    filtered_text = self._filter.filter_text(text)  # Remove noise/duplicates
                    if filtered_text:
                        cleaned_text = self._filter.clean_text(filtered_text)  # Format properly
                        # Only call callback if text passed all filters
                        if cleaned_text and self.on_transcription:
                            self.on_transcription(cleaned_text, timestamp)
                    
            except queue.Empty:
                # No audio to process yet, continue waiting
                continue
            except Exception as e:
                self.logger.error(f"Error in transcription worker: {e}", exc_info=True)
                time.sleep(0.1)  # Brief pause before retrying
    
    def _transcribe_openai_api(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe using OpenAI Whisper API.
        
        Args:
            audio: Audio data
            
        Returns:
            Transcribed text or None
        """
        try:
            from openai import OpenAI
            
            if not self.api_key:
                return None
            
            client = OpenAI(api_key=self.api_key)
            
            # Convert to int16 for API
            if audio.dtype != np.int16:
                audio_int16 = (audio * 32767).astype(np.int16)
            else:
                audio_int16 = audio
            
            # Save to temporary file
            import tempfile
            import wave
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                with wave.open(tmp_file.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._sample_rate)
                    wf.writeframes(audio_int16.tobytes())
                
                # Transcribe
                with open(tmp_file.name, 'rb') as f:
                    transcript = client.audio.transcriptions.create(
                        model=self.model,
                        file=f,
                        language="en"
                    )
                
                import os
                os.unlink(tmp_file.name)
                
                return transcript.text.strip() if transcript.text else None
                
        except ImportError:
            self.logger.error("openai package not installed. Install with: pip install openai")
            return None
        except Exception as e:
            self.logger.error(f"Error in OpenAI API transcription: {e}", exc_info=True)
            return None
    
    def _transcribe_openai_realtime(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe using OpenAI Realtime API.
        
        Args:
            audio: Audio data
            
        Returns:
            Transcribed text or None
        """
        # Realtime API requires WebSocket connection
        # For now, fall back to Whisper API
        return self._transcribe_openai_api(audio)
    
    def _transcribe_local(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe using local Whisper.
        
        Args:
            audio: Audio data
            
        Returns:
            Transcribed text or None
        """
        if not self._local_transcriber:
            return None
        
        return self._local_transcriber.transcribe_chunk(audio)
    
    def is_running(self) -> bool:
        """Check if transcription is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._is_running

