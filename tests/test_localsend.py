from __future__ import annotations

import hashlib
import http.client
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from pdf_to_epub import localsend
from pdf_to_epub.localsend import (
    DEFAULT_PORT,
    LocalSendBusy,
    LocalSendDevice,
    LocalSendError,
    LocalSendFingerprintMismatch,
    LocalSendPinRequired,
    LocalSendRejected,
    discover_devices,
    load_or_create_identity,
    parse_device_address,
    probe_device,
    send_file,
)


class _UploadServer(ThreadingHTTPServer):
    def __init__(self, status: int = 200) -> None:
        self.prepare_status = status
        self.prepare: dict[str, object] | None = None
        self.prepare_path = ""
        self.upload = b""
        super().__init__(("127.0.0.1", 0), _UploadHandler)


class _UploadHandler(BaseHTTPRequestHandler):
    server: _UploadServer

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path.startswith("/api/localsend/v2/prepare-upload"):
            self.server.prepare_path = self.path
            self.server.prepare = json.loads(body)
            if self.server.prepare_status != 200:
                self.send_response(self.server.prepare_status)
                self.end_headers()
                return
            file_id = next(iter(self.server.prepare["files"]))  # type: ignore[index]
            response = json.dumps(
                {"sessionId": "session-1", "files": {file_id: "token-1"}}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return
        if self.path.startswith("/api/localsend/v2/upload"):
            query = parse_qs(urlparse(self.path).query)
            assert query["sessionId"] == ["session-1"]
            assert query["token"] == ["token-1"]
            self.server.upload = body
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_error(404)

    def log_message(self, _format: str, *args: object) -> None:
        return


def _run_server(server: ThreadingHTTPServer):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("192.168.1.50", ("192.168.1.50", DEFAULT_PORT)),
        ("192.168.1.50:6000", ("192.168.1.50", 6000)),
        ("[::1]:53318", ("::1", 53318)),
        ("::1", ("::1", DEFAULT_PORT)),
    ],
)
def test_parse_device_address(raw: str, expected: tuple[str, int]) -> None:
    assert parse_device_address(raw) == expected


@pytest.mark.parametrize("raw", ["", "reader.local", "[::1", "1.2.3.4:99999"])
def test_parse_device_address_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_device_address(raw)


def test_identity_is_persistent_and_recovers_from_broken_files(tmp_path: Path) -> None:
    first = load_or_create_identity(tmp_path)
    second = load_or_create_identity(tmp_path)
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64

    first.certificate_path.write_text("broken", encoding="utf-8")
    repaired = load_or_create_identity(tmp_path)
    assert repaired.fingerprint != first.fingerprint


def test_discovery_callback_registers_device_and_returns_sender_identity(tmp_path: Path) -> None:
    identity = load_or_create_identity(tmp_path)
    server = localsend._DiscoveryServer(identity)
    thread = _run_server(server)
    payload = json.dumps(
        {
            "alias": "Kobo Libra",
            "version": "2.2",
            "deviceModel": "KOReader",
            "deviceType": "mobile",
            "fingerprint": "AB" * 32,
            "port": 53317,
            "protocol": "https",
        }
    ).encode()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
    try:
        connection.request(
            "POST",
            "/api/localsend/v2/register",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        response = connection.getresponse()
        returned = json.loads(response.read())
        assert response.status == 200
        assert returned["fingerprint"] == identity.fingerprint
        assert next(iter(server.devices.values())).alias == "Kobo Libra"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


@pytest.mark.parametrize(
    "payload",
    [
        {"alias": "Reader", "protocol": "ftp"},
        {"alias": "Reader", "port": "not-a-port"},
        {"alias": "Reader", "port": 70000},
    ],
)
def test_parse_device_rejects_invalid_advertisements(payload: dict[str, object]) -> None:
    with pytest.raises(LocalSendError):
        localsend._parse_device(payload, "192.168.1.2")


def test_send_file_uses_localsend_metadata_pin_checksum_and_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    server = _UploadServer()
    thread = _run_server(server)
    book = tmp_path / "book.epub"
    book.write_bytes(b"ebook-data" * 1000)
    progress: list[tuple[int, int]] = []
    device = LocalSendDevice("KOReader", "127.0.0.1", server.server_port, protocol="http")
    try:
        result = send_file(
            device,
            book,
            pin="1234",
            progress=lambda sent, total: progress.append((sent, total)),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert result.bytes_sent == book.stat().st_size
    assert server.upload == book.read_bytes()
    assert server.prepare_path.endswith("?pin=1234")
    assert server.prepare is not None
    file_meta = next(iter(server.prepare["files"].values()))  # type: ignore[index,union-attr]
    assert file_meta["fileName"] == "book.epub"
    assert file_meta["fileType"] == "application/epub+zip"
    assert file_meta["sha256"] == hashlib.sha256(book.read_bytes()).hexdigest()
    assert progress[0] == (0, book.stat().st_size)
    assert progress[-1] == (book.stat().st_size, book.stat().st_size)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, LocalSendPinRequired),
        (403, LocalSendRejected),
        (409, LocalSendBusy),
        (429, LocalSendError),
        (500, LocalSendError),
    ],
)
def test_send_file_maps_receiver_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_type: type[Exception],
) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    server = _UploadServer(status)
    thread = _run_server(server)
    book = tmp_path / "book.mobi"
    book.write_bytes(b"book")
    try:
        with pytest.raises(error_type):
            send_file(
                LocalSendDevice("KOReader", "127.0.0.1", server.server_port, "http"),
                book,
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_send_file_rejects_missing_files(tmp_path: Path) -> None:
    device = LocalSendDevice("KOReader", "127.0.0.1", protocol="http")
    with pytest.raises(LocalSendError, match="File not found"):
        send_file(device, tmp_path / "missing.epub")


def test_send_file_accepts_arbitrary_file_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    server = _UploadServer()
    thread = _run_server(server)
    notes = tmp_path / "notes.md"
    notes.write_text("# Notes", encoding="utf-8")
    try:
        result = send_file(
            LocalSendDevice("KOReader", "127.0.0.1", server.server_port, protocol="http"),
            notes,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert result.bytes_sent == notes.stat().st_size
    assert server.prepare is not None
    file_meta = next(iter(server.prepare["files"].values()))  # type: ignore[index,union-attr]
    assert file_meta["fileName"] == "notes.md"
    assert file_meta["fileType"] == "text/markdown"


def test_send_file_handles_already_received_and_invalid_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    book = tmp_path / "book.epub"
    book.write_bytes(b"book")
    device = LocalSendDevice("KOReader", "127.0.0.1", protocol="http")
    monkeypatch.setattr(localsend, "_request", lambda *_args, **_kwargs: (204, b"", ""))
    assert send_file(device, book).bytes_sent == 0

    monkeypatch.setattr(localsend, "_request", lambda *_args, **_kwargs: (200, b"{}", ""))
    with pytest.raises(LocalSendError, match="invalid upload session"):
        send_file(device, book)


def test_send_file_retries_checksum_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    book = tmp_path / "book.pdf"
    book.write_bytes(b"book")
    file_id: list[str] = []

    def prepared(*_args: object, **_kwargs: object) -> tuple[int, bytes, str]:
        request = json.loads(_kwargs["body"])
        file_id.append(next(iter(request["files"])))
        body = json.dumps({"sessionId": "session", "files": {file_id[-1]: "token"}}).encode()
        return 200, body, ""

    attempts = 0

    def upload(*_args: object, **_kwargs: object) -> int:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise LocalSendError("The received file checksum did not match.")
        return book.stat().st_size

    monkeypatch.setattr(localsend, "_request", prepared)
    monkeypatch.setattr(localsend, "_upload", upload)
    result = send_file(LocalSendDevice("KOReader", "127.0.0.1", protocol="http"), book)
    assert result.bytes_sent == book.stat().st_size
    assert attempts == 3


class _InfoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps(
            {
                "alias": "KOReader TLS",
                "version": "2.2",
                "deviceModel": "Kobo",
                "deviceType": "mobile",
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        return


def test_probe_https_device_captures_and_pins_certificate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client_identity = load_or_create_identity(tmp_path / "client")
    server_identity = load_or_create_identity(tmp_path / "server")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: client_identity)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _InfoHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(server_identity.certificate_path, server_identity.private_key_path)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=client_identity.certificate_path)
    if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
        context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = _run_server(server)
    try:
        device = probe_device("127.0.0.1", server.server_port)
        assert device.protocol == "https"
        assert device.fingerprint == server_identity.fingerprint
        assert device.alias == "KOReader TLS"

        impostor = LocalSendDevice(
            "KOReader TLS",
            "127.0.0.1",
            server.server_port,
            "https",
            fingerprint="00" * 32,
        )
        with pytest.raises(LocalSendFingerprintMismatch):
            localsend._request(
                impostor,
                client_identity,
                "GET",
                "/api/localsend/v2/info",
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def test_discovery_collects_udp_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = load_or_create_identity(tmp_path / "identity")
    monkeypatch.setattr(localsend, "load_or_create_identity", lambda: identity)
    payload = json.dumps(
        {
            "alias": "Kobo Clara",
            "version": "2.2",
            "deviceModel": "KOReader",
            "deviceType": "mobile",
            "fingerprint": "AA" * 32,
            "port": 53317,
            "protocol": "https",
            "announce": False,
        }
    ).encode()

    class FakeSocket:
        def __init__(self, *_args: object) -> None:
            self.returned = False
            self.sent: list[tuple[bytes, tuple[str, int]]] = []

        def setsockopt(self, *_args: object) -> None:
            return

        def bind(self, _address: tuple[str, int]) -> None:
            return

        def settimeout(self, _timeout: float) -> None:
            return

        def sendto(self, data: bytes, address: tuple[str, int]) -> None:
            self.sent.append((data, address))

        def recvfrom(self, _size: int) -> tuple[bytes, tuple[str, int]]:
            if not self.returned:
                self.returned = True
                return payload, ("192.168.1.80", 53317)
            raise TimeoutError

        def close(self) -> None:
            return

    class FakeDiscoveryServer:
        def __init__(self, selected_identity: object) -> None:
            self.identity = selected_identity
            self.server_address = ("0.0.0.0", 49152)
            self.devices: dict[str, LocalSendDevice] = {}
            self.devices_lock = threading.Lock()

        def record(self, data: dict[str, object], ip: str) -> None:
            device = localsend._parse_device(data, ip)
            self.devices[device.fingerprint or device.address] = device

        def serve_forever(self) -> None:
            return

        def shutdown(self) -> None:
            return

        def server_close(self) -> None:
            return

    fake = FakeSocket()
    monkeypatch.setattr(localsend, "_DiscoveryServer", FakeDiscoveryServer)
    monkeypatch.setattr(localsend.socket, "socket", lambda *_args: fake)
    devices = discover_devices(timeout=0.03)
    assert [(item.alias, item.ip) for item in devices] == [("Kobo Clara", "192.168.1.80")]
    assert fake.sent[0][1] == (localsend.MULTICAST_ADDRESS, DEFAULT_PORT)
