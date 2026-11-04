"""DGM's common SDK; not a manufacturer-issued or hardware-certified SDK."""
from .catalog import devices, describe, profile_template, doctor, ProfileError, UnsupportedDevice
from .profiles import load_profile, check_profile
from .session import open_device, DeviceSession, SessionError
from .errors import error_details
from .virtual_lab import VirtualLab, HardwareLab
from .virtual_world import Scenario, Fault
from .virtual_recipe import WlanScan, measure_wlan

__version__ = "0.2.0"
__all__ = ["devices", "describe", "profile_template", "doctor", "load_profile", "check_profile",
           "open_device", "DeviceSession", "ProfileError", "UnsupportedDevice", "SessionError", "error_details",
           "VirtualLab", "HardwareLab", "Scenario", "Fault", "WlanScan", "measure_wlan"]
