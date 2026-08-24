"""LocalSend v2.2 discovery and file transfer for KOReader devices."""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import mimetypes
import os
import platform
import socket
import ssl
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from platformdirs import user_config_path

MULTICAST_ADDRESS = "224.0.0.167"
DEFAULT_PORT = 53317
PROTOCOL_VERSION = "2.2"
MAX_DISCOVERY_BODY = 64 * 1024
MAX_CONTROL_BODY = 1024 * 1024


class LocalSendError(RuntimeError):
    """Base class for user-facing LocalSend failures."""


class LocalSendPinRequired(LocalSendError):
    """The receiver requires a PIN or rejected the supplied PIN."""


class LocalSendRejected(LocalSendError):
    """The receiver rejected the transfer."""


class LocalSendBusy(LocalSendError):
    """The receiver is already handling another transfer."""


class LocalSendFingerprintMismatch(LocalSendError):
    """The HTTPS certificate does not match the discovered device."""


@dataclass(frozen=True)
class LocalSendDevice:
    """A LocalSend receiver discovered on the local network."""

    alias: str
    ip: str
    port: int = DEFAULT_PORT
    protocol: str = "https"
    version: str = PROTOCOL_VERSION
    device_model: str = ""
    device_type: str = ""
    fingerprint: str = ""

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"


@dataclass(frozen=True)
class LocalSendIdentity:
    """Persistent sender identity used for LocalSend mutual TLS."""

    certificate_path: Path
    private_key_path: Path
    fingerprint: str


@dataclass(frozen=True)
class LocalSendResult:
    """Result of one completed transfer."""

    device: LocalSendDevice
    file_path: Path
    bytes_sent: int


ProgressCallback = Callable[[int, int], None]


def _certificate_fingerprint(certificate_der: bytes) -> str:
    return hashlib.sha256(certificate_der).hexdigest().upper()


def _normalize_fingerprint(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).upper()


def load_or_create_identity(config_dir: Path | None = None) -> LocalSendIdentity:
    """Load or create the persistent certificate used by the LocalSend sender."""

    root = config_dir or user_config_path("pdf-to-epub-ocr") / "localsend"
    root.mkdir(parents=True, exist_ok=True)
    certificate_path = root / "identity.pem"
    private_key_path = root / "identity-key.pem"

    if certificate_path.is_file() and private_key_path.is_file():
        try:
            certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
            serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
            return LocalSendIdentity(
                certificate_path,
                private_key_path,
                _certificate_fingerprint(certificate.public_bytes(serialization.Encoding.DER)),
            )
        except (OSError, ValueError, TypeError):
            pass

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "PDF to EPUB OCR")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.DNSName("pdf-to-epub-ocr")]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    private_key_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    with suppress(OSError):
        private_key_path.chmod(0o600)
    return LocalSendIdentity(
        certificate_path,
        private_key_path,
        _certificate_fingerprint(certificate.public_bytes(serialization.Encoding.DER)),
    )


def _sender_info(identity: LocalSendIdentity, *, port: int = DEFAULT_PORT) -> dict[str, Any]:
    return {
        "alias": "PDF to EPUB OCR",
        "version": PROTOCOL_VERSION,
        "deviceModel": platform.system() or ("Windows" if os.name == "nt" else "Desktop"),
        "deviceType": "desktop",
        "fingerprint": identity.fingerprint,
        "port": port,
        "protocol": "https",
        "download": False,
    }


def _parse_device(payload: dict[str, Any], ip: str) -> LocalSendDevice:
    alias = str(payload.get("alias") or "LocalSend device").strip()
    protocol = str(payload.get("protocol") or "https").casefold()
    if protocol not in {"http", "https"}:
        raise LocalSendError(f"Unsupported LocalSend protocol: {protocol}")
    try:
        port = int(payload.get("port") or DEFAULT_PORT)
    except (TypeError, ValueError) as error:
        raise LocalSendError("The LocalSend device advertised an invalid port.") from error
    if not 1 <= port <= 65535:
        raise LocalSendError("The LocalSend device advertised an invalid port.")
    return LocalSendDevice(
        alias=alias,
        ip=ip,
        port=port,
        protocol=protocol,
        version=str(payload.get("version") or PROTOCOL_VERSION),
        device_model=str(payload.get("deviceModel") or ""),
        device_type=str(payload.get("deviceType") or ""),
        fingerprint=_normalize_fingerprint(str(payload.get("fingerprint") or "")),
    )


class _DiscoveryServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, identity: LocalSendIdentity) -> None:
        self.identity = identity
        self.devices: dict[str, LocalSendDevice] = {}
        self.devices_lock = threading.Lock()
        super().__init__(("0.0.0.0", 0), _DiscoveryHandler)

    def record(self, payload: dict[str, Any], ip: str) -> None:
        device = _parse_device(payload, ip)
        key = device.fingerprint or device.address
        if device.fingerprint == self.identity.fingerprint:
            return
        with self.devices_lock:
            self.devices[key] = device


class _DiscoveryHandler(BaseHTTPRequestHandler):
    server: _DiscoveryServer

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.rstrip("/") != "/api/localsend/v2/register":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 < length <= MAX_DISCOVERY_BODY:
            self.send_error(400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError
            self.server.record(payload, self.client_address[0])
        except (json.JSONDecodeError, LocalSendError, ValueError):
            self.send_error(400)
            return
        response = json.dumps(_sender_info(self.server.identity)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format: str, *args: object) -> None:
        return


def discover_devices(timeout: float = 4.0) -> list[LocalSendDevice]:
    """Discover LocalSend receivers by multicast and HTTP registration callback."""

    if timeout <= 0:
        raise ValueError("Discovery timeout must be positive.")
    identity = load_or_create_identity()
    server = _DiscoveryServer(identity)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    callback_port = int(server.server_address[1])
    announcement = _sender_info(identity, port=callback_port)
    announcement["protocol"] = "http"
    announcement["announce"] = True
    encoded = json.dumps(announcement, separators=(",", ":")).encode()

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    udp.bind(("", 0))
    deadline = time.monotonic() + timeout
    next_announcement = 0.0
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_announcement:
                udp.sendto(encoded, (MULTICAST_ADDRESS, DEFAULT_PORT))
                next_announcement = now + 0.75
            udp.settimeout(min(0.2, max(0.01, deadline - now)))
            try:
                packet, remote = udp.recvfrom(MAX_DISCOVERY_BODY + 1)
            except TimeoutError:
                continue
            if len(packet) > MAX_DISCOVERY_BODY:
                continue
            try:
                payload = json.loads(packet)
                if isinstance(payload, dict) and not payload.get("announce", False):
                    server.record(payload, remote[0])
            except (json.JSONDecodeError, LocalSendError, UnicodeDecodeError):
                continue
    finally:
        udp.close()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)

    with server.devices_lock:
        return sorted(server.devices.values(), key=lambda item: (item.alias.casefold(), item.ip))


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        identity: LocalSendIdentity,
        expected_fingerprint: str = "",
        timeout: float,
    ) -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.load_cert_chain(identity.certificate_path, identity.private_key_path)
        super().__init__(host, port, context=context, timeout=timeout)
        self.expected_fingerprint = _normalize_fingerprint(expected_fingerprint)
        self.peer_fingerprint = ""

    def connect(self) -> None:
        super().connect()
        if self.sock is None:
            raise LocalSendError("The LocalSend TLS connection was not established.")
        certificate = self.sock.getpeercert(binary_form=True)
        if not certificate:
            self.close()
            raise LocalSendError("The LocalSend device did not present a certificate.")
        self.peer_fingerprint = _certificate_fingerprint(certificate)
        if self.expected_fingerprint and self.peer_fingerprint != self.expected_fingerprint:
            expected = self.expected_fingerprint
            actual = self.peer_fingerprint
            self.close()
            raise LocalSendFingerprintMismatch(
                f"LocalSend certificate fingerprint mismatch (expected {expected}, got {actual})."
            )


def _connection(
    device: LocalSendDevice,
    identity: LocalSendIdentity,
    *,
    timeout: float,
) -> http.client.HTTPConnection:
    if device.protocol == "https":
        return _PinnedHTTPSConnection(
            device.ip,
            device.port,
            identity=identity,
            expected_fingerprint=device.fingerprint,
            timeout=timeout,
        )
    return http.client.HTTPConnection(device.ip, device.port, timeout=timeout)


def _read_limited(response: http.client.HTTPResponse) -> bytes:
    body = response.read(MAX_CONTROL_BODY + 1)
    if len(body) > MAX_CONTROL_BODY:
        raise LocalSendError("The LocalSend device returned an oversized response.")
    return body


def _request(
    device: LocalSendDevice,
    identity: LocalSendIdentity,
    method: str,
    target: str,
    *,
    body: bytes | None = None,
    content_type: str = "application/json",
    timeout: float = 30.0,
) -> tuple[int, bytes, str]:
    connection = _connection(device, identity, timeout=timeout)
    try:
        headers = {"User-Agent": "pdf-to-epub-ocr", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(body))
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        response_body = _read_limited(response)
        fingerprint = getattr(connection, "peer_fingerprint", "")
        return response.status, response_body, fingerprint
    finally:
        connection.close()


def probe_device(ip: str, port: int = DEFAULT_PORT, timeout: float = 4.0) -> LocalSendDevice:
    """Resolve a manually entered LocalSend IP, preferring HTTPS."""

    clean_ip = str(ipaddress.ip_address(ip.strip().strip("[]")))
    identity = load_or_create_identity()
    failures: list[Exception] = []
    for protocol in ("https", "http"):
        candidate = LocalSendDevice("LocalSend device", clean_ip, port, protocol)
        try:
            status, body, peer_fingerprint = _request(
                candidate,
                identity,
                "GET",
                "/api/localsend/v2/info",
                timeout=timeout,
            )
            if status != 200:
                raise LocalSendError(f"LocalSend info request returned HTTP {status}.")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise LocalSendError("The LocalSend device returned invalid information.")
            payload["protocol"] = protocol
            payload["port"] = port
            if protocol == "https":
                payload["fingerprint"] = peer_fingerprint
            return _parse_device(payload, clean_ip)
        except (OSError, ssl.SSLError, json.JSONDecodeError, LocalSendError) as error:
            failures.append(error)
    detail = str(failures[-1]) if failures else "connection failed"
    raise LocalSendError(f"No LocalSend receiver was found at {clean_ip}:{port}: {detail}")


def parse_device_address(value: str) -> tuple[str, int]:
    """Parse an IPv4/IPv6 address with an optional port for the manual-send UI."""

    raw = value.strip()
    if not raw:
        raise ValueError("Enter the KOReader device IP address.")
    port = DEFAULT_PORT
    host = raw
    if raw.startswith("["):
        closing = raw.find("]")
        if closing < 0:
            raise ValueError("Invalid IPv6 address.")
        host = raw[1:closing]
        remainder = raw[closing + 1 :]
        if remainder:
            if not remainder.startswith(":"):
                raise ValueError("Invalid device address.")
            try:
                port = int(remainder[1:])
            except ValueError as error:
                raise ValueError("Invalid LocalSend port.") from error
    elif raw.count(":") == 1:
        possible_host, possible_port = raw.rsplit(":", 1)
        if possible_port.isdecimal():
            host = possible_host
            port = int(possible_port)
    try:
        normalized_host = str(ipaddress.ip_address(host))
    except ValueError as error:
        raise ValueError("Enter a valid IPv4 or IPv6 address.") from error
    if not 1 <= port <= 65535:
        raise ValueError("The LocalSend port must be between 1 and 65535.")
    return normalized_host, port


def _file_type(path: Path) -> str:
    known = {
        ".epub": "application/epub+zip",
        ".mobi": "application/x-mobipocket-ebook",
        ".pdf": "application/pdf",
    }
    detected = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return known.get(path.suffix.casefold(), detected)


def _raise_for_status(status: int, *, upload: bool = False) -> None:
    if 200 <= status < 300:
        return
    if status == 401:
        raise LocalSendPinRequired("A PIN is required, or the PIN is incorrect.")
    if status == 403:
        raise LocalSendRejected("The transfer was rejected on the KOReader device.")
    if status == 409:
        raise LocalSendBusy("The KOReader device is busy with another transfer.")
    if status == 422 and upload:
        raise LocalSendError("The received file checksum did not match.")
    if status == 429:
        raise LocalSendError("The KOReader device received too many requests. Try again shortly.")
    raise LocalSendError(f"The KOReader device returned HTTP {status}.")


def _upload(
    device: LocalSendDevice,
    identity: LocalSendIdentity,
    path: Path,
    target: str,
    progress: ProgressCallback | None,
) -> int:
    connection = _connection(device, identity, timeout=120.0)
    total = path.stat().st_size
    sent = 0
    try:
        connection.putrequest("POST", target)
        connection.putheader("User-Agent", "pdf-to-epub-ocr")
        connection.putheader("Content-Type", "application/octet-stream")
        connection.putheader("Content-Length", str(total))
        connection.endheaders()
        if progress is not None:
            progress(0, total)
        with path.open("rb") as source:
            while chunk := source.read(256 * 1024):
                connection.send(chunk)
                sent += len(chunk)
                if progress is not None:
                    progress(sent, total)
        response = connection.getresponse()
        _read_limited(response)
        _raise_for_status(response.status, upload=True)
        return sent
    finally:
        connection.close()


def send_file(
    device: LocalSendDevice,
    file_path: Path,
    *,
    pin: str = "",
    progress: ProgressCallback | None = None,
) -> LocalSendResult:
    """Prepare and upload one regular file using LocalSend protocol v2.2."""

    path = file_path.expanduser().resolve()
    if not path.is_file():
        raise LocalSendError(f"File not found: {path}")

    identity = load_or_create_identity()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)

    file_id = str(uuid.uuid4())
    metadata = {
        "id": file_id,
        "fileName": path.name,
        "size": path.stat().st_size,
        "fileType": _file_type(path),
        "sha256": digest.hexdigest(),
    }
    request_body = json.dumps(
        {"info": _sender_info(identity), "files": {file_id: metadata}},
        separators=(",", ":"),
    ).encode()
    prepare_target = "/api/localsend/v2/prepare-upload"
    if pin.strip():
        prepare_target += "?" + urlencode({"pin": pin.strip()})

    try:
        status, body, _ = _request(
            device,
            identity,
            "POST",
            prepare_target,
            body=request_body,
            timeout=180.0,
        )
        _raise_for_status(status)
        if status == 204:
            return LocalSendResult(device, path, 0)
        try:
            prepared = json.loads(body)
            session_id = str(prepared["sessionId"])
            token = str(prepared["files"][file_id])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise LocalSendError(
                "The KOReader device returned an invalid upload session."
            ) from error

        query = urlencode({"sessionId": session_id, "fileId": file_id, "token": token})
        upload_target = f"/api/localsend/v2/upload?{query}"
        last_error: LocalSendError | None = None
        for _attempt in range(3):
            try:
                sent = _upload(device, identity, path, upload_target, progress)
                return LocalSendResult(device, path, sent)
            except LocalSendError as error:
                last_error = error
                if "checksum" not in str(error).casefold():
                    raise
        raise last_error or LocalSendError("The file could not be transferred.")
    except TimeoutError as error:
        raise LocalSendError(
            "The KOReader device did not respond in time. Check the confirmation screen."
        ) from error
    except (ConnectionError, OSError, ssl.SSLError) as error:
        raise LocalSendError(f"Could not connect to the KOReader device: {error}") from error
