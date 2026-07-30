"""Bootstrap sem dependências para descobrir e iniciar o worker no a-Shell."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import platform
import socket
import time
from typing import Any, Mapping
from uuid import uuid4

from distributed_runtime import (
    DEFAULT_DISCOVERY_PORT,
    PROTOCOL,
    VERSION,
    read_secret,
    verify,
)
from ios_worker import IOSWorker, IOSWorkerState, IOS_HANDLERS
from pairing import KDF_NAME, derive_network_key


BOOTSTRAP_FORMAT = "dragonbrx-ios-bootstrap"
BOOTSTRAP_VERSION = 1


def _decode_discovery(
    payload: bytes,
    address: tuple[str, int],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    try:
        message = json.loads(payload.decode("utf-8"))
        body = dict(message.get("body") or {})
        port = int(body.get("tcp_port", 0))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if (
        message.get("protocol") != PROTOCOL
        or message.get("version") != VERSION
        or message.get("type") != "discovery"
        or message.get("sender") != "core"
        or body.get("service") != "DragonBRX"
        or body.get("local_only") is not True
        or not 1 <= port <= 65_535
    ):
        return None
    try:
        timestamp = float(message.get("timestamp", 0.0))
    except (TypeError, ValueError):
        return None
    if abs(time.time() - timestamp) > 30.0:
        return None
    connection = {
        "host": address[0],
        "port": port,
        "service_id": str(body.get("service_id", "")),
    }
    return message, body, connection


def parse_discovery(
    payload: bytes,
    address: tuple[str, int],
    secret: bytes,
) -> dict[str, Any] | None:
    decoded = _decode_discovery(payload, address)
    if decoded is None:
        return None
    message, _, connection = decoded
    return connection if verify(message, secret) else None


def pair_discovery(
    payload: bytes,
    address: tuple[str, int],
    password: str,
) -> tuple[dict[str, Any], bytes] | None:
    decoded = _decode_discovery(payload, address)
    if decoded is None:
        return None
    message, body, connection = decoded
    pairing = body.get("pairing")
    if not isinstance(pairing, Mapping):
        return None
    if str(pairing.get("kdf", "")) != KDF_NAME:
        return None
    try:
        secret = derive_network_key(
            password,
            salt_b64=str(pairing.get("salt_b64", "")),
            iterations=int(pairing.get("iterations", 0)),
        )
    except (TypeError, ValueError):
        return None
    if not verify(message, secret):
        return None
    return connection, secret


def discover_core(
    secret: bytes,
    *,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("", int(discovery_port)))
        listener.settimeout(1.0)
        while time.monotonic() < deadline:
            try:
                payload, address = listener.recvfrom(65_535)
            except socket.timeout:
                continue
            discovered = parse_discovery(payload, address, secret)
            if discovered is not None:
                return discovered
    raise TimeoutError(
        "nenhum coordenador DragonBRX autenticado foi encontrado na LAN"
    )


def _save_secret(path: Path, secret: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(secret)
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def discover_and_pair(
    secret_path: Path,
    *,
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
    timeout_seconds: float = 60.0,
) -> tuple[dict[str, Any], bytes]:
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    prompted_password: str | None = None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("", int(discovery_port)))
        listener.settimeout(1.0)
        while time.monotonic() < deadline:
            try:
                payload, address = listener.recvfrom(65_535)
            except socket.timeout:
                continue
            decoded = _decode_discovery(payload, address)
            if decoded is None:
                continue
            _, body, _ = decoded
            pairing = body.get("pairing")
            if (
                not isinstance(pairing, Mapping)
                or pairing.get("kdf") != KDF_NAME
            ):
                continue
            if prompted_password is None:
                prompted_password = getpass.getpass(
                    "Digite a senha de pareamento definida no PC: "
                )
            paired = pair_discovery(
                payload,
                address,
                prompted_password,
            )
            if paired is None:
                raise ValueError("senha de pareamento incorreta")
            connection, secret = paired
            _save_secret(secret_path, secret)
            return connection, secret
    raise TimeoutError(
        "nenhum coordenador com pareamento por senha foi encontrado"
    )


def load_identity(path: Path) -> dict[str, Any]:
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
        if (
            document.get("format") != BOOTSTRAP_FORMAT
            or int(document.get("version", 0)) != BOOTSTRAP_VERSION
            or not str(document.get("agent_id", "")).strip()
        ):
            raise ValueError("identidade do bootstrap é incompatível")
        return document
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "format": BOOTSTRAP_FORMAT,
        "version": BOOTSTRAP_VERSION,
        "agent_id": "iphone-" + uuid4().hex[:10],
        "platform": (
            f"a-Shell/{platform.python_version()}/{platform.machine()}"
        ),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
    return document


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Instalação lógica, descoberta e conexão do worker iOS"
    )
    root.add_argument(
        "--config-dir",
        default="~/Documents/.dragonbrx",
    )
    root.add_argument(
        "--discovery-port",
        type=int,
        default=DEFAULT_DISCOVERY_PORT,
    )
    root.add_argument(
        "--discovery-timeout",
        type=float,
        default=60.0,
    )
    root.add_argument("--host")
    root.add_argument("--port", type=int, default=9999)
    return root


def main() -> None:
    args = parser().parse_args()
    config_dir = Path(args.config_dir).expanduser()
    secret_path = config_dir / "network.key"
    identity_path = config_dir / "ios-bootstrap.json"
    state_path = config_dir / "ios-worker-state.json"
    identity = load_identity(identity_path)

    if secret_path.exists():
        secret = read_secret(str(secret_path))
    else:
        secret = b""
    if args.host and not secret:
        raise ValueError(
            "o primeiro pareamento exige descoberta LAN para receber "
            "os parâmetros seguros do KDF"
        )
    if args.host:
        connection = {
            "host": args.host,
            "port": args.port,
            "service_id": "manual",
        }
    elif secret:
        print(
            "Procurando o coordenador DragonBRX autenticado no Wi-Fi local..."
        )
        connection = discover_core(
            secret,
            discovery_port=args.discovery_port,
            timeout_seconds=args.discovery_timeout,
        )
    else:
        print(
            "Primeiro pareamento: procurando o PC na rede local..."
        )
        connection, secret = discover_and_pair(
            secret_path,
            discovery_port=args.discovery_port,
            timeout_seconds=args.discovery_timeout,
        )
    print(
        "Coordenador autenticado encontrado em "
        f"{connection['host']}:{connection['port']}."
    )
    worker = IOSWorker(
        str(identity["agent_id"]),
        secret,
        IOS_HANDLERS,
        IOSWorkerState(state_path, str(identity["agent_id"])),
    )
    print(
        "Worker ativo. Mantenha o a-Shell em primeiro plano; reexecute "
        "o bootstrap depois de uma suspensão."
    )
    worker.run(
        str(connection["host"]),
        int(connection["port"]),
    )


if __name__ == "__main__":
    main()
