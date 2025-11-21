"""Settings window for the application."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QCheckBox, QGroupBox, QFileDialog,
    QFormLayout, QMessageBox, QGridLayout, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from pathlib import Path
import json


class SettingsWindow(QDialog):
    """Settings dialog window."""
    
    def __init__(self, parent=None, settings: dict = None):
        """Initialize settings window.
        
        Args:
            parent: Parent widget
            settings: Current settings dictionary
        """
        super().__init__(parent)
        self.settings = settings or {}
        self.setWindowTitle("Settings")
        
        # Set minimum size to prevent overlapping
        # Minimum width: label column (180) + widget column (400) + margins (60) + spacing (40) = ~680
        # Minimum height: all rows + margins + buttons = ~650
        self.setMinimumWidth(700)
        self.setMinimumHeight(650)
        
        # Set default size (larger to show everything properly)
        # This ensures the window opens at a proper size, not minimized
        self.resize(750, 700)
        
        # Make window resizable
        self.setSizeGripEnabled(True)
        
        self.init_ui()
        self.load_settings()
        
        # Force window to show at proper size after UI is initialized
        # This prevents the window from opening in a minimized/collapsed state
        self.adjustSize()
        if self.width() < 700 or self.height() < 650:
            self.resize(max(750, self.width()), max(700, self.height()))
        
        # Ensure window is shown in normal state (not minimized)
        if self.isMinimized():
            self.showNormal()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Common label column width - wide enough for longest label
        LABEL_COLUMN_WIDTH = 180
        
        # Audio Settings
        audio_group = QGroupBox("Audio Settings")
        audio_group.setContentsMargins(15, 15, 15, 15)
        audio_layout = QGridLayout()
        audio_layout.setSpacing(0)  # We'll control spacing with row heights
        audio_layout.setVerticalSpacing(20)  # Space between rows
        audio_layout.setHorizontalSpacing(15)  # Space between label and widget
        audio_layout.setColumnMinimumWidth(0, LABEL_COLUMN_WIDTH)
        audio_layout.setColumnStretch(1, 1)
        audio_layout.setRowMinimumHeight(0, 40)  # Explicit row height
        audio_layout.setRowMinimumHeight(1, 40)  # Explicit row height
        
        audio_device_label = QLabel("Audio Device:")
        audio_device_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.setMinimumWidth(350)
        self.audio_device_combo.setMinimumHeight(35)
        self.audio_device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.audio_device_combo.setEditable(False)
        # Connect to showPopup to resize dropdown view
        self.audio_device_combo.showPopup = lambda: self._show_popup(self.audio_device_combo)
        audio_layout.addWidget(audio_device_label, 0, 0)
        audio_layout.addWidget(self.audio_device_combo, 0, 1)
        
        self.auto_detect_checkbox = QCheckBox("Auto-detect meetings")
        self.auto_detect_checkbox.setToolTip(
            "Automatically start transcription when a meeting is detected"
        )
        self.auto_detect_checkbox.setMinimumHeight(35)
        audio_layout.addWidget(self.auto_detect_checkbox, 1, 1)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Transcription Settings
        trans_group = QGroupBox("Transcription Settings")
        trans_group.setContentsMargins(15, 15, 15, 15)
        trans_layout = QGridLayout()
        trans_layout.setSpacing(0)  # We'll control spacing with row heights
        trans_layout.setVerticalSpacing(20)  # Space between rows
        trans_layout.setHorizontalSpacing(15)  # Space between label and widget
        trans_layout.setColumnMinimumWidth(0, LABEL_COLUMN_WIDTH)
        trans_layout.setColumnStretch(1, 1)
        trans_layout.setRowMinimumHeight(0, 40)  # Explicit row height
        trans_layout.setRowMinimumHeight(1, 40)  # Explicit row height
        trans_layout.setRowMinimumHeight(2, 40)  # Explicit row height
        
        self.trans_method_combo = QComboBox()
        self.trans_method_combo.setMinimumWidth(350)
        self.trans_method_combo.setMinimumHeight(35)
        self.trans_method_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.trans_method_combo.setEditable(False)
        self.trans_method_combo.showPopup = lambda: self._show_popup(self.trans_method_combo)
        self.trans_method_combo.addItems([
            "Local Whisper (Free)",
            "OpenAI Whisper API"
        ])
        trans_method_label = QLabel("Transcription Method:")
        trans_method_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trans_layout.addWidget(trans_method_label, 0, 0)
        trans_layout.addWidget(self.trans_method_combo, 0, 1)
        
        self.trans_model_combo = QComboBox()
        self.trans_model_combo.setMinimumWidth(350)
        self.trans_model_combo.setMinimumHeight(35)
        self.trans_model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.trans_model_combo.setEditable(False)
        self.trans_model_combo.showPopup = lambda: self._show_popup(self.trans_model_combo)
        self.trans_model_combo.addItems([
            "small",
            "base",
            "medium",
            "large",
            "whisper-1"
        ])
        trans_model_label = QLabel("Model:")
        trans_model_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trans_layout.addWidget(trans_model_label, 1, 0)
        trans_layout.addWidget(self.trans_model_combo, 1, 1)
        
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setPlaceholderText("Only needed for OpenAI Whisper API")
        self.openai_key_edit.setMinimumWidth(350)
        self.openai_key_edit.setMinimumHeight(35)
        self.openai_key_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        openai_key_label = QLabel("OpenAI API Key:")
        openai_key_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        trans_layout.addWidget(openai_key_label, 2, 0)
        trans_layout.addWidget(self.openai_key_edit, 2, 1)
        
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)
        
        # Summarization Settings
        summary_group = QGroupBox("Summarization Settings")
        summary_group.setContentsMargins(15, 15, 15, 15)
        summary_layout = QGridLayout()
        summary_layout.setSpacing(0)  # We'll control spacing with row heights
        summary_layout.setVerticalSpacing(20)  # Space between rows
        summary_layout.setHorizontalSpacing(15)  # Space between label and widget
        summary_layout.setColumnMinimumWidth(0, LABEL_COLUMN_WIDTH)
        summary_layout.setColumnStretch(1, 1)
        summary_layout.setRowMinimumHeight(0, 40)  # Explicit row height
        summary_layout.setRowMinimumHeight(1, 40)  # Explicit row height
        summary_layout.setRowMinimumHeight(2, 40)  # Explicit row height
        
        self.summary_provider_combo = QComboBox()
        self.summary_provider_combo.setMinimumWidth(350)
        self.summary_provider_combo.setMinimumHeight(35)
        self.summary_provider_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.summary_provider_combo.setEditable(False)
        self.summary_provider_combo.showPopup = lambda: self._show_popup(self.summary_provider_combo)
        self.summary_provider_combo.addItems([
            "Gemini",
            "OpenAI"
        ])
        provider_label = QLabel("Provider:")
        provider_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        summary_layout.addWidget(provider_label, 0, 0)
        summary_layout.addWidget(self.summary_provider_combo, 0, 1)
        
        self.summary_model_combo = QComboBox()
        self.summary_model_combo.setMinimumWidth(350)
        self.summary_model_combo.setMinimumHeight(35)
        self.summary_model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.summary_model_combo.setEditable(False)
        self.summary_model_combo.showPopup = lambda: self._show_popup(self.summary_model_combo)
        self.summary_model_combo.addItems([
            "gemini-2.5-flash",
            "gemini-3-pro-preview",
            "gemini-pro",
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-3.5-turbo"
        ])
        summary_model_label = QLabel("Model:")
        summary_model_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        summary_layout.addWidget(summary_model_label, 1, 0)
        summary_layout.addWidget(self.summary_model_combo, 1, 1)
        
        self.gemini_key_edit = QLineEdit()
        self.gemini_key_edit.setEchoMode(QLineEdit.Password)
        self.gemini_key_edit.setPlaceholderText("Enter Gemini API key")
        self.gemini_key_edit.setMinimumWidth(350)
        self.gemini_key_edit.setMinimumHeight(35)
        self.gemini_key_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        gemini_key_label = QLabel("Gemini API Key:")
        gemini_key_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        summary_layout.addWidget(gemini_key_label, 2, 0)
        summary_layout.addWidget(self.gemini_key_edit, 2, 1)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Output Settings
        output_group = QGroupBox("Output Settings")
        output_group.setContentsMargins(15, 15, 15, 15)
        output_layout = QGridLayout()
        output_layout.setSpacing(0)  # We'll control spacing with row heights
        output_layout.setVerticalSpacing(20)  # Space between rows
        output_layout.setHorizontalSpacing(15)  # Space between label and widget
        output_layout.setColumnMinimumWidth(0, LABEL_COLUMN_WIDTH)
        output_layout.setColumnStretch(1, 1)
        output_layout.setRowMinimumHeight(0, 40)  # Explicit row height
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Default: ~/CallSummaries")
        self.output_dir_edit.setMinimumWidth(300)
        self.output_dir_edit.setMinimumHeight(35)
        self.output_dir_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setMinimumWidth(100)
        browse_btn.setMinimumHeight(35)
        browse_btn.clicked.connect(self.browse_output_dir)
        
        output_dir_layout = QHBoxLayout()
        output_dir_layout.setSpacing(10)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(browse_btn)
        
        output_dir_widget = QWidget()
        output_dir_widget.setLayout(output_dir_layout)
        
        save_dir_label = QLabel("Save Directory:")
        save_dir_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        output_layout.addWidget(save_dir_label, 0, 0)
        output_layout.addWidget(output_dir_widget, 0, 1)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load settings into UI."""
        # Audio device
        device_name = self.settings.get('audio_device', '')
        if device_name:
            index = self.audio_device_combo.findText(device_name)
            if index >= 0:
                self.audio_device_combo.setCurrentIndex(index)
        
        # Auto-detect
        self.auto_detect_checkbox.setChecked(
            self.settings.get('auto_detect_meetings', True)
        )
        
        # Transcription method
        trans_method = self.settings.get('transcription_method', 'local_whisper')
        if trans_method == 'local_whisper':
            self.trans_method_combo.setCurrentIndex(0)
        elif trans_method == 'openai_whisper_api':
            self.trans_method_combo.setCurrentIndex(1)
        
        # Transcription model
        trans_model = self.settings.get('transcription_model', 'small')
        # Find model in combo box (exact match or starts with)
        index = self.trans_model_combo.findText(trans_model, Qt.MatchStartsWith)
        if index >= 0:
            self.trans_model_combo.setCurrentIndex(index)
        else:
            # Default to small if not found
            self.trans_model_combo.setCurrentIndex(0)
        
        # OpenAI key
        self.openai_key_edit.setText(self.settings.get('openai_api_key', ''))
        
        # Summary provider
        summary_provider = self.settings.get('summary_provider', 'gemini')
        if summary_provider == 'gemini':
            self.summary_provider_combo.setCurrentIndex(0)
        elif summary_provider == 'openai':
            self.summary_provider_combo.setCurrentIndex(1)
        
        # Summary model
        summary_model = self.settings.get('summary_model', 'gemini-2.5-flash')
        # Find model (exact match or starts with)
        index = self.summary_model_combo.findText(summary_model, Qt.MatchStartsWith)
        if index >= 0:
            self.summary_model_combo.setCurrentIndex(index)
        else:
            # Default to gemini-2.5-flash
            self.summary_model_combo.setCurrentIndex(0)
        
        # Gemini key
        self.gemini_key_edit.setText(self.settings.get('gemini_api_key', ''))
        
        # Output directory
        output_dir = self.settings.get('output_directory', '')
        self.output_dir_edit.setText(output_dir)
    
    def save_settings(self):
        """Save settings from UI."""
        # Validate API keys if needed
        trans_method = self.trans_method_combo.currentText()
        if "OpenAI Whisper API" in trans_method and not self.openai_key_edit.text():
            QMessageBox.warning(
                self,
                "Warning",
                "OpenAI API key is required for OpenAI Whisper API."
            )
            return
        
        summary_provider = self.summary_provider_combo.currentText()
        if "Gemini" in summary_provider and not self.gemini_key_edit.text():
            QMessageBox.warning(
                self,
                "Warning",
                "Gemini API key is required for Gemini summarization."
            )
            return
        
        # Determine transcription method
        if "OpenAI Whisper API" in trans_method:
            trans_method_str = 'openai_whisper_api'
        else:
            trans_method_str = 'local_whisper'
        
        # Get transcription model (already clean, no descriptions)
        trans_model = self.trans_model_combo.currentText().strip()
        
        # Determine summary provider
        if "Gemini" in summary_provider:
            summary_provider_str = 'gemini'
        else:
            summary_provider_str = 'openai'
        
        # Get summary model (already clean)
        summary_model = self.summary_model_combo.currentText().strip()
        
        # Save settings
        self.settings = {
            'audio_device': self.audio_device_combo.currentText(),
            'auto_detect_meetings': self.auto_detect_checkbox.isChecked(),
            'transcription_method': trans_method_str,
            'transcription_model': trans_model,
            'openai_api_key': self.openai_key_edit.text(),
            'summary_provider': summary_provider_str,
            'summary_model': summary_model,
            'gemini_api_key': self.gemini_key_edit.text(),
            'output_directory': self.output_dir_edit.text() or str(Path.home() / "CallSummaries"),
        }
        
        self.accept()
    
    def _show_popup(self, combo_box: QComboBox):
        """Show popup with proper width for combo box."""
        # Call the original showPopup
        QComboBox.showPopup(combo_box)
        # Get the view and set minimum width
        view = combo_box.view()
        if view:
            # Ensure dropdown is at least as wide as the combo box, minimum 350px
            min_width = max(combo_box.width(), 350)
            view.setMinimumWidth(min_width)
            # Resize the popup if needed
            popup = combo_box.view().window()
            if popup and popup.width() < min_width:
                popup.resize(min_width, popup.height())
    
    def browse_output_dir(self):
        """Browse for output directory."""
        current_dir = self.output_dir_edit.text() or str(Path.home())
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current_dir
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def get_settings(self) -> dict:
        """Get current settings.
        
        Returns:
            Settings dictionary
        """
        return self.settings
    
    def set_audio_devices(self, devices: list):
        """Set available audio devices.
        
        Args:
            devices: List of device dictionaries
        """
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("Default")
        for device in devices:
            self.audio_device_combo.addItem(device['name'], device)

