import sqlite3
from contextlib import closing

import pytest

from pipeline.sqlite_read import ReadConnection, read_connection


def test_reader_retries_live_writer_lock_without_writes(tmp_path, monkeypatch):
    path = tmp_path/'live.sqlite3'
    writer = sqlite3.connect(path, check_same_thread=False)
    writer.execute('CREATE TABLE counters (n INTEGER)')
    writer.execute('INSERT INTO counters VALUES (7)')
    writer.commit()
    writer.execute('BEGIN EXCLUSIVE')
    sleeps = []

    def pause(delay):
        sleeps.append(delay)
        writer.commit()

    monkeypatch.setattr('pipeline.sqlite_read.time.sleep', pause)
    monkeypatch.setattr(ReadConnection, 'backoff', 0.05)
    try:
        with closing(read_connection(path, timeout=0.01)) as db:
            assert db.execute('SELECT n FROM counters').fetchone() == (7,)
            assert sleeps
            with pytest.raises(sqlite3.OperationalError, match='readonly'):
                db.execute('DELETE FROM counters')
    finally:
        writer.close()


def test_permanent_lock_is_bounded_and_other_errors_not_retried(tmp_path, monkeypatch):
    path = tmp_path/'locked.sqlite3'
    with closing(sqlite3.connect(path)) as writer:
        writer.execute('CREATE TABLE counters (n INTEGER)')
        writer.commit()
        with closing(read_connection(path, timeout=0.001)) as reader:
            pauses = []
            monkeypatch.setattr('pipeline.sqlite_read.time.sleep', pauses.append)
            with pytest.raises(sqlite3.OperationalError, match='no such table'):
                reader.execute('SELECT * FROM nonexistent')
            assert pauses == []
            writer.execute('BEGIN EXCLUSIVE')
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                reader.execute('SELECT * FROM counters')
            assert pauses == [0.25, 0.5, 1.0]
