"""Worker temporário e recuperável do DragonBRX para a-Shell no iPhone.

O worker não aceita shell remoto. Cada capacidade é uma função explícita,
limitada e determinística. Resultados são persistidos antes do envio e só são
removidos após confirmação autenticada do núcleo, permitindo continuar depois
que o iOS suspender o a-Shell.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import threading
import time
from typing import Any, Callable, Dict, Mapping

from distributed_runtime import (
    MAX_MESSAGE_BYTES,
    ReplayGuard,
    envelope,
    read_secret,
    receive_message,
    send_message,
    system_info,
    text_statistics,
)


STATE_FORMAT = "dragonbrx-ios-worker-state"
STATE_VERSION = 1
MAX_CACHED_RESULTS = 128
MAX_SAMPLES = 512
MAX_FEATURES = 128
MAX_ABSOLUTE_NUMBER = 1_000_000.0
Handler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _finite_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} precisa ser numérico") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} precisa ser finito")
    if abs(number) > MAX_ABSOLUTE_NUMBER:
        raise ValueError(f"{label} excedeu o limite numérico")
    return number


def ios_system_info(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    result = dict(system_info(inputs))
    result.update(
        {
            "worker": "ios-a-shell",
            "temporary": True,
            "foreground_required": True,
        }
    )
    return result


def sha256_chunks(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    chunks = inputs.get("chunks", [])
    if not isinstance(chunks, list) or len(chunks) > 1_024:
        raise ValueError("chunks precisa ser uma lista com no máximo 1024 itens")
    encoded = [str(item).encode("utf-8") for item in chunks]
    total = sum(len(item) for item in encoded)
    if total > 512 * 1_024:
        raise ValueError("os chunks excederam 512 KiB")
    return {
        "algorithm": "sha256",
        "count": len(encoded),
        "bytes": total,
        "digests": [
            hashlib.sha256(item).hexdigest()
            for item in encoded
        ],
    }


def linear_gradient(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    """Calcula loss e gradiente MSE de um lote linear pequeno."""
    features = inputs.get("features")
    targets = inputs.get("targets")
    weights = inputs.get("weights")
    if not isinstance(features, list) or not features:
        raise ValueError("features precisa ser uma matriz não vazia")
    if len(features) > MAX_SAMPLES:
        raise ValueError(f"o lote excedeu {MAX_SAMPLES} amostras")
    if not isinstance(targets, list) or len(targets) != len(features):
        raise ValueError("targets precisa ter uma saída por amostra")
    if not isinstance(weights, list) or not weights:
        raise ValueError("weights precisa ser um vetor não vazio")
    if len(weights) > MAX_FEATURES:
        raise ValueError(f"o vetor excedeu {MAX_FEATURES} parâmetros")

    clean_weights = [
        _finite_number(value, f"weights[{index}]")
        for index, value in enumerate(weights)
    ]
    clean_targets = [
        _finite_number(value, f"targets[{index}]")
        for index, value in enumerate(targets)
    ]
    clean_features: list[list[float]] = []
    for row_index, row in enumerate(features):
        if not isinstance(row, list) or len(row) != len(clean_weights):
            raise ValueError(
                f"features[{row_index}] precisa ter "
                f"{len(clean_weights)} valores"
            )
        clean_features.append(
            [
                _finite_number(
                    value,
                    f"features[{row_index}][{column_index}]",
                )
                for column_index, value in enumerate(row)
            ]
        )

    bias = _finite_number(inputs.get("bias", 0.0), "bias")
    l2 = _finite_number(inputs.get("l2", 0.0), "l2")
    if l2 < 0.0 or l2 > 10_000.0:
        raise ValueError("l2 precisa estar entre 0 e 10000")

    gradient = [0.0] * len(clean_weights)
    bias_gradient = 0.0
    squared_error = 0.0
    predictions: list[float] = []
    for row, target in zip(clean_features, clean_targets):
        prediction = bias + sum(
            weight * value
            for weight, value in zip(clean_weights, row)
        )
        error = prediction - target
        predictions.append(prediction)
        squared_error += error * error
        bias_gradient += error
        for index, value in enumerate(row):
            gradient[index] += error * value

    count = float(len(clean_features))
    gradient = [
        (2.0 / count) * value + 2.0 * l2 * clean_weights[index]
        for index, value in enumerate(gradient)
    ]
    bias_gradient = (2.0 / count) * bias_gradient
    loss = squared_error / count + l2 * sum(
        value * value for value in clean_weights
    )
    return {
        "objective": "mean_squared_error",
        "samples": len(clean_features),
        "features": len(clean_weights),
        "loss": loss,
        "gradient": gradient,
        "bias_gradient": bias_gradient,
        "prediction_sha256": hashlib.sha256(
            json.dumps(
                predictions,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


IOS_HANDLERS: Dict[str, Handler] = {
    "system_info": ios_system_info,
    "text_statistics": text_statistics,
    "sha256_chunks": sha256_chunks,
    "linear_gradient": linear_gradient,
}


class IOSWorkerState:
    def __init__(self, path: str | Path, agent_id: str) -> None:
        self.path = Path(path).expanduser()
        self.agent_id = agent_id
        self._lock = threading.RLock()
        self.document = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "format": STATE_FORMAT,
            "version": STATE_VERSION,
            "agent_id": self.agent_id,
            "completed": {},
            "acknowledged": 0,
            "rejected": 0,
            "updated_at": time.time(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        document = json.loads(self.path.read_text(encoding="utf-8"))
        if (
            not isinstance(document, dict)
            or document.get("format") != STATE_FORMAT
            or int(document.get("version", 0)) != STATE_VERSION
            or document.get("agent_id") != self.agent_id
            or not isinstance(document.get("completed"), dict)
        ):
            raise ValueError("checkpoint do worker iOS é incompatível")
        return document

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.document["updated_at"] = time.time()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                self.document,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def get(self, reply_to: str) -> dict[str, Any] | None:
        with self._lock:
            item = self.document["completed"].get(reply_to)
            return dict(item) if isinstance(item, dict) else None

    def put(self, reply_to: str, result: Mapping[str, Any]) -> None:
        encoded = json.dumps(
            dict(result),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise ValueError("resultado excedeu o limite do protocolo")
        with self._lock:
            completed = self.document["completed"]
            completed[reply_to] = dict(result)
            while len(completed) > MAX_CACHED_RESULTS:
                completed.pop(next(iter(completed)))
            self._save()

    def acknowledge(self, reply_to: str, accepted: bool) -> bool:
        with self._lock:
            existed = self.document["completed"].pop(reply_to, None) is not None
            counter = "acknowledged" if accepted else "rejected"
            self.document[counter] = int(self.document.get(counter, 0)) + 1
            self._save()
            return existed

    def pending_ids(self) -> list[str]:
        with self._lock:
            return list(self.document["completed"])[-32:]


class IOSWorker:
    def __init__(
        self,
        agent_id: str,
        secret: bytes,
        handlers: Mapping[str, Handler],
        state: IOSWorkerState,
    ) -> None:
        if not handlers:
            raise ValueError("o worker precisa de ao menos uma capacidade")
        if state.agent_id != agent_id:
            raise ValueError("agent_id diverge do checkpoint")
        self.agent_id = agent_id
        self.secret = secret
        self.handlers = dict(handlers)
        self.state = state
        self._write_lock = threading.Lock()
        self._busy = threading.Event()

    def run(
        self,
        host: str,
        port: int,
        *,
        reconnect_min: float = 2.0,
        reconnect_max: float = 30.0,
    ) -> None:
        delay = max(1.0, reconnect_min)
        maximum = max(delay, reconnect_max)
        while True:
            try:
                self.connect_once(host, port)
                delay = max(1.0, reconnect_min)
            except (OSError, EOFError, RuntimeError, ValueError) as exc:
                print(
                    f"[ios-worker] desconectado: {exc}; "
                    f"reconexão em {delay:.1f}s"
                )
                time.sleep(delay)
                delay = min(maximum, delay * 1.7)

    def connect_once(self, host: str, port: int) -> None:
        replay_guard = ReplayGuard()
        with socket.create_connection((host, port), timeout=15) as sock:
            sock.settimeout(None)
            stream = sock.makefile("rwb")
            self._send(
                stream,
                "hello",
                {
                    "agent_id": self.agent_id,
                    "capabilities": sorted(self.handlers),
                    "platform": (
                        f"iOS-a-Shell/{platform.python_version()}/"
                        f"{platform.machine()}"
                    ),
                    "temporary": True,
                    "resume_pending": self.state.pending_ids(),
                },
            )
            accepted = receive_message(
                stream,
                self.secret,
                replay_guard,
            )
            if accepted.get("type") != "accepted":
                raise RuntimeError("registro do worker iOS recusado")

            heartbeat_stop = threading.Event()
            heartbeat = threading.Thread(
                target=self._heartbeat_loop,
                args=(stream, heartbeat_stop),
                daemon=True,
            )
            heartbeat.start()
            try:
                while True:
                    message = receive_message(
                        stream,
                        self.secret,
                        replay_guard,
                    )
                    self._handle(stream, message)
            finally:
                heartbeat_stop.set()
                heartbeat.join(timeout=1.0)

    def _send(
        self,
        stream: Any,
        kind: str,
        body: Mapping[str, Any],
    ) -> None:
        with self._write_lock:
            send_message(
                stream,
                envelope(kind, self.agent_id, body),
                self.secret,
            )

    def _heartbeat_loop(
        self,
        stream: Any,
        stop: threading.Event,
        interval: float = 20.0,
    ) -> None:
        while not stop.is_set():
            try:
                self._send(
                    stream,
                    "heartbeat",
                    {
                        "load": 1.0 if self._busy.is_set() else 0.0,
                        "pending_results": len(
                            self.state.pending_ids()
                        ),
                        "foreground": True,
                    },
                )
            except (OSError, ValueError):
                return
            if stop.wait(interval):
                return

    def _handle(
        self,
        stream: Any,
        message: Mapping[str, Any],
    ) -> None:
        kind = str(message.get("type", ""))
        body = dict(message.get("body") or {})
        if kind == "result_ack":
            reply_to = str(body.get("reply_to", ""))
            if reply_to:
                self.state.acknowledge(
                    reply_to,
                    bool(body.get("accepted")),
                )
            return
        if kind != "task":
            return

        reply_to = str(message.get("message_id", ""))
        cached = self.state.get(reply_to)
        if cached is not None:
            cached["resumed"] = True
            self._send(stream, "result", cached)
            return

        capability = str(body.get("capability", ""))
        handler = self.handlers.get(capability)
        self._busy.set()
        try:
            if handler is None:
                result: dict[str, Any] = {
                    "ok": False,
                    "error": "capacidade não instalada no worker iOS",
                }
            else:
                try:
                    output = dict(
                        handler(dict(body.get("inputs") or {}))
                    )
                    result = {"ok": True, "output": output}
                except Exception as exc:
                    result = {
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
            result.update(
                {
                    "reply_to": reply_to,
                    "action_id": body.get("action_id"),
                    "capability": capability,
                    "confidence": 0.9 if result["ok"] else 0.1,
                    "load": 0.0,
                    "worker": "ios-a-shell",
                }
            )
            self.state.put(reply_to, result)
            self._send(stream, "result", result)
        finally:
            self._busy.clear()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Worker recuperável DragonBRX para a-Shell no iPhone"
    )
    root.add_argument("--host", required=True)
    root.add_argument("--port", type=int, default=9999)
    root.add_argument("--agent-id", default="iphone-12-pro")
    root.add_argument("--secret-file", required=True)
    root.add_argument(
        "--state-file",
        default="~/Documents/.dragonbrx/ios-worker-state.json",
    )
    root.add_argument(
        "--capability",
        action="append",
        choices=sorted(IOS_HANDLERS),
        default=[],
    )
    root.add_argument("--reconnect-min", type=float, default=2.0)
    root.add_argument("--reconnect-max", type=float, default=30.0)
    return root


def main() -> None:
    args = parser().parse_args()
    selected_names = args.capability or [
        "system_info",
        "text_statistics",
        "sha256_chunks",
        "linear_gradient",
    ]
    selected = {
        name: IOS_HANDLERS[name]
        for name in selected_names
    }
    state = IOSWorkerState(args.state_file, args.agent_id)
    worker = IOSWorker(
        args.agent_id,
        read_secret(args.secret_file),
        selected,
        state,
    )
    print(
        "DragonBRX iOS worker iniciado. Mantenha o a-Shell em primeiro "
        "plano; após suspensão, execute o mesmo comando para retomar."
    )
    try:
        worker.run(
            args.host,
            args.port,
            reconnect_min=args.reconnect_min,
            reconnect_max=args.reconnect_max,
        )
    except KeyboardInterrupt:
        print("\nWorker interrompido; resultados pendentes ficaram salvos.")


if __name__ == "__main__":
    main()
