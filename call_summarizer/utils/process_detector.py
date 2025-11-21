"""Process detection for meeting applications."""

import platform
import psutil
import re
from typing import List, Optional, Set
from pathlib import Path


class MeetingDetector:
    """Detects active meeting applications."""
    
    # Process names to check for
    ZOOM_PROCESSES = ['zoom', 'zoom.us', 'ZoomOpener', 'zTray']
    TEAMS_PROCESSES = ['Teams', 'ms-teams', 'Microsoft Teams']
    MEET_PROCESSES = ['chrome', 'chromium', 'firefox', 'safari', 'edge']
    
    # Window title patterns
    MEET_TITLE_PATTERNS = [
        r'meet\.google\.com',
        r'zoom\.us',
        r'teams\.microsoft\.com',
        r'Meeting',
        r'Call',
    ]
    
    def __init__(self):
        self.system = platform.system()
        self._last_window_titles: Set[str] = set()
    
    def is_meeting_active(self) -> bool:
        """Check if a meeting application is currently active.
        
        Returns:
            True if a meeting is detected, False otherwise
        """
        # Check for process names
        if self._check_processes():
            return True
        
        # Check for browser tabs with meeting URLs
        if self._check_browser_tabs():
            return True
        
        return False
    
    def _check_processes(self) -> bool:
        """Check if meeting application processes are running."""
        all_processes = [p.name().lower() for p in psutil.process_iter(['name'])]
        
        # Check Zoom
        for zoom_proc in self.ZOOM_PROCESSES:
            if any(zoom_proc.lower() in proc for proc in all_processes):
                return True
        
        # Check Teams
        for teams_proc in self.TEAMS_PROCESSES:
            if any(teams_proc.lower() in proc for proc in all_processes):
                return True
        
        return False
    
    def _check_browser_tabs(self) -> bool:
        """Check browser windows/tabs for meeting URLs."""
        try:
            if self.system == "Darwin":  # macOS
                return self._check_macos_browser_tabs()
            elif self.system == "Windows":
                return self._check_windows_browser_tabs()
            else:
                # Linux - basic check
                return False
        except Exception:
            return False
    
    def _check_macos_browser_tabs(self) -> bool:
        """Check browser tabs on macOS using AppleScript."""
        try:
            import subprocess
            
            # Check Chrome/Chromium
            script = '''
            tell application "Google Chrome"
                repeat with w in windows
                    repeat with t in tabs of w
                        set urlText to URL of t
                        if urlText contains "meet.google.com" or urlText contains "zoom.us" or urlText contains "teams.microsoft.com" then
                            return true
                        end if
                    end repeat
                end repeat
            end tell
            return false
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and 'true' in result.stdout.lower():
                return True
        except Exception:
            pass
        
        return False
    
    def _check_windows_browser_tabs(self) -> bool:
        """Check browser tabs on Windows."""
        try:
            import win32gui
            import win32process
            
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    for pattern in self.MEET_TITLE_PATTERNS:
                        if re.search(pattern, window_title, re.IGNORECASE):
                            windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            return len(windows) > 0
        except ImportError:
            # pywin32 not available, skip
            return False
        except Exception:
            return False
    
    def get_active_meeting_app(self) -> Optional[str]:
        """Get the name of the active meeting application.
        
        Returns:
            Name of the meeting app or None
        """
        all_processes = [p.name().lower() for p in psutil.process_iter(['name'])]
        
        for zoom_proc in self.ZOOM_PROCESSES:
            if any(zoom_proc.lower() in proc for proc in all_processes):
                return "Zoom"
        
        for teams_proc in self.TEAMS_PROCESSES:
            if any(teams_proc.lower() in proc for proc in all_processes):
                return "Microsoft Teams"
        
        if self._check_browser_tabs():
            return "Google Meet (Browser)"
        
        return None

