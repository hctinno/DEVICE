"""NFC16 PRBS protected broadcast backend. Dispatch is not RF acknowledgement."""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import files
import json
import math
import re
import subprocess
import threading
import time
from .core import CommandRejected, RFError, CleanupError


def nfc_prbs_spec():
    return json.loads(files('dgm_rf').joinpath('data/nfc-prbs.json').read_text(encoding='utf-8'))


@dataclass(frozen=True)
class NfcRequest:
    request_id: int
    tech_index: int | None = None
    rate_index: int | None = None

    def __post_init__(self):
        if type(self.request_id) is not int or self.request_id not in (31,32):
            raise CommandRejected('Only source-confirmed PRBS request IDs 31/32 are accepted')
        if self.request_id == 31:
            if any(type(v) is not int or v not in (0,1,2) for v in (self.tech_index,self.rate_index)):
                raise CommandRejected('TECH and RATE indices must each be 0, 1 or 2')
        elif self.tech_index is not None or self.rate_index is not None:
            raise CommandRejected('STOP request has no TECH/RATE parameters')

    @property
    def nci_payload(self):
        # Payload only; not an AT string, full NCI frame, or direct USB packet.
        return bytes([0x21, 1, self.tech_index+1, self.rate_index+1]) if self.request_id == 31 else bytes([0x21,0])

    def adb_argv(self, serial, *, adb='adb'):
        if not isinstance(serial,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+',serial) or serial.startswith('-'):
            raise CommandRejected('Explicit, valid ADB device serial required')
        spec=nfc_prbs_spec()
        args=[adb,'-s',serial,'shell','am','broadcast','-a',spec['action'],'-p',spec['service'],
              '--ei',spec['extra_prefix']+'ID',str(self.request_id)]
        if self.request_id == 31:
            args += ['--ei',spec['extra_prefix']+'TECH',str(self.tech_index),
                     '--ei',spec['extra_prefix']+'RATE',str(self.rate_index)]
        return args


@dataclass(frozen=True)
class NfcProfile:
    model: str
    build: str
    apk_sha256: str
    # Caller has independently checked the sending UID's OEM permission.
    sender_permission_verified: bool = False


class AdbNfcTransport:
    """Requires an already provisioned lab identity; does not grant permissions."""
    simulated=False

    def __init__(self, serial, profile, *, adb='adb', runner=subprocess.run):
        spec=nfc_prbs_spec()
        if (not profile.model or not profile.build or profile.apk_sha256.lower()!=spec['apk_sha256']
                or profile.sender_permission_verified is not True):
            raise CommandRejected('Matching NFC APK and independently verified sender permission required')
        NfcRequest(32).adb_argv(serial,adb=adb)
        self.serial,self.adb,self.runner=serial,adb,runner

    def dispatch(self, request, timeout):
        result=self.runner(request.adb_argv(self.serial,adb=self.adb),capture_output=True,
                           text=True,encoding='utf-8',errors='replace',timeout=timeout,shell=False)
        output=result.stdout+'\n'+result.stderr
        if result.returncode or re.search(r'permission denial|securityexception|error:|exception occurred',output,re.I):
            raise RFError('NFC broadcast dispatch failed: '+output)
        # Even "Broadcast completed: result=0" does not prove receiver execution.
        return output


class SimulatedNfcTransport:
    simulated=True
    def __init__(self):
        self.sent=[]
    def dispatch(self, request, timeout):
        self.sent.append(request)
        return 'SIMULATED_DISPATCH_ONLY'


class NfcPrbsController:
    def __init__(self, transport):
        self.transport=transport
        self.log=[]
        self.lock=threading.RLock()

    def _dispatch(self, request, timeout):
        event=dict(request_id=request.request_id,tech_index=request.tech_index,rate_index=request.rate_index,
                   timestamp=time.time(),status='attempted',simulated=self.transport.simulated,rf_measured=False)
        self.log.append(event)
        try:
            event['raw_response']=self.transport.dispatch(request,timeout)
            event['status']='dispatched_unconfirmed'
        except BaseException as exc:
            event.update(status='failed',error=repr(exc))
            raise
        return event

    @contextmanager
    def session(self, tech_index, rate_index, *, verify_started, verify_stopped, timeout=15.0, cancelled=None):
        """Verification callbacks receive a time budget and must return exactly True.

        Use an instrument or an authenticated device helper, not ADB stdout, for
        these callbacks. They are required even in simulation to expose the contract.
        """
        start=NfcRequest(31,tech_index,rate_index)
        stop=NfcRequest(32)
        if not math.isfinite(timeout) or timeout<=0 or not callable(verify_started) or not callable(verify_stopped):
            raise CommandRejected('Positive timeout and both verification callbacks required')
        with self.lock:
            if cancelled and cancelled.is_set():
                raise InterruptedError('NFC PRBS cancelled before dispatch')
            original=None
            try:
                event=self._dispatch(start,timeout)
                if verify_started(timeout) is not True:
                    raise RFError('NFC PRBS start unconfirmed')
                event['status']='confirmed_by_callback' if not self.transport.simulated else 'simulated_confirmation'
                if cancelled and cancelled.is_set():
                    raise InterruptedError('NFC PRBS cancelled')
                yield self
            except BaseException as exc:
                original=exc
                raise
            finally:
                try:
                    event=self._dispatch(stop,timeout)
                    if verify_stopped(timeout) is not True:
                        raise RFError('NFC PRBS stop unconfirmed')
                    event['status']='confirmed_by_callback' if not self.transport.simulated else 'simulated_confirmation'
                except BaseException as exc:
                    cleanup=CleanupError([repr(exc)])
                    if original is not None:
                        raise BaseExceptionGroup('NFC operation failed and RF OFF is unconfirmed',[original,cleanup]) from None
                    raise cleanup from exc
