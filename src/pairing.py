"""Pareamento local por senha sem armazenar a senha do operador."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Any, Mapping


PAIRING_FORMAT = "dragonbrx-lan-pairing"
PAIRING_VERSION = 1
KDF_NAME = "pbkdf2-hmac-sha256"
DEFAULT_ITERATIONS = 300_000
MINIMUM_PASSWORD_CHARACTERS = 12


def validate_password(password: str) -> str:
    clean = password.strip()
    if len(clean) < MINIMUM_PASSWORD_CHARACTERS:
        raise ValueError(
            "a senha de pareamento precisa ter ao menos "
            f"{MINIMUM_PASSWORD_CHARACTERS} caracteres"
        )
    if len(clean.encode("utf-8")) > 1_024:
        raise ValueError("a senha de pareamento excedeu 1024 bytes")
    return clean


def derive_network_key(
    password: str,
    *,
    salt_b64: str,
    iterations: int,
) -> bytes:
    clean = validate_password(password)
    count = int(iterations)
    if not 100_000 <= count <= 2_000_000:
        raise ValueError("iterações PBKDF2 fora do limite")
    try:
        salt = base64.b64decode(salt_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("salt de pareamento inválido") from exc
    if not 16 <= len(salt) <= 64:
        raise ValueError("salt de pareamento precisa ter entre 16 e 64 bytes")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        clean.encode("utf-8"),
        salt,
        count,
        dklen=32,
    )
    # O protocolo existente lê uma chave textual de 64 bytes.
    return derived.hex().encode("ascii")


def load_pairing(path: str | Path) -> dict[str, Any]:
    document = json.loads(
        Path(path).expanduser().read_text(encoding="utf-8")
    )
    if (
        not isinstance(document, dict)
        or document.get("format") != PAIRING_FORMAT
        or int(document.get("version", 0)) != PAIRING_VERSION
        or document.get("kdf") != KDF_NAME
    ):
        raise ValueError("configuração de pareamento incompatível")
    # Valida limites sem precisar conhecer a senha.
    salt_b64 = str(document.get("salt_b64", ""))
    iterations = int(document.get("iterations", 0))
    try:
        salt = base64.b64decode(salt_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("salt de pareamento inválido") from exc
    if not 16 <= len(salt) <= 64:
        raise ValueError("salt de pareamento inválido")
    if not 100_000 <= iterations <= 2_000_000:
        raise ValueError("iterações de pareamento inválidas")
    return {
        "format": PAIRING_FORMAT,
        "version": PAIRING_VERSION,
        "kdf": KDF_NAME,
        "salt_b64": salt_b64,
        "iterations": iterations,
    }


def initialize_pairing(
    password: str,
    *,
    pairing_file: str | Path,
    secret_file: str | Path,
) -> dict[str, Any]:
    pairing_path = Path(pairing_file).expanduser()
    secret_path = Path(secret_file).expanduser()
    if pairing_path.exists():
        document = load_pairing(pairing_path)
    else:
        document = {
            "format": PAIRING_FORMAT,
            "version": PAIRING_VERSION,
            "kdf": KDF_NAME,
            "salt_b64": base64.b64encode(
                secrets.token_bytes(24)
            ).decode("ascii"),
            "iterations": DEFAULT_ITERATIONS,
        }
    derived = derive_network_key(
        password,
        salt_b64=str(document["salt_b64"]),
        iterations=int(document["iterations"]),
    )
    if secret_path.exists():
        current = secret_path.read_bytes().strip()
        if not hmac.compare_digest(current, derived):
            raise ValueError("a senha não corresponde ao pareamento existente")
    else:
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_secret = secret_path.with_suffix(
            secret_path.suffix + ".tmp"
        )
        temporary_secret.write_bytes(derived)
        temporary_secret.replace(secret_path)
        try:
            os.chmod(secret_path, 0o600)
        except OSError:
            pass
    if not pairing_path.exists():
        pairing_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_pairing = pairing_path.with_suffix(
            pairing_path.suffix + ".tmp"
        )
        temporary_pairing.write_text(
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary_pairing.replace(pairing_path)
    return dict(document)


def public_pairing(document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kdf": str(document["kdf"]),
        "salt_b64": str(document["salt_b64"]),
        "iterations": int(document["iterations"]),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Configurar senha local de pareamento DragonBRX"
    )
    root.add_argument("command", choices=["initialize", "show-public"])
    root.add_argument("--pairing-file", required=True)
    root.add_argument("--secret-file")
    root.add_argument("--password-stdin", action="store_true")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "show-public":
        print(
            json.dumps(
                public_pairing(load_pairing(args.pairing_file)),
                ensure_ascii=False,
            )
        )
        return
    if not args.secret_file or not args.password_stdin:
        raise SystemExit(
            "initialize exige --secret-file e --password-stdin"
        )
    password = sys.stdin.readline().rstrip("\r\n")
    document = initialize_pairing(
        password,
        pairing_file=args.pairing_file,
        secret_file=args.secret_file,
    )
    print(
        json.dumps(
            {
                "configured": True,
                "password_stored": False,
                "kdf": document["kdf"],
                "iterations": document["iterations"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

