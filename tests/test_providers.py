"""HTTP request shape and secret handling using a mocked urlopen boundary."""

import json
from pathlib import Path
from typing import ClassVar

import pytest

from pipeline.providers import HTTPTransport, ProviderError, keys_from_env


def test_keys_checked_without_echo(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    missing = tmp_path / ".env"
    with pytest.raises(ValueError):
        keys_from_env(missing)
    missing.write_text("OPENAI_API_KEY=synthetic-only\nTYPESAFE_API_KEY=also-synthetic\n")
    assert keys_from_env(missing)["OPENAI_API_KEY"] == "synthetic-only"
    assert capsys.readouterr().out == ""


class Socket:
    def settimeout(self, value):
        self.timeout = value


class Reply:
    status = 200
    will_close = False
    body = b'{"model":"test"}'
    def getheaders(self):
        return [('x-request-id', 'test-id'), ('secret-other-header', 'do-not-save')]
    def read(self):
        return self.body


class Connection:
    instances: ClassVar[list] = []
    failure = None
    def __init__(self, host, timeout):
        self.host, self.timeout, self.sock = host, timeout, None
        self.requests = []
        self.instances.append(self)
    def connect(self):
        if self.failure == 'connect':
            raise TimeoutError('synthetic-key connect timeout')
        self.sock = Socket()
    def request(self, method, path, body, headers):
        self.requests.append((method, path, body, headers))
        if self.failure == 'send':
            raise ConnectionResetError('send reset')
    def getresponse(self):
        if self.failure == 'post_send':
            raise TimeoutError('read timeout')
        return Reply()
    def close(self):
        self.sock = None


@pytest.fixture
def fake_connection(monkeypatch):
    Connection.instances = []
    Connection.failure = None
    Reply.body = b'{"model":"test"}'
    monkeypatch.setattr('http.client.HTTPSConnection', Connection)
    return Connection


def test_keepalive_both_providers_and_explicit_timeouts(fake_connection):
    transport = HTTPTransport({'TYPESAFE_API_KEY':'synthetic-key','OPENAI_API_KEY':'synthetic-key'}, 60, connect_timeout=15)
    for provider in ('typesafe','openai'):
        first = transport.request(provider, {})
        second = transport.request(provider, {})
        assert not first['_transport']['connection_reused']
        assert second['_transport']['connection_reused']
        assert second['_headers'] == {'x-request-id':'test-id'}
        assert 'synthetic-key' not in json.dumps(second)
    assert len(fake_connection.instances) == 2
    for connection in fake_connection.instances:
        assert connection.timeout == 15
        assert connection.sock.timeout == 60
        assert len(connection.requests) == 2
        assert connection.requests[0][3]['Connection'] == 'keep-alive'
    transport.close()
    assert all(c.sock is None for c in fake_connection.instances)


@pytest.mark.parametrize('phase', ['connect','send','post_send'])
def test_failure_phase_and_no_hidden_retry(fake_connection, phase):
    transport = HTTPTransport({'TYPESAFE_API_KEY':'synthetic-key'}, 60)
    fake_connection.failure = phase
    with pytest.raises(ProviderError) as caught:
        transport.request('typesafe', {})
    diagnostic = caught.value.diagnostic
    assert diagnostic['failure_phase'] == phase
    assert diagnostic['request_sent'] == (phase == 'post_send')
    assert 'synthetic-key' not in json.dumps(diagnostic)
    assert len(fake_connection.instances) == 1
    assert fake_connection.instances[0].sock is None
    fake_connection.failure = None
    assert not transport.request('typesafe', {})['_transport']['connection_reused']


def test_unreadable_reply_has_unknown_charge(fake_connection):
    Reply.body = b'not-json'
    with pytest.raises(ProviderError) as caught:
        HTTPTransport({'TYPESAFE_API_KEY':'synthetic-key'},60).request('typesafe',{})
    assert caught.value.unknown_charge
    assert caught.value.diagnostic['failure_phase'] == 'post_send'


def test_connections_are_worker_local(fake_connection):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier = Barrier(8)
    transport = HTTPTransport({'TYPESAFE_API_KEY':'synthetic-key'},60)
    def worker(_):
        barrier.wait()
        transport.request('typesafe',{})
        return transport.request('typesafe',{})['_transport']['connection_reused']
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(worker,range(8)))
    assert len(fake_connection.instances) == 8
    transport.close()
