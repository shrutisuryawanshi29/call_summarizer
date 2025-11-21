"""Main window for the Call Summarizer application."""

import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QStatusBar, QMenuBar,
    QMenu, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QFont

from ..audio.audio_capture import AudioCapture
from ..audio.device_utils import AudioDeviceManager
from ..transcription.transcriber import Transcriber, TranscriptionMethod
from ..summaries.summarizer import Summarizer, SummarizationProvider
from ..summaries.exporter import Exporter
from ..utils.process_detector import MeetingDetector
from ..utils.logger import setup_logger
from .settings_window import SettingsWindow


class TranscriptionSignals(QObject):
    """Signals for transcription updates."""
    transcript_update = Signal(str, float)  # text, timestamp
    summary_update = Signal(str)  # summary text
    status_update = Signal(str)  # status message


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.logger = setup_logger()
        
        # Components
        self.audio_capture: Optional[AudioCapture] = None
        self.transcriber: Optional[Transcriber] = None
        self.summarizer: Optional[Summarizer] = None
        self.exporter: Optional[Exporter] = None
        self.meeting_detector = MeetingDetector()
        self.device_manager = AudioDeviceManager()
        
        # State
        self.is_transcribing = False
        self.transcript_segments: list = []
        self.full_transcript = ""
        self.meeting_start_time: Optional[datetime] = None
        self.last_summarized_index = 0  # Track which segments have been summarized
        
        # Settings
        self.settings = self.load_settings()
        
        # Signals
        self.signals = TranscriptionSignals()
        self.signals.transcript_update.connect(self.on_transcript_update)
        self.signals.summary_update.connect(self.on_summary_update)
        self.signals.status_update.connect(self.on_status_update)
        
        # Timers
        self.auto_detect_timer = QTimer()
        self.auto_detect_timer.timeout.connect(self.check_meeting_status)
        self.mini_summary_timer = QTimer()
        self.mini_summary_timer.timeout.connect(self.generate_mini_summary)
        self.audio_check_timer = QTimer()
        self.audio_check_timer.timeout.connect(self.check_audio_reception)
        self._audio_received_since_start = False
        
        # UI
        self.init_ui()
        self.setup_audio()
        self.setup_transcription()
        self.setup_summarization()
        
        # Auto-detect if enabled
        if self.settings.get('auto_detect_meetings', True):
            self.auto_detect_timer.start(2000)  # Check every 2 seconds
    
    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Call Summarizer")
        self.setMinimumSize(1000, 750)
        
        # Central widget with better styling - use theme background
        central_widget = QWidget()
        # Set background to match Cursor dark theme
        central_widget.setStyleSheet("""
            QWidget {
                background: #1e1e1e;
            }
        """)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section with title and status
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title with better styling
        title_label = QLabel("🎙️ Call Summarizer")
        title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(26)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Status label with better styling
        self.status_label = QLabel("Ready to transcribe")
        self.status_label.setObjectName("statusLabel")
        status_font = QFont()
        status_font.setPointSize(10)
        self.status_label.setFont(status_font)
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(header_widget)
        
        # Control buttons with better layout
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        
        self.start_button = QPushButton("▶ Start Transcription")
        self.start_button.setObjectName("startButton")
        self.start_button.setMinimumHeight(48)
        self.start_button.setMinimumWidth(200)
        self.start_button.clicked.connect(self.start_transcription)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹ Stop Transcription")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setMinimumHeight(48)
        self.stop_button.setMinimumWidth(200)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_transcription)
        button_layout.addWidget(self.stop_button)
        
        settings_button = QPushButton("⚙ Settings")
        settings_button.setMinimumHeight(48)
        settings_button.setMinimumWidth(130)
        settings_button.clicked.connect(self.show_settings)
        button_layout.addWidget(settings_button)
        
        button_layout.addStretch()
        layout.addWidget(button_widget)
        
        # Splitter for transcript and summary with better styling
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Transcript panel with card-like styling
        transcript_widget = QWidget()
        transcript_widget.setStyleSheet("""
            QWidget {
                background: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
        """)
        transcript_layout = QVBoxLayout(transcript_widget)
        transcript_layout.setSpacing(12)
        transcript_layout.setContentsMargins(20, 20, 20, 20)
        
        transcript_header = QWidget()
        transcript_header_layout = QHBoxLayout(transcript_header)
        transcript_header_layout.setContentsMargins(0, 0, 0, 0)
        
        transcript_label = QLabel("📝 Live Transcript")
        transcript_label_font = QFont()
        transcript_label_font.setPointSize(14)
        transcript_label_font.setBold(True)
        transcript_label.setFont(transcript_label_font)
        transcript_label.setStyleSheet("color: #cccccc;")
        transcript_header_layout.addWidget(transcript_label)
        transcript_header_layout.addStretch()
        
        transcript_layout.addWidget(transcript_header)
        
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setPlaceholderText("Your transcript will appear here in real-time...")
        self.transcript_text.setFont(QFont("", 11))
        self.transcript_text.setStyleSheet("color: #cccccc;")
        transcript_layout.addWidget(self.transcript_text)
        
        splitter.addWidget(transcript_widget)
        
        # Summary panel with card-like styling
        summary_widget = QWidget()
        summary_widget.setStyleSheet("""
            QWidget {
                background: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
            }
        """)
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setSpacing(12)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        
        summary_header = QWidget()
        summary_header_layout = QHBoxLayout(summary_header)
        summary_header_layout.setContentsMargins(0, 0, 0, 0)
        
        summary_label = QLabel("📊 Live Summary")
        summary_label_font = QFont()
        summary_label_font.setPointSize(14)
        summary_label_font.setBold(True)
        summary_label.setFont(summary_label_font)
        summary_label.setStyleSheet("color: #cccccc;")
        summary_header_layout.addWidget(summary_label)
        summary_header_layout.addStretch()
        
        summary_layout.addWidget(summary_header)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Meeting summaries will appear here...")
        self.summary_text.setFont(QFont("", 11))
        self.summary_text.setStyleSheet("color: #cccccc;")
        summary_layout.addWidget(self.summary_text)
        
        splitter.addWidget(summary_widget)
        
        splitter.setSizes([500, 500])
        splitter.setHandleWidth(2)
        layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Menu bar
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Transcript", self)
        export_action.triggered.connect(self.export_transcript)
        file_menu.addAction(export_action)
        
        export_summary_action = QAction("Export Summary", self)
        export_summary_action.triggered.connect(self.export_summary)
        file_menu.addAction(export_summary_action)
        
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_audio(self):
        """Set up audio capture."""
        # On macOS, try to trigger microphone permission dialog early
        # by querying audio devices when the app starts
        if sys.platform == "darwin":
            try:
                import sounddevice as sd
                # This will trigger the permission dialog if not already granted
                _ = sd.query_devices(kind='input')
                self.logger.info("Audio device query triggered (may request microphone permission)")
            except Exception as e:
                self.logger.debug(f"Audio device query: {e}")
        
        device_id = None
        device_name = self.settings.get('audio_device', '')
        
        if device_name and device_name != "Default":
            device = self.device_manager.find_device_by_name(device_name)
            if device:
                device_id = device['id']
        
        if device_id is None:
            device = self.device_manager.get_default_loopback_device()
            if device:
                device_id = device['id']
        
        self.audio_capture = AudioCapture(
            device_id=device_id,
            on_audio_data=self.on_audio_data
        )
        
        # Check macOS BlackHole
        if sys.platform == "darwin":
            is_installed, message = self.device_manager.check_macos_blackhole()
            if not is_installed:
                QMessageBox.information(self, "macOS Audio Setup", message)
    
    def setup_transcription(self):
        """Set up transcription engine."""
        method_str = self.settings.get('transcription_method', 'local_whisper')
        method = TranscriptionMethod.LOCAL_WHISPER
        if method_str == 'openai_whisper_api':
            method = TranscriptionMethod.OPENAI_WHISPER_API
        
        api_key = self.settings.get('openai_api_key', '')
        # Use 'small' model by default for better accent recognition
        # 'base' is faster but less accurate for accents
        model = self.settings.get('transcription_model', 'small')
        
        self.transcriber = Transcriber(
            method=method,
            api_key=api_key if api_key else None,
            model=model,
            on_transcription=self.on_transcription_callback
        )
    
    def setup_summarization(self):
        """Set up summarization engine."""
        provider_str = self.settings.get('summary_provider', 'gemini')
        provider = SummarizationProvider.GEMINI
        if provider_str == 'openai':
            provider = SummarizationProvider.OPENAI
        
        api_key = self.settings.get('gemini_api_key' if provider == SummarizationProvider.GEMINI else 'openai_api_key', '')
        # Default to gemini-2.5-flash (better free tier limits)
        model = self.settings.get('summary_model', 'gemini-2.5-flash')
        
        self.summarizer = Summarizer(
            provider=provider,
            api_key=api_key if api_key else None,
            model=model
        )
        
        # Setup exporter
        output_dir = self.settings.get('output_directory', '')
        if output_dir:
            self.exporter = Exporter(Path(output_dir))
        else:
            self.exporter = Exporter()
    
    def start_transcription(self):
        """Start transcription."""
        if self.is_transcribing:
            return
        
        # Check audio device
        if not self.audio_capture:
            QMessageBox.warning(self, "Error", "Audio capture not initialized.")
            return
        
        # Check transcription
        if not self.transcriber:
            QMessageBox.warning(self, "Error", "Transcriber not initialized.")
            return
        
        # Start audio capture
        if not self.audio_capture.start():
            error_msg = (
                "Failed to start audio capture.\n\n"
                "Possible solutions:\n"
                "1. Go to Settings → Select a different audio device\n"
                "2. Try 'MacBook Air Microphone' for microphone input\n"
                "3. Install BlackHole for system audio capture\n"
                "4. Check System Settings → Privacy → Microphone permissions"
            )
            QMessageBox.warning(self, "Audio Capture Failed", error_msg)
            self.logger.error("Audio capture failed to start")
            return
        
        # Start transcription
        if not self.transcriber.start():
            error_msg = (
                "Failed to start transcription engine.\n\n"
                "This may be because:\n"
                "1. Local Whisper model is downloading (first time only)\n"
                "2. Check your internet connection\n"
                "3. Try restarting the app"
            )
            QMessageBox.warning(self, "Transcription Failed", error_msg)
            self.logger.error("Transcription engine failed to start")
            self.audio_capture.stop()
            return
        
        # Update UI
        self.is_transcribing = True
        self.meeting_start_time = datetime.now()
        self.transcript_segments = []
        self.full_transcript = ""
        self.last_summarized_index = 0  # Reset summary tracking
        self.transcript_text.clear()
        self.summary_text.clear()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.status_label.setText("Transcribing...")
        self.status_bar.showMessage("Transcription active")
        
        # Start mini-summary timer (every 30 seconds)
        self.mini_summary_timer.start(30000)
        
        # Start a diagnostic timer to check if audio is being received
        self.audio_check_timer = QTimer()
        self.audio_check_timer.timeout.connect(self.check_audio_reception)
        self.audio_check_timer.start(5000)  # Check after 5 seconds
        
        self.logger.info("Transcription started")
    
    def stop_transcription(self):
        """Stop transcription."""
        if not self.is_transcribing:
            return
        
        # Stop timers
        self.mini_summary_timer.stop()
        
        # Stop audio capture
        if self.audio_capture:
            self.audio_capture.stop()
        
        # Stop transcription
        if self.transcriber:
            self.transcriber.stop()
        
        # Generate final summary
        if self.summarizer and self.full_transcript:
            self.status_label.setText("Generating final summary...")
            threading.Thread(
                target=self.generate_final_summary,
                daemon=True
            ).start()
        
        # Stop audio check timer
        if hasattr(self, 'audio_check_timer'):
            self.audio_check_timer.stop()
        
        # Update UI
        self.is_transcribing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._audio_received_since_start = False
        
        self.status_label.setText("Stopped")
        self.status_bar.showMessage("Transcription stopped")
        
        self.logger.info("Transcription stopped")
    
    def on_audio_data(self, audio_data):
        """Handle audio data from capture.
        
        Args:
            audio_data: Audio numpy array
        """
        if self.transcriber and self.is_transcribing:
            self._audio_received_since_start = True
            self.transcriber.add_audio(audio_data)
    
    def on_transcription_callback(self, text: str, timestamp: float):
        """Handle transcription result.
        
        Args:
            text: Transcribed text
            timestamp: Timestamp
        """
        if text:
            self.signals.transcript_update.emit(text, timestamp)
    
    def on_transcript_update(self, text: str, timestamp: float):
        """Update transcript UI (called from signal).
        
        Args:
            text: Transcribed text
            timestamp: Timestamp
        """
        self.transcript_segments.append(text)
        self.full_transcript += text + " "
        
        # Update UI
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        self.transcript_text.append(f"[{time_str}] {text}")
        
        # Add to summarizer
        if self.summarizer:
            self.summarizer.add_transcript_segment(text)
        
        # Auto-scroll
        scrollbar = self.transcript_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def generate_mini_summary(self):
        """Generate mini-summary every 30 seconds (called by timer).
        
        Only processes new transcript segments since the last summary
        to avoid duplicate/redundant summaries.
        """
        if not self.summarizer or not self.transcript_segments:
            return
        
        # Only generate if there are new segments since last summary
        # This prevents overlapping summaries of the same content
        if len(self.transcript_segments) <= self.last_summarized_index:
            return
        
        # Run in background thread to avoid blocking UI
        threading.Thread(
            target=self._generate_mini_summary_thread,
            daemon=True
        ).start()
    
    def _generate_mini_summary_thread(self):
        """Generate mini-summary in background thread.
        
        Processes only new transcript segments and updates the summary display.
        Updates last_summarized_index to track which segments have been processed.
        """
        try:
            # Extract only new segments since last summary (prevents duplicates)
            new_segments = self.transcript_segments[self.last_summarized_index:]
            
            # Need at least 3 segments to generate a meaningful summary
            if len(new_segments) < 3:
                return
            
            # Generate summary from new segments only
            summary = self.summarizer.generate_mini_summary(new_segments)
            if summary and 'bullets' in summary:
                # Format bullets with timestamp
                bullets_text = "\n".join([f"• {b}" for b in summary['bullets']])
                time_str = datetime.now().strftime("%H:%M:%S")
                mini_summary = f"[{time_str}] Recent Updates:\n{bullets_text}\n\n"
                
                # Emit signal to update UI (thread-safe)
                self.signals.summary_update.emit(mini_summary)
                
                # Update index to mark these segments as summarized
                # This prevents them from being summarized again
                self.last_summarized_index = len(self.transcript_segments)
        except Exception as e:
            self.logger.error(f"Error generating mini-summary: {e}")
    
    def generate_final_summary(self):
        """Generate final comprehensive summary."""
        try:
            if not self.summarizer or not self.full_transcript:
                return
            
            summary = self.summarizer.generate_full_summary(self.full_transcript)
            
            if summary:
                # Update UI
                summary_text = self.format_summary(summary)
                self.signals.summary_update.emit(summary_text)
                
                # Export files
                if self.exporter and self.meeting_start_time:
                    try:
                        # Export transcript
                        transcript_path = self.exporter.export_transcript(
                            self.full_transcript,
                            self.meeting_start_time
                        )
                        
                        # Export summary
                        summary_md_path = self.exporter.export_summary_markdown(
                            summary,
                            self.meeting_start_time
                        )
                        
                        summary_pdf_path = self.exporter.export_summary_pdf(
                            summary,
                            self.full_transcript,
                            self.meeting_start_time
                        )
                        
                        self.signals.status_update.emit(
                            f"Files saved: {transcript_path.name}, "
                            f"{summary_md_path.name}, {summary_pdf_path.name}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error exporting files: {e}")
                        self.signals.status_update.emit(f"Error exporting files: {e}")
        except Exception as e:
            self.logger.error(f"Error generating final summary: {e}")
    
    def format_summary(self, summary: dict) -> str:
        """Format summary dictionary as text.
        
        Args:
            summary: Summary dictionary
            
        Returns:
            Formatted summary text
        """
        text = "=== MEETING SUMMARY ===\n\n"
        
        if 'summary' in summary:
            text += f"Overview:\n{summary['summary']}\n\n"
        
        if 'key_points' in summary and summary['key_points']:
            text += "Key Points:\n"
            for point in summary['key_points']:
                text += f"  • {point}\n"
            text += "\n"
        
        if 'decisions' in summary and summary['decisions']:
            text += "Decisions:\n"
            for decision in summary['decisions']:
                text += f"  • {decision}\n"
            text += "\n"
        
        if 'action_items' in summary and summary['action_items']:
            text += "Action Items:\n"
            for item in summary['action_items']:
                if isinstance(item, dict):
                    task = item.get('task', 'N/A')
                    assignee = item.get('assignee', 'TBD')
                    deadline = item.get('deadline', 'TBD')
                    text += f"  • {task} (Assignee: {assignee}, Deadline: {deadline})\n"
                else:
                    text += f"  • {item}\n"
            text += "\n"
        
        if 'people_mentioned' in summary and summary['people_mentioned']:
            text += "People Mentioned:\n"
            for person in summary['people_mentioned']:
                text += f"  • {person}\n"
            text += "\n"
        
        return text
    
    def on_summary_update(self, summary_text: str):
        """Update summary UI (called from signal).
        
        Args:
            summary_text: Summary text
        """
        self.summary_text.append(summary_text)
        scrollbar = self.summary_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_status_update(self, message: str):
        """Update status (called from signal).
        
        Args:
            message: Status message
        """
        self.status_bar.showMessage(message)
    
    def check_meeting_status(self):
        """Check if a meeting is active (for auto-detection)."""
        if self.is_transcribing:
            return
        
        try:
            if self.meeting_detector.is_meeting_active():
                app_name = self.meeting_detector.get_active_meeting_app()
                if app_name:
                    self.status_label.setText(f"Meeting detected: {app_name}")
                    # Auto-start after 2 seconds (only if not already trying)
                    if not hasattr(self, '_auto_starting'):
                        self._auto_starting = True
                        QTimer.singleShot(2000, lambda: self._try_auto_start(app_name))
        except Exception as e:
            self.logger.error(f"Error in meeting detection: {e}")
    
    def check_audio_reception(self):
        """Check if audio is being received after starting transcription."""
        if not self.is_transcribing:
            return
        
        if not self._audio_received_since_start:
            # Audio not being received - show helpful error message
            error_msg = (
                "No audio detected. Possible issues:\n\n"
                "1. Microphone permissions not granted\n"
                "   → Go to System Settings → Privacy & Security → Microphone\n"
                "   → Enable access for this app\n\n"
                "2. Wrong audio device selected\n"
                "   → Go to Settings → Select correct audio device\n"
                "   → Try 'MacBook Air Microphone' for microphone input\n\n"
                "3. For system audio capture, install BlackHole\n"
                "   → https://github.com/ExistentialAudio/BlackHole"
            )
            QMessageBox.warning(self, "No Audio Detected", error_msg)
            self.logger.warning("No audio received after 5 seconds - checking permissions and device")
            self.audio_check_timer.stop()  # Only show once
        else:
            # Audio is working, stop the check timer
            self.audio_check_timer.stop()
            self.logger.info("Audio reception confirmed - transcription is working")
    
    def _try_auto_start(self, app_name: str):
        """Try to auto-start transcription."""
        self._auto_starting = False
        if not self.is_transcribing:
            try:
                self.start_transcription()
            except Exception as e:
                self.logger.error(f"Auto-start failed: {e}")
                self.status_label.setText(f"Auto-start failed: {e}")
    
    def show_settings(self):
        """Show settings window."""
        dialog = SettingsWindow(self, self.settings)
        
        # Populate audio devices
        devices = self.device_manager.get_all_devices()
        dialog.set_audio_devices(devices)
        
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.save_settings()
            
            # Reinitialize components
            self.setup_audio()
            self.setup_transcription()
            self.setup_summarization()
            
            QMessageBox.information(
                self,
                "Settings",
                "Settings saved. Restart transcription to apply changes."
            )
    
    def export_transcript(self):
        """Export current transcript."""
        if not self.full_transcript:
            QMessageBox.information(self, "Export", "No transcript to export.")
            return
        
        if self.exporter:
            try:
                path = self.exporter.export_transcript(
                    self.full_transcript,
                    self.meeting_start_time or datetime.now()
                )
                QMessageBox.information(
                    self,
                    "Export",
                    f"Transcript exported to:\n{path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")
    
    def export_summary(self):
        """Export current summary."""
        summary_text = self.summary_text.toPlainText()
        if not summary_text or "MEETING SUMMARY" not in summary_text:
            QMessageBox.information(self, "Export", "No summary to export.")
            return
        
        # For now, just show message
        QMessageBox.information(
            self,
            "Export",
            "Summary will be exported automatically when transcription stops."
        )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Call Summarizer",
            "Call Summarizer v1.0.0\n\n"
            "Automatically transcribe and summarize meeting calls.\n\n"
            "Supports:\n"
            "• Zoom\n"
            "• Google Meet\n"
            "• Microsoft Teams"
        )
    
    def load_settings(self) -> dict:
        """Load settings from file.
        
        Returns:
            Settings dictionary
        """
        settings_file = Path.home() / "CallSummaries" / "settings.json"
        
        if settings_file.exists():
            try:
                import json
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading settings: {e}")
        
        # Default settings - Using Gemini by default
        return {
            'audio_device': 'Default',
            'auto_detect_meetings': True,
            'transcription_method': 'local_whisper',  # Free, no API key needed
            'transcription_model': 'small',  # Better for accent recognition
            'openai_api_key': '',
            'summary_provider': 'gemini',  # Default to Gemini
            'summary_model': 'gemini-2.5-flash',  # Better free tier limits
            'gemini_api_key': '',
            'output_directory': str(Path.home() / "CallSummaries"),
        }
    
    def save_settings(self):
        """Save settings to file."""
        settings_file = Path.home() / "CallSummaries" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import json
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.is_transcribing:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Transcription is active. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_transcription()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

