"""DGM's common SDK; not a manufacturer-issued or hardware-certified SDK."""
from .catalog import devices, describe, profile_template, doctor, ProfileError, UnsupportedDevice
from .profiles import load_profile, check_profile
from .session import open_device, DeviceSession, SessionError
from .errors import error_details

__version__ = "0.1.0"
__all__ = ["devices", "describe", "profile_template", "doctor", "load_profile", "check_profile",
           "open_device", "DeviceSession", "ProfileError", "UnsupportedDevice", "SessionError", "error_details"]
