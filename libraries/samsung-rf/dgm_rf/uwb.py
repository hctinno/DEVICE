"""Samsung S918NKSU1AWC8 periodic TX, not a universal Samsung dialect."""
from contextlib import contextmanager
from dataclasses import dataclass
from .core import CommandRejected


@dataclass(frozen=True)
class UwbTxConfig:
    channel: int
    antenna: int
    gap: int
    window: int
    packets: int
    power_code: int | None = None
    calibrated_power: bool = False


def uwb_tx_plan(config):
    if type(config.antenna) is not int or config.antenna not in (0, 1):
        raise CommandRejected('UWB antenna must be 0 or 1')
    if type(config.calibrated_power) is not bool:
        raise CommandRejected('calibrated_power must be Boolean')
    if config.calibrated_power == (config.power_code is not None):
        raise CommandRejected('Choose exactly one: power_code or calibrated_power')
    setup = [
        ('s23_uwb_off', {}),  # Clear an existing test session before reconfiguration.
        ('s23_uwb_on', {}),
        ('s23_uwb_channel', {'value': config.channel}),
        ('s23_uwb_antenna', {'value': 'TX_ANT_'+str(config.antenna)}),
        ('s23_uwb_timing', {'gap': config.gap, 'window': config.window, 'packets': config.packets}),
        ('s23_uwb_tx_calibrated', {}) if config.calibrated_power else ('s23_uwb_tx', {'value': config.power_code}),
    ]
    return setup, [('s23_uwb_off', {})]


@contextmanager
def uwb_tx(controller, config, *, cancelled=None):
    setup, cleanup = uwb_tx_plan(config)
    with controller.session(setup, cleanup, cancelled=cancelled):
        yield controller
