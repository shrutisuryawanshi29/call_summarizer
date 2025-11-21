"""Main application entry point for Call Summarizer."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .utils.logger import setup_logger


def main():
    """Main application entry point.
    
    Initializes the Qt application, loads the theme stylesheet,
    creates the main window, and starts the event loop.
    """
    # Initialize logging system for debugging and error tracking
    logger = setup_logger()
    logger.info("Starting Call Summarizer")
    
    # Create Qt application instance (required for all Qt widgets)
    app = QApplication(sys.argv)
    app.setApplicationName("Call Summarizer")
    app.setOrganizationName("CallSummarizer")
    
    # Load custom dark theme stylesheet if available
    try:
        theme_path = Path(__file__).parent / "ui" / "theme.qss"
        if theme_path.exists():
            with open(theme_path, 'r') as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        logger.warning(f"Could not load theme: {e}")
    
    # Create and display the main application window
    window = MainWindow()
    window.show()
    
    # Start the Qt event loop (blocks until application exits)
    sys.exit(app.exec())


# Entry point when running this module directly
if __name__ == "__main__":
    main()

