"""Execute the existing source-reviewed CMW500 LTE FDD RMC plan, with bounded state waits."""
import time
from .analyzers import RS
from .core import Scpi, InstrumentError, number, managed_run


class CmwLte(Scpi):
    source_id = 'rs-cmw-lte'

    def __init__(self, transport, *, site_profile_confirmed=False):
        super().__init__(transport, model='CMW500', manufacturers=RS)
        if site_profile_confirmed is not True:
            raise InstrumentError('Confirm installed LTE signaling license, RF route/loss, test SIM/PLMN and channel allocation')
        self.plan = None
        self.configured = False
        self.active = False

    def configure(self, config):
        from dgm_rf.cmw_lte import lte_rmc_plan
        plan = lte_rmc_plan(config)
        self.ready()
        with self.io.transaction():
            if self.active:
                raise InstrumentError('Stop the current LTE instance before reconfiguration')
            self.configured = False
            # Retain the addressed instance for cleanup even when configuration fails.
            self.plan = plan
            self.apply(plan['configure'])
            self.configured = True

    def _wait(self, query, expected, *, timeout, cancelled=None):
        deadline = time.monotonic() + number(timeout, 'state timeout', 0.001, 3600)
        last = None
        while time.monotonic() < deadline:
            if cancelled is not None and cancelled.is_set():
                raise InterruptedError('LTE procedure cancelled')
            last = self.io.query(query).replace(' ', '')
            if last == expected:
                self.errors()
                return last
            time.sleep(min(0.1, max(0, deadline-time.monotonic())))
        raise TimeoutError(f'CMW state timeout; expected {expected!r}, last {last!r}')

    def start(self, *, timeout=60, cancelled=None):
        number(timeout, 'state timeout', 0.001, 3600)
        self.ready()
        if self.plan is None or not self.configured:
            raise InstrumentError('configure() must succeed first')
        with self.io.transaction():
            self.active = True  # includes a partially successful CELL ON
            self.io.write(self.plan['start'][0])
            for checkpoint in self.plan['checkpoints'][:2]:
                self._wait(checkpoint['query'], checkpoint['expect'], timeout=timeout, cancelled=cancelled)
            self.io.write(self.plan['start'][1])
            checkpoint = self.plan['checkpoints'][2]
            self._wait(checkpoint['query'], checkpoint['expect'], timeout=timeout, cancelled=cancelled)

    def stop(self):
        self.ready()
        if self.plan is None:
            raise InstrumentError('No configured LTE instance; stop cannot guess an instance')
        failures = []
        with self.io.transaction():
            # Always attempt CELL OFF even when disconnect fails.
            for command in self.plan['cleanup']:
                try:
                    self.io.write(command)
                except BaseException as exc:
                    failures.append(exc)
            try:
                self._wait(self.plan['off_query'], self.plan['off_expect'], timeout=10)
            except BaseException as exc:
                failures.append(exc)
        if failures:
            raise BaseExceptionGroup('CMW cleanup failed; DUT RF cessation is unconfirmed', failures)
        self.active = False

    def connected(self, *, timeout=60, cancelled=None):
        return managed_run(lambda: self.start(timeout=timeout, cancelled=cancelled), self.stop)
