"""Rede de trabalho distribuída do DragonBRX para notebook e Termux.

Não usa modelo, API externa nem execução remota de shell. O núcleo central envia
tarefas declarativas e cada celular executa somente capacidades registradas em
uma lista local. As mensagens são JSON por TCP e autenticadas com HMAC-SHA256.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import socket
import socketserver
import threading
import time
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
from uuid import uuid4

from cognitive_fabric import Action, CognitiveFabric


PROTOCOL = "dragonbrx-node"
VERSION = 1
MAX_MESSAGE_BYTES = 1_048_576
Handler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _canonical(message: Mapping[str, Any]) -> bytes:
    clean = dict(message)
    clean.pop("signature", None)
    return json.dumps(
        clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sign(message: Mapping[str, Any], secret: bytes) -> Dict[str, Any]:
    signed = dict(message)
    signed["signature"] = hmac.new(secret, _canonical(signed), hashlib.sha256).hexdigest()
    return signed


def verify(message: Mapping[str, Any], secret: bytes) -> bool:
    supplied = str(message.get("signature", ""))
    expected = hmac.new(secret, _canonical(message), hashlib.sha256).hexdigest()
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def envelope(kind: str, sender: str, body: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "version": VERSION,
        "message_id": uuid4().hex,
        "type": kind,
        "sender": sender,
        "timestamp": time.time(),
        "body": dict(body),
    }


def read_secret(path: str) -> bytes:
    secret = Path(path).expanduser().read_bytes().strip()
    if len(secret) < 32:
        raise ValueError("o segredo compartilhado precisa ter pelo menos 32 bytes")
    return secret


def send_message(stream: Any, message: Mapping[str, Any], secret: bytes) -> None:
    raw = json.dumps(sign(message, secret), ensure_ascii=False, separators=(",", ":"))
    encoded = raw.encode("utf-8")
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise ValueError("mensagem excede o limite")
    stream.write(encoded + b"\n")
    stream.flush()


def receive_message(stream: Any, secret: bytes) -> Dict[str, Any]:
    raw = stream.readline(MAX_MESSAGE_BYTES + 2)
    if not raw:
        raise EOFError("conexão encerrada")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("mensagem excede o limite")
    data = json.loads(raw.decode("utf-8"))
    if data.get("protocol") != PROTOCOL or data.get("version") != VERSION:
        raise ValueError("protocolo incompatível")
    if not verify(data, secret):
        raise ValueError("assinatura inválida")
    return data


class AgentRegistry:
    def __init__(self, core: CognitiveFabric) -> None:
        self.core = core
        self.connections: Dict[str, Any] = {}
        self.inflight: Dict[str, Action] = {}
        self._lock = threading.RLock()

    def attach(
        self,
        agent_id: str,
        stream: Any,
        capabilities: Iterable[str],
        platform_name: str,
    ) -> None:
        with self._lock:
            self.connections[agent_id] = stream
            self.core.register_agent(
                agent_id,
                capabilities,
                platform=platform_name,
                reliability=0.5,
            )

    def detach(self, agent_id: str) -> None:
        with self._lock:
            self.connections.pop(agent_id, None)
            agent = self.core.agents.get(agent_id)
            if agent:
                agent.last_seen = 0.0

    def dispatch(self, action: Action) -> str:
        decision = self.core.choose([action])
        if not decision.delegated_to:
            raise RuntimeError(f"nenhum agente disponível para {action.capability}")
        with self._lock:
            stream = self.connections.get(decision.delegated_to)
            if stream is None:
                raise RuntimeError("agente selecionado perdeu a conexão")
            message = envelope(
                "task",
                "core",
                {
                    "action_id": action.action_id,
                    "name": action.name,
                    "capability": action.capability,
                    "inputs": action.inputs,
                    "expected": action.expected,
                },
            )
            send_message(stream, message, self.server_secret)
            self.inflight[message["message_id"]] = action
            return message["message_id"]

    def complete(self, agent_id: str, body: Mapping[str, Any]) -> bool:
        """Fecha uma tarefa e transforma o resultado em aprendizagem."""
        reply_to = str(body.get("reply_to", ""))
        with self._lock:
            action = self.inflight.pop(reply_to, None)
        if action is None:
            return False
        success = 1.0 if body.get("ok") is True else 0.0
        self.core.learn_outcome(
            action,
            success,
            evidence=dict(body),
            agent_id=agent_id,
        )
        return True


class CognitiveTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        core: CognitiveFabric,
        secret: bytes,
    ) -> None:
        self.core = core
        self.secret = secret
        self.registry = AgentRegistry(core)
        self.registry.server_secret = secret
        super().__init__(address, CognitiveRequestHandler)


class CognitiveRequestHandler(socketserver.StreamRequestHandler):
    server: CognitiveTCPServer

    def handle(self) -> None:
        agent_id: Optional[str] = None
        try:
            hello = receive_message(self.rfile, self.server.secret)
            if hello.get("type") != "hello":
                raise ValueError("a primeira mensagem precisa ser hello")
            body = dict(hello.get("body") or {})
            agent_id = str(body.get("agent_id", "")).strip()
            capabilities = body.get("capabilities", [])
            if not agent_id or not isinstance(capabilities, list) or not capabilities:
                raise ValueError("identidade ou capacidades inválidas")
            self.server.registry.attach(
                agent_id,
                self.wfile,
                capabilities,
                str(body.get("platform", "unknown")),
            )
            send_message(
                self.wfile,
                envelope("accepted", "core", {"agent_id": agent_id}),
                self.server.secret,
            )

            while True:
                message = receive_message(self.rfile, self.server.secret)
                self._integrate(agent_id, message)
        except EOFError:
            pass
        except (ValueError, json.JSONDecodeError) as exc:
            try:
                send_message(
                    self.wfile,
                    envelope("error", "core", {"message": str(exc)}),
                    self.server.secret,
                )
            except OSError:
                pass
        finally:
            if agent_id:
                self.server.registry.detach(agent_id)

    def _integrate(self, agent_id: str, message: Mapping[str, Any]) -> None:
        kind = str(message.get("type"))
        body = dict(message.get("body") or {})
        agent = self.server.core.agents.get(agent_id)
        if agent:
            agent.last_seen = time.time()
            agent.load = max(0.0, min(1.0, float(body.get("load", agent.load))))

        if kind == "heartbeat":
            return
        if kind not in {"result", "observation"}:
            raise ValueError(f"mensagem {kind!r} não aceita")
        if kind == "result" and self.server.registry.complete(agent_id, body):
            return
        self.server.core.perceive(
            kind,
            body,
            source=agent_id,
            salience=float(body.get("salience", 0.6)),
            confidence=float(body.get("confidence", 0.7)),
        )


class TermuxAgent:
    def __init__(
        self,
        agent_id: str,
        secret: bytes,
        handlers: Mapping[str, Handler],
    ) -> None:
        if not handlers:
            raise ValueError("o agente precisa de pelo menos uma capacidade")
        self.agent_id = agent_id
        self.secret = secret
        self.handlers = dict(handlers)
        self._write_lock = threading.Lock()

    def run(self, host: str, port: int, reconnect_delay: float = 5.0) -> None:
        while True:
            try:
                with socket.create_connection((host, port), timeout=15) as sock:
                    sock.settimeout(None)
                    stream = sock.makefile("rwb")
                    self._send(
                        stream,
                        "hello",
                        {
                            "agent_id": self.agent_id,
                            "capabilities": sorted(self.handlers),
                            "platform": f"{platform.system()}-{platform.machine()}",
                        },
                    )
                    accepted = receive_message(stream, self.secret)
                    if accepted.get("type") != "accepted":
                        raise RuntimeError("registro recusado")
                    for message in self._messages(stream):
                        self._handle(stream, message)
            except (OSError, EOFError, RuntimeError, ValueError) as exc:
                print(f"[agent] conexão indisponível: {exc}; nova tentativa em {reconnect_delay}s")
                time.sleep(reconnect_delay)

    def _messages(self, stream: Any):
        while True:
            yield receive_message(stream, self.secret)

    def _send(
        self,
        stream: Any,
        kind: str,
        body: Mapping[str, Any],
    ) -> None:
        with self._write_lock:
            send_message(stream, envelope(kind, self.agent_id, body), self.secret)

    def _handle(self, stream: Any, message: Mapping[str, Any]) -> None:
        if message.get("type") != "task":
            return
        body = dict(message.get("body") or {})
        capability = str(body.get("capability", ""))
        handler = self.handlers.get(capability)
        if handler is None:
            result: Dict[str, Any] = {
                "ok": False,
                "error": "capacidade não instalada",
            }
        else:
            try:
                output = dict(handler(dict(body.get("inputs") or {})))
                result = {"ok": True, "output": output}
            except Exception as exc:
                result = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        result.update(
            {
                "reply_to": message.get("message_id"),
                "action_id": body.get("action_id"),
                "capability": capability,
                "confidence": 0.8 if result["ok"] else 0.2,
                "load": 0.0,
            }
        )
        self._send(stream, "result", result)


def system_info(_: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }


def text_statistics(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
    text = str(inputs.get("text", ""))
    words = text.split()
    return {
        "characters": len(text),
        "words": len(words),
        "lines": len(text.splitlines()) or 1,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


BUILTIN_HANDLERS: Dict[str, Handler] = {
    "system_info": system_info,
    "text_statistics": text_statistics,
}


def _central_command(
    server: CognitiveTCPServer,
    core: CognitiveFabric,
    raw: str,
    state_file: str,
) -> bool:
    """Executa um comando JSON local; retorna False quando deve encerrar."""
    command = json.loads(raw)
    kind = command.get("type")
    if kind == "status":
        print(json.dumps(core.status(), ensure_ascii=False, indent=2))
    elif kind == "introspect":
        print(json.dumps(core.introspect(), ensure_ascii=False, indent=2))
    elif kind == "recall":
        print(
            json.dumps(
                core.recall(command.get("query", {}), int(command.get("limit", 5))),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif kind == "goal":
        goal = core.add_goal(
            str(command["description"]),
            desired=command["desired"],
            avoid=command.get("avoid", []),
            priority=float(command.get("priority", 0.5)),
        )
        print(json.dumps(asdict(goal), ensure_ascii=False, indent=2))
    elif kind == "perceive":
        event = core.perceive(
            str(command.get("kind", "observation")),
            dict(command.get("payload") or {}),
            source=str(command.get("source", "operator")),
            salience=float(command.get("salience", 0.5)),
            confidence=float(command.get("confidence", 0.8)),
        )
        print(json.dumps(asdict(event), ensure_ascii=False, indent=2))
    elif kind == "task":
        action = Action(
            action_id=str(command.get("action_id") or uuid4().hex),
            name=str(command["name"]),
            capability=str(command["capability"]),
            inputs=dict(command.get("inputs") or {}),
            expected=list(command.get("expected") or []),
            cost=float(command.get("cost", 0.0)),
            risk=float(command.get("risk", 0.0)),
        )
        message_id = server.registry.dispatch(action)
        print(json.dumps({"dispatched": message_id}, indent=2))
    elif kind == "save":
        core.save(state_file)
        print(json.dumps({"saved": state_file}))
    elif kind in {"exit", "quit"}:
        return False
    else:
        raise ValueError(
            "tipo deve ser status, introspect, recall, goal, perceive, task, save ou exit"
        )
    return True


def run_central(args: argparse.Namespace) -> None:
    state_path = Path(args.state_file)
    core = CognitiveFabric.load(state_path) if state_path.exists() else CognitiveFabric()
    server = CognitiveTCPServer((args.host, args.port), core, read_secret(args.secret_file))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"DragonBRX central ouvindo em {args.host}:{args.port}")
    print("Sem modelo e sem API externa. Digite comandos JSON; {\"type\":\"status\"}.")
    try:
        running = True
        while running:
            raw = input("dragonbrx> ").strip()
            if not raw:
                continue
            try:
                running = _central_command(server, core, raw, args.state_file)
            except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(json.dumps({"error": str(exc)}, ensure_ascii=False))
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        server.shutdown()
        server.server_close()
        core.save(args.state_file)


def run_agent(args: argparse.Namespace) -> None:
    selected = {
        name: BUILTIN_HANDLERS[name]
        for name in args.capability
        if name in BUILTIN_HANDLERS
    }
    unknown = set(args.capability).difference(selected)
    if unknown:
        raise SystemExit(f"capacidades desconhecidas: {', '.join(sorted(unknown))}")
    agent = TermuxAgent(args.agent_id, read_secret(args.secret_file), selected)
    agent.run(args.host, args.port)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Rede cognitiva distribuída DragonBRX")
    sub = root.add_subparsers(dest="mode", required=True)

    central = sub.add_parser("central", help="executar cérebro central")
    central.add_argument("--host", default="127.0.0.1")
    central.add_argument("--port", type=int, default=9999)
    central.add_argument("--secret-file", required=True)
    central.add_argument("--state-file", default="state/cognitive-state.json")
    central.set_defaults(func=run_central)

    agent = sub.add_parser("agent", help="executar agente em notebook ou Termux")
    agent.add_argument("--host", required=True)
    agent.add_argument("--port", type=int, default=9999)
    agent.add_argument("--agent-id", required=True)
    agent.add_argument("--secret-file", required=True)
    agent.add_argument(
        "--capability",
        action="append",
        choices=sorted(BUILTIN_HANDLERS),
        default=[],
    )
    agent.set_defaults(func=run_agent)
    return root


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.func(arguments)
