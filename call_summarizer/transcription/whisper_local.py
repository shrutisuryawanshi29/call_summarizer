"""Local Whisper transcription using faster-whisper (faster) or openai-whisper (fallback)."""

import numpy as np
from typing import Optional, List, Tuple
import threading
import queue
import time


class WhisperLocalTranscriber:
    """Local Whisper-based transcriber."""
    
    def __init__(self, model_name: str = "base"):
        """Initialize local Whisper transcriber.
        
        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self._model = None
        self._faster_whisper_model = None
        self._use_faster_whisper = False  # Track which backend we're using
        self._audio_buffer: List[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """Initialize the Whisper model.
        
        Tries faster-whisper first (2-4x faster, lower memory, free),
        falls back to openai-whisper if unavailable.
        
        Returns:
            True if successful, False otherwise
        """
        if self._is_initialized:
            return True
        
        # Try faster-whisper first (recommended: 2-4x faster, lower memory usage, free)
        try:
            from faster_whisper import WhisperModel
            
            print(f"Loading Faster-Whisper model '{self.model_name}' (2-4x faster, free)...")
            print("Note: First download requires internet connection and may take 1-2 minutes")
            
            # Initialize faster-whisper with optimized settings
            # device="cpu" for compatibility (use "cuda" if GPU available for even faster processing)
            # compute_type="int8" provides good balance of speed and accuracy
            self._faster_whisper_model = WhisperModel(
                self.model_name,
                device="cpu",  # Can be "cuda" for GPU acceleration
                compute_type="int8"  # int8 quantization: faster, lower memory, slight accuracy trade-off
            )
            
            self._use_faster_whisper = True
            self._is_initialized = True
            print("✓ Faster-Whisper model loaded successfully! (2-4x faster transcription)")
            return True
                
        except ImportError:
            # faster-whisper not available, try openai-whisper
            print("faster-whisper not found, falling back to openai-whisper...")
            print("Tip: Install with 'pip install faster-whisper' for 2-4x faster transcription")
        except Exception as e:
            # faster-whisper failed, try openai-whisper
            print(f"faster-whisper initialization failed: {e}")
            print("Falling back to openai-whisper...")
        
        # Fallback to openai-whisper
        try:
            # Set SSL certificate path before importing whisper
            import os
            import certifi
            
            # Set environment variables for SSL certificate verification
            cert_path = certifi.where()
            if cert_path and os.path.exists(cert_path):
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
            
            # Try openai-whisper
            import whisper
            
            print(f"Loading Whisper model '{self.model_name}' (this may take a minute on first run)...")
            print("Note: First download requires internet connection and may take 1-2 minutes")
            
            # Try to load model with SSL fix
            try:
                self._model = whisper.load_model(self.model_name)
            except Exception as download_error:
                error_str = str(download_error)
                if "CERTIFICATE" in error_str or "SSL" in error_str:
                    print("\n⚠️  SSL Certificate Error Detected")
                    print("\nTo fix this, run in your terminal:")
                    print("  cd /Users/shrutisuryawanshi/Documents/Cursor/Summarizer")
                    print("  source venv/bin/activate")
                    print("  /Applications/Python\\ 3.12/Install\\ Certificates.command")
                    print("\nOr try:")
                    print("  pip install --upgrade certifi")
                    print("\nAlternatively, use OpenAI Whisper API in Settings (requires API key)")
                    return False
                else:
                    raise
            
            self._use_faster_whisper = False
            self._is_initialized = True
            print("✓ Whisper model loaded successfully!")
            return True
        except ImportError:
            print("openai-whisper not installed. Install with: pip install openai-whisper")
            return False
        except Exception as e:
            error_msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in error_msg or "SSL" in error_msg:
                print(f"SSL certificate error: {e}")
                print("\nTo fix SSL certificate issues on macOS, run:")
                print("  /Applications/Python\\ 3.12/Install\\ Certificates.command")
                print("\nOr install certificates manually:")
                print("  pip install --upgrade certifi")
            else:
                print(f"Error initializing Whisper: {e}")
            return False
    
    def transcribe_chunk(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe a single audio chunk.
        
        Args:
            audio: Audio data as numpy array (16kHz mono float32)
            
        Returns:
            Transcribed text or None
        """
        if not self._is_initialized:
            return None
        
        try:
            # Ensure audio is in correct format
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Normalize to [-1, 1] range
            if audio.max() > 1.0 or audio.min() < -1.0:
                audio = audio / np.max(np.abs(audio))
            
            # Use faster-whisper if available (2-4x faster)
            if self._use_faster_whisper and self._faster_whisper_model is not None:
                return self._transcribe_faster_whisper(audio)
            
            # Fallback to openai-whisper
            if self._model is None:
                return None
            
            # Optimized transcription parameters for better accuracy
            # These settings improve recognition of various English accents
            transcribe_params = {
                "language": "en",  # English (handles accent variations automatically)
                "task": "transcribe",
                "fp16": False,  # Use float32 for better accuracy (fp16 can cause issues on some systems)
                "verbose": False,  # Suppress verbose output
                "temperature": 0.0,  # Deterministic output (better for consistent transcription)
                "condition_on_previous_text": True,  # Use previous context for better recognition
                "initial_prompt": "This is a meeting or conversation in English with Indian accent. Focus on spoken content only.",
                "no_speech_threshold": 0.6,  # Higher threshold = more aggressive noise filtering
                "compression_ratio_threshold": 2.4,  # Filter out repetitive/hallucinated text
            }
            
            # Beam search for larger models (improves accuracy at cost of speed)
            # Only use for models that can handle it (small, medium, large)
            if self.model_name in ['small', 'medium', 'large']:
                transcribe_params["beam_size"] = 5  # Number of beams for search
                transcribe_params["best_of"] = 3  # Consider top 3 candidates
                transcribe_params["patience"] = 1.0  # Patience parameter for decoding
            
            result = self._model.transcribe(audio, **transcribe_params)
            
            text = result.get("text", "").strip()
            return text if text else None
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    def _transcribe_faster_whisper(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe using faster-whisper (2-4x faster than openai-whisper).
        
        Args:
            audio: Audio data as numpy array (16kHz mono float32)
            
        Returns:
            Transcribed text or None
        """
        try:
            # Ensure audio is 1D array (faster-whisper requirement)
            if audio.ndim > 1:
                audio = audio.flatten()
            
            # Transcribe with faster-whisper (optimized CTranslate2 backend)
            segments, info = self._faster_whisper_model.transcribe(
                audio,
                language="en",
                initial_prompt="This is a meeting or conversation in English with Indian accent. Focus on spoken content only.",
                temperature=0.0,  # Deterministic output
                beam_size=5 if self.model_name in ['small', 'medium', 'large'] else 1,  # Beam search for larger models
                vad_filter=True,  # Built-in Voice Activity Detection (filters silence automatically)
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # Minimum silence duration to split segments
                    threshold=0.6  # VAD threshold (higher = more aggressive filtering)
                )
            )
            
            # Extract and join text from all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            text = " ".join(text_parts).strip()
            return text if text else None
            
        except Exception as e:
            print(f"Error in faster-whisper transcription: {e}")
            return None
    
    def transcribe_streaming(self, audio_chunks: List[np.ndarray]) -> Optional[str]:
        """Transcribe multiple audio chunks as a continuous stream.
        
        Args:
            audio_chunks: List of audio chunks
            
        Returns:
            Transcribed text or None
        """
        if not audio_chunks:
            return None
        
        # Concatenate chunks
        audio = np.concatenate(audio_chunks)
        return self.transcribe_chunk(audio)
    
    def is_ready(self) -> bool:
        """Check if transcriber is ready.
        
        Returns:
            True if ready, False otherwise
        """
        return self._is_initialized

