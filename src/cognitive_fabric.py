"""Núcleo cognitivo autônomo e portátil do DragonBRX.

Este módulo não encapsula nem chama um LLM. Ele implementa um ciclo cognitivo
próprio, baseado em estado simbólico e eventos:

    perceber -> integrar -> priorizar -> decidir -> delegar -> aprender

A arquitetura usa unidades conceituais e relações aprendidas, não uma tentativa
de reproduzir neurônios ou partes anatômicas do cérebro humano. Todo o estado e
todo o protocolo de subagentes são JSON, permitindo executar o núcleo em um
notebook e agentes leves em Python/Termux sem dependências externas.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from threading import RLock
import time
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional, Sequence
from uuid import uuid4
from lira_core import LiraState, CognitiveStep


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_\-]{2,}")
PROTOCOL_VERSION = 1


def _now() -> float:
    return time.time()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _tokens(value: Any) -> List[str]:
    """Extrai conceitos normalizados de qualquer payload JSON."""
    found: List[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                walk(str(key))
                walk(nested)
        elif isinstance(item, (list, tuple, set)):
            for nested in item:
                walk(nested)
        elif item is not None:
            found.extend(token.casefold() for token in _TOKEN_RE.findall(str(item)))

    walk(value)
    return list(dict.fromkeys(found))


@dataclass
class Concept:
    name: str
    activation: float = 0.0
    confidence: float = 0.5
    encounters: int = 0
    successes: int = 0
    failures: int = 0
    links: Dict[str, float] = field(default_factory=dict)

    def quality(self) -> float:
        observations = self.successes + self.failures
        if observations == 0:
            return self.confidence
        return (self.successes + 1.0) / (observations + 2.0)


@dataclass
class Goal:
    goal_id: str
    description: str
    priority: float
    desired: List[str]
    avoid: List[str] = field(default_factory=list)
    status: str = "active"
    progress: float = 0.0
    evidence: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)


@dataclass
class Experience:
    event_id: str
    kind: str
    source: str
    concepts: List[str]
    salience: float
    confidence: float
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[float] = None


@dataclass
class Action:
    action_id: str
    name: str
    capability: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected: List[str] = field(default_factory=list)
    cost: float = 0.0
    risk: float = 0.0


@dataclass
class Decision:
    cycle: int
    action: Optional[Action]
    score: float
    reasons: List[str]
    delegated_to: Optional[str] = None


@dataclass
class SubAgent:
    agent_id: str
    capabilities: List[str]
    platform: str = "unknown"
    load: float = 0.0
    reliability: float = 0.5
    last_seen: float = field(default_factory=_now)


class CognitiveFabric:
    """Motor cognitivo determinístico, inspecionável e independente de modelo."""

    def __init__(
        self,
        *,
        memory_limit: int = 2048,
        activation_decay: float = 0.82,
        link_learning_rate: float = 0.12,
        association_spread: float = 0.18,
        lira_path: str = "lira_state.json"
    ) -> None:
        if memory_limit < 16:
            raise ValueError("memory_limit deve ser >= 16")
        self.memory_limit = int(memory_limit)
        self.activation_decay = _clamp(activation_decay)
        self.link_learning_rate = _clamp(link_learning_rate)
        self.association_spread = _clamp(association_spread)
        self.concepts: Dict[str, Concept] = {}
        self.goals: Dict[str, Goal] = {}
        self.agents: Dict[str, SubAgent] = {}
        self.experiences: Deque[Experience] = deque(maxlen=self.memory_limit)
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.cycle_count = 0
        self._lock = RLock()
        self.lira = LiraState(lira_path)

    def add_goal(
        self,
        description: str,
        *,
        desired: Iterable[str],
        avoid: Iterable[str] = (),
        priority: float = 0.5,
        goal_id: Optional[str] = None,
    ) -> Goal:
        wanted = _tokens(list(desired))
        if not wanted:
            raise ValueError("um objetivo precisa de ao menos um conceito desejado")
        goal = Goal(
            goal_id=goal_id or uuid4().hex,
            description=description.strip(),
            priority=_clamp(priority),
            desired=wanted,
            avoid=_tokens(list(avoid)),
        )
        with self._lock:
            self.goals[goal.goal_id] = goal
        return goal

    def perceive(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        source: str = "local",
        salience: float = 0.5,
        confidence: float = 0.7,
        timestamp: Optional[float] = None,
    ) -> Experience:
        """Integra uma observação e aprende relações entre conceitos coexistentes."""
        clean_payload = dict(payload)
        concepts = _tokens({"kind": kind, "payload": clean_payload})
        event = Experience(
            event_id=uuid4().hex,
            kind=kind,
            source=source,
            concepts=concepts,
            salience=_clamp(salience),
            confidence=_clamp(confidence),
            timestamp=float(timestamp if timestamp is not None else _now()),
            payload=clean_payload,
        )
        boost = event.salience * event.confidence
        with self._lock:
            self.experiences.append(event)
            for name in concepts:
                concept = self.concepts.setdefault(name, Concept(name=name))
                concept.encounters += 1
                concept.activation = _clamp(concept.activation + boost)
                concept.confidence = _clamp(
                    (concept.confidence * (concept.encounters - 1) + event.confidence)
                    / concept.encounters
                )
            self._associate(concepts, boost)
            self._update_goal_progress(concepts)
        return event

    def _associate(self, names: Sequence[str], strength: float) -> None:
        delta = self.link_learning_rate * strength
        for left in names:
            for right in names:
                if left == right:
                    continue
                node = self.concepts[left]
                node.links[right] = _clamp(node.links.get(right, 0.0) + delta)

    def _update_goal_progress(self, observed: Sequence[str]) -> None:
        seen = set(observed)
        for goal in self.goals.values():
            if goal.status != "active":
                continue
            accumulated = set(goal.evidence)
            accumulated.update(seen.intersection(goal.desired))
            goal.evidence = sorted(accumulated)
            goal.progress = len(accumulated) / len(goal.desired)
            if goal.progress >= 1.0 and not seen.intersection(goal.avoid):
                goal.status = "completed"

    def register_agent(
        self,
        agent_id: str,
        capabilities: Iterable[str],
        *,
        platform: str = "termux",
        load: float = 0.0,
        reliability: float = 0.5,
    ) -> SubAgent:
        agent = SubAgent(
            agent_id=agent_id,
            capabilities=_tokens(list(capabilities)),
            platform=platform,
            load=_clamp(load),
            reliability=_clamp(reliability),
        )
        if not agent.capabilities:
            raise ValueError("subagente precisa declarar capacidades")
        with self._lock:
            self.agents[agent_id] = agent
        return agent

    def choose(self, candidates: Sequence[Action], intent: str = "") -> Decision:
        """Escolhe uma ação por objetivos, contexto, custo, risco e experiência."""
        with self._lock:
            self.cycle_count += 1
            self._decay_and_spread()
            
            step = CognitiveStep(intent=intent)
            step.domains_activated = sorted({task.capability for task in candidates}) if candidates else []
            
            if not candidates:
                decision = Decision(self.cycle_count, None, 0.0, ["sem ações candidatas"])
                step.method_result = "Nenhuma ação candidata disponível"
                step.metacognition["strategy_adopted"] = "experimental"
                self.lira.add_step(step)
                return decision

            ranked = [(self._score(action), action) for action in candidates]
            ranked.sort(key=lambda item: (item[0][0], item[1].action_id), reverse=True)
            (score, reasons), selected = ranked[0]
            
            # Lógica de Metacognição
            confidence = _clamp(score / 2.0 + 0.5)
            strategy = "immediate"
            if confidence < 0.4:
                strategy = "deep"
            elif confidence < 0.7:
                strategy = "careful"
            
            step.metacognition = {
                "confidence": confidence,
                "uncertainty_source": "baixa ativação de conceitos" if confidence < 0.5 else "competição de objetivos",
                "strategy_adopted": strategy,
                "self_correction_applied": False
            }
            
            step.interpretation = f"Priorizando {selected.name} (Estratégia: {strategy}) entre {len(candidates)} opções"
            step.hypotheses = [f"Ação {a.name} pode atingir {a.expected}" for a in candidates[:3]]
            step.decision_reason = "; ".join(reasons)
            
            agent = self._select_agent(selected.capability)
            delegated_to = agent.agent_id if agent else None
            
            decision = Decision(
                cycle=self.cycle_count,
                action=selected,
                score=score,
                reasons=reasons,
                delegated_to=delegated_to,
            )
            
            step.actions_taken = [asdict(selected)]
            step.method_result = f"Ação selecionada: {selected.name}"
            self.lira.add_step(step)
            
            return decision

    def _score(self, action: Action) -> tuple[float, List[str]]:
        expected = set(_tokens(action.expected))
        goal_gain = 0.0
        conflicts = 0.0
        reasons: List[str] = []
        for goal in self.goals.values():
            if goal.status != "active":
                continue
            match = len(expected.intersection(goal.desired)) / max(1, len(goal.desired))
            conflict = len(expected.intersection(goal.avoid)) / max(1, len(goal.avoid))
            goal_gain += goal.priority * match
            conflicts += goal.priority * conflict
        context = sum(
            self.concepts[name].activation * self.concepts[name].quality()
            for name in expected
            if name in self.concepts
        ) / max(1, len(expected))
        novelty = sum(1 for name in expected if name not in self.concepts) / max(1, len(expected))
        score = goal_gain + 0.35 * context + 0.08 * novelty
        score -= 0.45 * _clamp(action.risk) + 0.25 * _clamp(action.cost) + conflicts
        reasons.extend(
            [
                f"ganho_de_objetivo={goal_gain:.3f}",
                f"contexto={context:.3f}",
                f"novidade={novelty:.3f}",
                f"penalidade={0.45 * _clamp(action.risk) + 0.25 * _clamp(action.cost) + conflicts:.3f}",
            ]
        )
        return score, reasons

    def _select_agent(self, capability: str) -> Optional[SubAgent]:
        target = capability.casefold()
        eligible = [
            agent
            for agent in self.agents.values()
            if target in agent.capabilities and _now() - agent.last_seen < 300
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda agent: agent.reliability * (1.0 - agent.load),
        )

    def create_task(self, decision: Decision) -> Optional[Dict[str, Any]]:
        """Cria um envelope JSON que pode ser enviado a um subagente."""
        if decision.action is None or decision.delegated_to is None:
            return None
        message_id = uuid4().hex
        envelope = {
            "protocol": "dragonbrx-cognitive",
            "version": PROTOCOL_VERSION,
            "message_id": message_id,
            "type": "task",
            "sender": "core",
            "recipient": decision.delegated_to,
            "timestamp": _now(),
            "body": {
                "action_id": decision.action.action_id,
                "name": decision.action.name,
                "capability": decision.action.capability,
                "inputs": decision.action.inputs,
                "expected": decision.action.expected,
            },
        }
        envelope["checksum"] = self._checksum(envelope)
        with self._lock:
            self.pending[message_id] = envelope
            self.agents[decision.delegated_to].load = _clamp(
                self.agents[decision.delegated_to].load + 0.1
            )
        return envelope

    def receive(self, envelope: Mapping[str, Any]) -> Experience:
        """Valida resultado/observação JSON de um subagente e o integra."""
        data = dict(envelope)
        supplied = data.pop("checksum", None)
        if data.get("protocol") != "dragonbrx-cognitive":
            raise ValueError("protocolo desconhecido")
        if data.get("version") != PROTOCOL_VERSION:
            raise ValueError("versão de protocolo incompatível")
        if supplied != self._checksum(data):
            raise ValueError("checksum inválido")
        if data.get("type") not in {"result", "observation", "heartbeat"}:
            raise ValueError("tipo de mensagem não aceito")

        sender = str(data.get("sender", "unknown"))
        body = dict(data.get("body") or {})
        with self._lock:
            agent = self.agents.get(sender)
            if agent:
                agent.last_seen = _now()
                agent.load = _clamp(body.get("load", agent.load - 0.1))
            reply_to = body.get("reply_to")
            if reply_to:
                self.pending.pop(str(reply_to), None)

        return self.perceive(
            str(data["type"]),
            body,
            source=sender,
            salience=float(body.get("salience", 0.6)),
            confidence=float(body.get("confidence", 0.7)),
            timestamp=float(data.get("timestamp", _now())),
        )

    def learn_outcome(
        self,
        action: Action,
        success: float,
        *,
        evidence: Optional[Mapping[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Experience:
        """Reforça ou enfraquece conceitos usando o resultado real da ação."""
        outcome = _clamp(success)
        event = self.perceive(
            "outcome",
            {
                "action": action.name,
                "expected": action.expected,
                "evidence": dict(evidence or {}),
                "success": outcome,
            },
            salience=max(0.5, abs(outcome - 0.5) * 2.0),
            confidence=0.9,
        )
        event.outcome = outcome
        with self._lock:
            for name in _tokens(action.expected):
                concept = self.concepts.setdefault(name, Concept(name=name))
                if outcome >= 0.5:
                    concept.successes += 1
                else:
                    concept.failures += 1
                concept.confidence = concept.quality()
            if agent_id and agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.reliability = _clamp(0.8 * agent.reliability + 0.2 * outcome)
                agent.load = _clamp(agent.load - 0.1)
        return event

    def _decay_and_spread(self) -> None:
        """Decai a atenção atual e propaga parte dela pelas relações aprendidas."""
        incoming: Dict[str, float] = {}
        for concept in self.concepts.values():
            concept.activation *= self.activation_decay
            total_link = sum(concept.links.values())
            if concept.activation <= 0.0 or total_link <= 0.0:
                continue
            budget = concept.activation * self.association_spread
            for target, weight in concept.links.items():
                if target in self.concepts:
                    incoming[target] = incoming.get(target, 0.0) + budget * weight / total_link
        for name, boost in incoming.items():
            self.concepts[name].activation = _clamp(
                self.concepts[name].activation + boost
            )

    def recall(self, query: Any, limit: int = 5) -> List[Dict[str, Any]]:
        """Recupera experiências por conceitos, atenção, saliência e recência."""
        wanted = set(_tokens(query))
        if limit < 1:
            return []
        now = _now()
        ranked: List[tuple[float, Experience]] = []
        with self._lock:
            for event in self.experiences:
                concepts = set(event.concepts)
                overlap = len(wanted.intersection(concepts)) / max(1, len(wanted))
                attention = sum(
                    self.concepts[name].activation
                    for name in concepts
                    if name in self.concepts
                ) / max(1, len(concepts))
                age_hours = max(0.0, now - event.timestamp) / 3600.0
                recency = 1.0 / (1.0 + age_hours)
                score = (
                    0.55 * overlap
                    + 0.20 * attention
                    + 0.15 * event.salience
                    + 0.10 * recency
                )
                if overlap > 0.0 or not wanted:
                    ranked.append((score, event))
        ranked.sort(key=lambda item: (item[0], item[1].timestamp), reverse=True)
        return [
            {"score": round(score, 6), "experience": asdict(event)}
            for score, event in ranked[:limit]
        ]

    def introspect(self, limit: int = 8) -> Dict[str, Any]:
        """Produz um relatório interno estruturado, sem geração por modelo."""
        with self._lock:
            active = sorted(
                self.concepts.values(),
                key=lambda item: item.activation,
                reverse=True,
            )[:limit]
            associations: List[Dict[str, Any]] = []
            for concept in active:
                if not concept.links:
                    continue
                target, strength = max(
                    concept.links.items(), key=lambda item: item[1]
                )
                associations.append(
                    {
                        "from": concept.name,
                        "to": target,
                        "strength": round(strength, 4),
                    }
                )
            unresolved = [
                {
                    "goal_id": goal.goal_id,
                    "description": goal.description,
                    "progress": round(goal.progress, 4),
                    "missing": sorted(set(goal.desired).difference(goal.evidence)),
                }
                for goal in self.goals.values()
                if goal.status == "active"
            ]
            return {
                "cycle": self.cycle_count,
                "focus": [item.name for item in active],
                "strongest_associations": associations,
                "unresolved_goals": unresolved,
            }

    @staticmethod
    def _checksum(envelope: Mapping[str, Any]) -> str:
        clean = dict(envelope)
        clean.pop("checksum", None)
        raw = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            active = sorted(
                self.concepts.values(), key=lambda item: item.activation, reverse=True
            )[:12]
            return {
                "cycle": self.cycle_count,
                "concepts": len(self.concepts),
                "experiences": len(self.experiences),
                "pending_tasks": len(self.pending),
                "active_concepts": [
                    {
                        "name": item.name,
                        "activation": round(item.activation, 4),
                        "quality": round(item.quality(), 4),
                    }
                    for item in active
                ],
                "goals": [asdict(goal) for goal in self.goals.values()],
                "agents": [asdict(agent) for agent in self.agents.values()],
            }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "format": "dragonbrx-cognitive-state",
                "version": 1,
                "config": {
                    "memory_limit": self.memory_limit,
                    "activation_decay": self.activation_decay,
                    "link_learning_rate": self.link_learning_rate,
                    "association_spread": self.association_spread,
                },
                "cycle_count": self.cycle_count,
                "concepts": {name: asdict(item) for name, item in self.concepts.items()},
                "goals": {key: asdict(item) for key, item in self.goals.items()},
                "agents": {key: asdict(item) for key, item in self.agents.items()},
                "experiences": [asdict(item) for item in self.experiences],
                "pending": self.pending,
            }

    def save(self, path: str | Path) -> None:
        """Persiste estado de modo atômico em Linux, Windows ou Termux."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "CognitiveFabric":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != "dragonbrx-cognitive-state":
            raise ValueError("arquivo de estado incompatível")
        core = cls(**data["config"])
        core.cycle_count = int(data.get("cycle_count", 0))
        core.concepts = {
            key: Concept(**value) for key, value in data.get("concepts", {}).items()
        }
        core.goals = {key: Goal(**value) for key, value in data.get("goals", {}).items()}
        core.agents = {
            key: SubAgent(**value) for key, value in data.get("agents", {}).items()
        }
        core.experiences.extend(
            Experience(**value) for value in data.get("experiences", [])
        )
        core.pending = dict(data.get("pending", {}))
        return core


def self_test() -> Dict[str, Any]:
    """Teste funcional pequeno, executável sem framework ou dependências."""
    core = CognitiveFabric(memory_limit=32)
    core.add_goal(
        "manter sensores disponíveis",
        desired=["sensor", "disponivel"],
        avoid=["falha"],
        priority=0.9,
    )
    core.perceive(
        "telemetria",
        {"sensor": "temperatura", "estado": "instavel"},
        salience=0.8,
    )
    core.register_agent("phone-01", ["diagnostico"], platform="termux", reliability=0.8)
    actions = [
        Action(
            "inspect",
            "diagnosticar sensor",
            "diagnostico",
            {"sensor": "temperatura"},
            ["sensor", "disponivel"],
            cost=0.2,
            risk=0.1,
        ),
        Action(
            "ignore",
            "ignorar evento",
            "local",
            {},
            ["falha"],
            cost=0.0,
            risk=0.8,
        ),
    ]
    decision = core.choose(actions)
    assert decision.action and decision.action.action_id == "inspect"
    assert decision.delegated_to == "phone-01"
    task = core.create_task(decision)
    assert task and task["recipient"] == "phone-01"
    core.learn_outcome(decision.action, 1.0, evidence={"status": "recuperado"})
    state = core.status()
    assert state["concepts"] > 0 and state["cycle"] == 1
    return {"ok": True, "decision": asdict(decision), "status": state}


if __name__ == "__main__":
    print(json.dumps(self_test(), ensure_ascii=False, indent=2))
