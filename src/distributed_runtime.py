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
import math
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
from uuid import uuid4

from cognitive_fabric import Action, CognitiveFabric
from prompt_system import PromptSystem
from pairing import load_pairing, public_pairing


PROTOCOL = "dragonbrx-node"
VERSION = 1
MAX_MESSAGE_BYTES = 1_048_576
DEFAULT_DISCOVERY_PORT = 9998
Handler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class ReplayGuard:
    """Bounded nonce cache with a strict clock window."""

    def __init__(
        self,
        *,
        max_age_seconds: float = 120.0,
        max_entries: int = 8_192,
    ) -> None:
        self.max_age_seconds = max(10.0, float(max_age_seconds))
        self.max_entries = max(256, int(max_entries))
        self._seen: Dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def accept(self, message: Mapping[str, Any]) -> bool:
        try:
            timestamp = float(message["timestamp"])
        except (KeyError, TypeError, ValueError):
            return False
        now = time.time()
        if not math.isfinite(timestamp):
            return False
        if abs(now - timestamp) > self.max_age_seconds:
            return False
        sender = str(message.get("sender", "")).strip()
        message_id = str(message.get("message_id", "")).strip()
        if not sender or len(message_id) < 16:
            return False
        key = (sender, message_id)
        with self._lock:
            cutoff = now - self.max_age_seconds
            self._seen = {
                item: seen_at
                for item, seen_at in self._seen.items()
                if seen_at >= cutoff
            }
            if key in self._seen:
                return False
            if len(self._seen) >= self.max_entries:
                oldest = min(self._seen, key=self._seen.get)
                self._seen.pop(oldest, None)
            self._seen[key] = now
        return True


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


class DiscoveryBroadcaster:
    """Anuncia somente endereço e porta; autenticação continua obrigatória."""

    def __init__(
        self,
        secret: bytes,
        tcp_port: int,
        *,
        discovery_port: int = DEFAULT_DISCOVERY_PORT,
        interval: float = 2.0,
        pairing: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.secret = secret
        self.tcp_port = int(tcp_port)
        self.discovery_port = int(discovery_port)
        self.interval = max(0.5, float(interval))
        self.pairing = dict(pairing or {})
        self.service_id = hashlib.sha256(secret).hexdigest()[:12]
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def packet(self) -> bytes:
        message = sign(
            envelope(
                "discovery",
                "core",
                {
                    "service": "DragonBRX",
                    "service_id": self.service_id,
                    "tcp_port": self.tcp_port,
                    "local_only": True,
                    "pairing": self.pairing,
                },
            ),
            self.secret,
        )
        return json.dumps(
            message,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="dragonbrx-lan-discovery",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as beacon:
            beacon.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not self._stop.is_set():
                try:
                    beacon.sendto(
                        self.packet(),
                        ("255.255.255.255", self.discovery_port),
                    )
                except OSError:
                    pass
                self._stop.wait(self.interval)


def receive_message(
    stream: Any,
    secret: bytes,
    replay_guard: Optional[ReplayGuard] = None,
) -> Dict[str, Any]:
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
    if replay_guard is not None and not replay_guard.accept(data):
        raise ValueError("mensagem repetida, expirada ou sem nonce válido")
    return data


class AgentRegistry:
    def __init__(
        self,
        core: CognitiveFabric,
        *,
        lease_seconds: float = 300.0,
    ) -> None:
        self.core = core
        self.connections: Dict[str, Any] = {}
        self.inflight: Dict[str, tuple[Action, str, float]] = {}
        self.prompt_system: Optional[PromptSystem] = None
        self.lease_seconds = max(10.0, float(lease_seconds))
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
            self.inflight[message["message_id"]] = (
                action,
                decision.delegated_to,
                time.time() + self.lease_seconds,
            )
            return message["message_id"]

    @staticmethod
    def _redelivery_message(
        message_id: str,
        action: Action,
    ) -> Dict[str, Any]:
        message = envelope(
            "task",
            "core",
            {
                "action_id": action.action_id,
                "name": action.name,
                "capability": action.capability,
                "inputs": action.inputs,
                "expected": action.expected,
                "redelivered": True,
            },
        )
        message["message_id"] = message_id
        return message

    def redeliver(self, agent_id: str) -> int:
        """Reenvia leases vivos após uma reconexão do mesmo agente."""
        now = time.time()
        with self._lock:
            stream = self.connections.get(agent_id)
            if stream is None:
                return 0
            expired = [
                message_id
                for message_id, (_, _, expires_at) in self.inflight.items()
                if expires_at < now
            ]
            for message_id in expired:
                self.inflight.pop(message_id, None)
            pending = [
                (message_id, action)
                for message_id, (
                    action,
                    assigned_agent,
                    expires_at,
                ) in self.inflight.items()
                if assigned_agent == agent_id and expires_at >= now
            ]
            for message_id, action in pending:
                self.inflight[message_id] = (
                    action,
                    agent_id,
                    now + self.lease_seconds,
                )
        for message_id, action in pending:
            send_message(
                stream,
                self._redelivery_message(message_id, action),
                self.server_secret,
            )
        return len(pending)

    def complete(self, agent_id: str, body: Mapping[str, Any]) -> bool:
        """Fecha uma tarefa e transforma o resultado em aprendizagem."""
        reply_to = str(body.get("reply_to", ""))
        with self._lock:
            assignment = self.inflight.get(reply_to)
            if assignment is None:
                return False
            action, assigned_agent, expires_at = assignment
            if (
                assigned_agent != agent_id
                or time.time() > expires_at
                or str(body.get("action_id", "")) != action.action_id
                or str(body.get("capability", "")) != action.capability
            ):
                if time.time() > expires_at:
                    self.inflight.pop(reply_to, None)
                return False
            self.inflight.pop(reply_to, None)
        if action is None:
            return False
        success = 1.0 if body.get("ok") is True else 0.0
        self.core.learn_outcome(
            action,
            success,
            evidence=dict(body),
            agent_id=agent_id,
        )
        if self.prompt_system:
            for plan_id, plan in self.prompt_system.plans.items():
                if any(task.task_id == action.action_id for task in plan.tasks):
                    self.prompt_system.complete_task(
                        plan_id,
                        action.action_id,
                        body,
                        success=bool(body.get("ok") is True),
                    )
                    break
        return True


class CognitiveTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        core: CognitiveFabric,
        secret: bytes,
        prompt_system: Optional[PromptSystem] = None,
    ) -> None:
        self.core = core
        self.secret = secret
        self.prompt_system = prompt_system or PromptSystem()
        self.replay_guard = ReplayGuard()
        self.registry = AgentRegistry(core)
        self.registry.server_secret = secret
        self.registry.prompt_system = self.prompt_system
        super().__init__(address, CognitiveRequestHandler)


class CognitiveRequestHandler(socketserver.StreamRequestHandler):
    server: CognitiveTCPServer

    def handle(self) -> None:
        agent_id: Optional[str] = None
        try:
            hello = receive_message(
                self.rfile,
                self.server.secret,
                self.server.replay_guard,
            )
            if hello.get("type") != "hello":
                raise ValueError("a primeira mensagem precisa ser hello")
            body = dict(hello.get("body") or {})
            agent_id = str(body.get("agent_id", "")).strip()
            capabilities = body.get("capabilities", [])
            if not agent_id or not isinstance(capabilities, list) or not capabilities:
                raise ValueError("identidade ou capacidades inválidas")
            if str(hello.get("sender", "")).strip() != agent_id:
                raise ValueError("sender e agent_id não correspondem")
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
            self.server.registry.redeliver(agent_id)

            while True:
                message = receive_message(
                    self.rfile,
                    self.server.secret,
                    self.server.replay_guard,
                )
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
        if str(message.get("sender", "")).strip() != agent_id:
            raise ValueError("agente tentou usar a identidade de outro nó")
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
        if kind == "result":
            accepted = self.server.registry.complete(agent_id, body)
            send_message(
                self.wfile,
                envelope(
                    "result_ack",
                    "core",
                    {
                        "reply_to": body.get("reply_to"),
                        "action_id": body.get("action_id"),
                        "accepted": accepted,
                    },
                ),
                self.server.secret,
            )
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
        self._replay_guard = ReplayGuard()

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
                    accepted = receive_message(
                        stream,
                        self.secret,
                        self._replay_guard,
                    )
                    if accepted.get("type") != "accepted":
                        raise RuntimeError("registro recusado")
                    heartbeat_stop = threading.Event()
                    heartbeat = threading.Thread(
                        target=self._heartbeat_loop,
                        args=(stream, heartbeat_stop),
                        daemon=True,
                    )
                    heartbeat.start()
                    try:
                        for message in self._messages(stream):
                            self._handle(stream, message)
                    finally:
                        heartbeat_stop.set()
                        heartbeat.join(timeout=1.0)
            except (OSError, EOFError, RuntimeError, ValueError) as exc:
                print(f"[agent] conexão indisponível: {exc}; nova tentativa em {reconnect_delay}s")
                time.sleep(reconnect_delay)

    def _heartbeat_loop(
        self,
        stream: Any,
        stop: threading.Event,
        interval: float = 30.0,
    ) -> None:
        while not stop.is_set():
            try:
                self._send(stream, "heartbeat", {"load": 0.0})
            except (OSError, ValueError):
                return
            if stop.wait(interval):
                return

    def _messages(self, stream: Any):
        while True:
            yield receive_message(
                stream,
                self.secret,
                self._replay_guard,
            )

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
    elif kind == "prompt":
        plan = server.prompt_system.create_plan(str(command["request"]))
        server.prompt_system.activate(core, plan)
        print(
            json.dumps(
                server.prompt_system.status(plan.plan_id),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif kind == "plan":
        print(
            json.dumps(
                server.prompt_system.status(str(command["plan_id"])),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif kind == "plan_dispatch":
        plan_id = str(command["plan_id"])
        assigned = []
        waiting = []
        for action in server.prompt_system.actions_for_ready_tasks(plan_id):
            try:
                message_id = server.registry.dispatch(action)
                server.prompt_system.start_task(plan_id, action.action_id)
                assigned.append(
                    {"task_id": action.action_id, "message_id": message_id}
                )
            except RuntimeError as exc:
                waiting.append(
                    {
                        "task_id": action.action_id,
                        "capability": action.capability,
                        "reason": str(exc),
                    }
                )
        print(
            json.dumps(
                {"plan_id": plan_id, "assigned": assigned, "waiting": waiting},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif kind == "plan_complete":
        task = server.prompt_system.complete_task(
            str(command["plan_id"]),
            str(command["task_id"]),
            dict(command.get("result") or {}),
            success=bool(command.get("success", True)),
        )
        print(json.dumps(asdict(task), ensure_ascii=False, indent=2))
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
            "tipo deve ser status, introspect, recall, prompt, plan, "
            "plan_dispatch, plan_complete, goal, perceive, task, save ou exit"
        )
    return True


def run_central(args: argparse.Namespace) -> None:
    state_path = Path(args.state_file)
    plans_path = Path(str(state_path) + ".plans.json")
    core = CognitiveFabric.load(state_path) if state_path.exists() else CognitiveFabric()
    prompt_system = (
        PromptSystem.load(plans_path) if plans_path.exists() else PromptSystem()
    )
    secret = read_secret(args.secret_file)
    server = CognitiveTCPServer(
        (args.host, args.port),
        core,
        secret,
        prompt_system,
    )
    discovery = (
        DiscoveryBroadcaster(
            secret,
            server.server_address[1],
            discovery_port=args.discovery_port,
            pairing=(
                public_pairing(load_pairing(args.pairing_file))
                if args.pairing_file
                else None
            ),
        )
        if args.discoverable
        else None
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if discovery is not None:
        discovery.start()
    print(f"DragonBRX central ouvindo em {args.host}:{args.port}")
    if discovery is not None:
        print(
            "Descoberta LAN ativa em UDP "
            f"{args.discovery_port}; autenticação HMAC obrigatória."
        )
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
        if discovery is not None:
            discovery.stop()
        server.shutdown()
        server.server_close()
        core.save(args.state_file)
        server.prompt_system.save(plans_path)


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
    central.add_argument(
        "--pairing-file",
        help="metadados públicos do KDF, mantidos fora do repositório",
    )
    central.add_argument(
        "--discoverable",
        action="store_true",
        help="anunciar o coordenador somente por broadcast na LAN",
    )
    central.add_argument(
        "--discovery-port",
        type=int,
        default=DEFAULT_DISCOVERY_PORT,
    )
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
