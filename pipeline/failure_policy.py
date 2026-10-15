"""Continue terminal item failures; stop admission for systemic failure rates."""

from collections import deque
from threading import Lock


class SystemicFailure(RuntimeError):
    """Too many terminal failures among finalized items."""


class FailureWindow:
    def __init__(self, window=100, minimum=20, threshold=.05, label='Terminal failures'):
        if type(window) is not int or type(minimum) is not int or not 1 <= minimum <= window or not 0 < threshold < 1:
            raise ValueError('Invalid terminal failure window')
        self.window, self.minimum, self.threshold = window, minimum, threshold
        self.label = label
        self.outcomes = deque(maxlen=window)
        self.seen = set()
        self.lock = Lock()

    def record(self, key, failed):
        with self.lock:
            if key in self.seen:
                return
            self.seen.add(key)
            self.outcomes.append(bool(failed))
            count, failures = len(self.outcomes), sum(self.outcomes)
            if count >= self.minimum and failures / count > self.threshold:
                raise SystemicFailure(f'{self.label} {failures}/{count} exceed {self.threshold:.0%} rolling threshold')


def failure_window(config):
    controls=config['controls']
    return FailureWindow(controls.get('terminal_failure_window',100),
                         controls.get('terminal_failure_minimum',20),
                         controls.get('terminal_failure_threshold',.05))
