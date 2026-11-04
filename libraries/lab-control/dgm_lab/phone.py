"""Reuse source-scoped OEM AT profiles; do not grant unverified latest-phone support."""
from contextlib import contextmanager
from .core import UnsupportedInstrument


@contextmanager
def phone_serial(*, port, baudrate, profile_path):
    from dgm_rf import Controller, Profile
    from dgm_rf.core import SerialTransport
    profile = Profile.load(profile_path)
    if profile.simulation_only or not profile.model or not profile.build or not profile.evidence_notes:
        raise UnsupportedInstrument('Real AT I/O requires a commissioned model/build/argument profile with evidence')
    transport = SerialTransport(port, baudrate)
    try:
        yield Controller(transport, profile)
    finally:
        # The caller must use phone.wlan_tx()/phone.session() so RF cleanup precedes closing.
        transport.close()


def measure_during_phone_tx(*, phone, config, acquire):
    """phone is dgm_rf.Controller; setup/stop remain its validated command-plan responsibility."""
    with phone.wlan_tx(config):
        return acquire()


def latest_phone_support(model):
    return dict(model=model, hardware_ready=False, direct_tx_supported=False,
                reason='Current OEM RF test firmware/authorization/argument mapping not publicly verified',
                required=['exact model and build', 'OEM test application or SDK',
                          'per-radio numeric argument table', 'verified TX start/stop response and RF cessation'])
