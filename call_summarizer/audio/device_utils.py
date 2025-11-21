"""Audio device enumeration and utilities."""

import platform
import sounddevice as sd
from typing import List, Dict, Optional, Tuple


class AudioDeviceManager:
    """Manages audio device enumeration and selection."""
    
    def __init__(self):
        self.system = platform.system()
        self._devices_cache: Optional[List[Dict]] = None
    
    def get_all_devices(self) -> List[Dict]:
        """Get all available audio devices.
        
        Returns:
            List of device dictionaries with id, name, channels, samplerate
        """
        if self._devices_cache is None:
            self._refresh_devices()
        return self._devices_cache or []
    
    def _refresh_devices(self):
        """Refresh the devices cache."""
        try:
            devices = sd.query_devices()
            self._devices_cache = []
            
            for i, device in enumerate(devices):
                device_info = {
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'samplerate': int(device['default_samplerate']),
                    'is_input': device['max_input_channels'] > 0,
                    'is_output': device['max_output_channels'] > 0,
                }
                self._devices_cache.append(device_info)
        except Exception as e:
            print(f"Error refreshing devices: {e}")
            self._devices_cache = []
    
    def get_loopback_devices(self) -> List[Dict]:
        """Get available loopback devices for system audio capture.
        
        Returns:
            List of loopback-capable devices
        """
        devices = self.get_all_devices()
        loopback_devices = []
        
        if self.system == "Windows":
            # WASAPI loopback devices have "Loopback" in name or are output devices
            for device in devices:
                if device['is_output'] or 'loopback' in device['name'].lower():
                    loopback_devices.append(device)
        elif self.system == "Darwin":
            # macOS - look for BlackHole or Multi-Output
            for device in devices:
                name_lower = device['name'].lower()
                if 'blackhole' in name_lower or 'multi-output' in name_lower:
                    loopback_devices.append(device)
        
        return loopback_devices
    
    def get_default_loopback_device(self) -> Optional[Dict]:
        """Get the default loopback device for the current platform.
        
        Returns:
            Default loopback device or None
        """
        loopback_devices = self.get_loopback_devices()
        
        if not loopback_devices:
            return None
        
        # Prefer devices with "loopback" in name on Windows
        if self.system == "Windows":
            for device in loopback_devices:
                if 'loopback' in device['name'].lower():
                    return device
        
        # Return first available
        return loopback_devices[0]
    
    def find_device_by_name(self, name: str) -> Optional[Dict]:
        """Find a device by name (partial match).
        
        Args:
            name: Device name to search for
            
        Returns:
            Matching device or None
        """
        devices = self.get_all_devices()
        name_lower = name.lower()
        
        for device in devices:
            if name_lower in device['name'].lower():
                return device
        
        return None
    
    def get_device_info(self, device_id: int) -> Optional[Dict]:
        """Get information about a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device info dictionary or None
        """
        devices = self.get_all_devices()
        for device in devices:
            if device['id'] == device_id:
                return device
        return None
    
    def check_macos_blackhole(self) -> Tuple[bool, str]:
        """Check if BlackHole is installed on macOS.
        
        Returns:
            Tuple of (is_installed, message)
        """
        if self.system != "Darwin":
            return True, "Not macOS"
        
        devices = self.get_all_devices()
        for device in devices:
            if 'blackhole' in device['name'].lower():
                return True, "BlackHole is installed"
        
        message = (
            "BlackHole is not installed. For system audio capture on macOS, "
            "please install BlackHole:\n"
            "https://github.com/ExistentialAudio/BlackHole\n\n"
            "Or use Multi-Output Device in Audio MIDI Setup."
        )
        return False, message

