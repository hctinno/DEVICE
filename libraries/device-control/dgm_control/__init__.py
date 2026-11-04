"""DGM's common SDK; not a manufacturer-issued or hardware-certified SDK."""
from .catalog import devices, describe, profile_template, doctor, ProfileError, UnsupportedDevice
from .profiles import load_profile, check_profile
from .session import open_device, DeviceSession, SessionError
from .errors import error_details
from .virtual_lab import VirtualLab, HardwareLab
from .virtual_world import Scenario, Fault
from .virtual_recipe import WlanScan, measure_wlan
from .hardware_run import run_hardware, check_hardware, load_hardware_inputs, plan_from_dict
from .radio_contracts import radio_catalog, radio_template, check_radio, nfc_profile_template
from .radio_run import run_radio, load_radio_profiles
from .evaluation import Evaluation, evaluation_template
from .receiver_measurement import detector_catalog, measurement_template, validate_measurement

__version__ = "0.9.0"
__all__ = ["devices", "describe", "profile_template", "doctor", "load_profile", "check_profile",
           "open_device", "DeviceSession", "ProfileError", "UnsupportedDevice", "SessionError", "error_details",
           "VirtualLab", "HardwareLab", "Scenario", "Fault", "WlanScan", "measure_wlan",
           "run_hardware", "check_hardware", "load_hardware_inputs", "plan_from_dict",
           "radio_catalog", "radio_template", "check_radio", "nfc_profile_template", "run_radio", "load_radio_profiles",
           "Evaluation", "evaluation_template", "detector_catalog", "measurement_template", "validate_measurement"]
