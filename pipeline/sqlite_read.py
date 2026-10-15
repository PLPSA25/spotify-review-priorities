"""Bounded retries for read-only monitoring during SQLite writer contention."""
import sqlite3
import time
from pathlib import Path


class ReadConnection(sqlite3.Connection):
    attempts = 4
    backoff = 0.25

    def execute(self, sql, parameters=()):
        for attempt in range(self.attempts):
            try:
                return super().execute(sql, parameters)
            except sqlite3.OperationalError as error:
                code = getattr(error, 'sqlite_errorcode', 0) & 255
                if code not in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} or attempt == self.attempts - 1:
                    raise
                time.sleep(self.backoff * 2 ** attempt)


def read_connection(path: Path, timeout: float = 5.0):
    # sqlite3's timeout installs busy_timeout (5000 ms by default). Each execute
    # retries only BUSY/LOCKED, at most four attempts (~21.75 s default bound).
    # Retrying reads never repeats snapshot writes or changes any failure window.
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True,
                           timeout=timeout, factory=ReadConnection)
