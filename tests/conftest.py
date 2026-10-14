"""All tests must remain offline, even when provider adapters are added."""

import socket
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Use workspace-local temporary files and remove them after every test."""
    root = Path(__file__).resolve().parents[1] / "artifacts"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="test-temp-", dir=root) as directory:
        yield Path(directory)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network access is forbidden in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
