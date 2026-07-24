"""Decomposição de intenções do DragonBRX, sem LLM ou API.

Um "prompt" é tratado como uma intenção de alto nível. Receitas cognitivas
extensíveis identificam o tipo de projeto, extraem restrições explícitas e
produzem um grafo de tarefas com capacidades, dependências, entregas e critérios
de aceitação. O resultado é estrutura de trabalho, não texto gerado.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from uuid import uuid4

from cognitive_fabric import Action, CognitiveFabric


_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_+.-]{2,}")


def _words(text: str) -> set[str]:
    return {word.casefold() for word in _WORD_RE.findall(text)}


@dataclass(frozen=True)
class TaskTemplate:
    key: str
    title: str
    domain: str
    capability: str
    depends_on: Sequence[str] = ()
    outputs: Sequence[str] = ()
    acceptance: Sequence[str] = ()
    priority: float = 0.5


@dataclass
class ProjectTask:
    task_id: str
    key: str
    title: str
    domain: str
    capability: str
    depends_on: List[str]
    outputs: List[str]
    acceptance: List[str]
    priority: float
    status: str = "pending"
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectRecipe:
    name: str
    keywords: Sequence[str]
    tasks: Sequence[TaskTemplate]
    description: str


@dataclass
class ProjectPlan:
    plan_id: str
    request: str
    project_type: str
    description: str
    confidence: float
    constraints: Dict[str, Any]
    tasks: List[ProjectTask]
    created_at: float = field(default_factory=time.time)
    status: str = "planned"

    def task_map(self) -> Dict[str, ProjectTask]:
        return {task.key: task for task in self.tasks}


GAME_RECIPE = ProjectRecipe(
    name="game",
    keywords=(
        "jogo", "game", "jogar", "rpg", "plataforma", "corrida", "puzzle",
        "fps", "aventura", "simulador", "multiplayer",
    ),
    description="Produção completa de um jogo digital.",
    tasks=(
        TaskTemplate(
            "vision",
            "Definir visão e escopo do jogo",
            "design",
            "game_design",
            outputs=("visão", "público", "plataforma", "escopo"),
            acceptance=("objetivo central definido", "limites do projeto registrados"),
            priority=1.0,
        ),
        TaskTemplate(
            "mechanics",
            "Projetar regras e mecânicas",
            "mechanics",
            "game_mechanics",
            ("vision",),
            ("regras", "progressão", "controles", "economia"),
            ("loop principal jogável", "condições de vitória e falha definidas"),
            0.95,
        ),
        TaskTemplate(
            "architecture",
            "Definir arquitetura técnica",
            "engineering",
            "software_architecture",
            ("vision",),
            ("componentes", "estado", "persistência", "pipeline"),
            ("módulos e contratos definidos",),
            0.9,
        ),
        TaskTemplate(
            "physics",
            "Definir física e colisões",
            "physics",
            "game_physics",
            ("mechanics", "architecture"),
            ("movimento", "colisões", "forças", "simulação"),
            ("comportamento determinístico testável",),
            0.85,
        ),
        TaskTemplate(
            "art",
            "Criar direção de arte e pipeline de recursos",
            "art",
            "game_art",
            ("vision",),
            ("estilo visual", "personagens", "cenários", "animações"),
            ("guia visual consistente", "lista de recursos"),
            0.8,
        ),
        TaskTemplate(
            "audio",
            "Projetar música e efeitos sonoros",
            "audio",
            "game_audio",
            ("vision",),
            ("música", "efeitos", "ambiência"),
            ("mapa de eventos sonoros definido",),
            0.7,
        ),
        TaskTemplate(
            "ui",
            "Projetar interface e experiência do jogador",
            "interface",
            "game_ui",
            ("vision", "mechanics"),
            ("menus", "hud", "feedback", "acessibilidade"),
            ("fluxos principais utilizáveis",),
            0.8,
        ),
        TaskTemplate(
            "integration",
            "Integrar uma versão jogável",
            "engineering",
            "game_integration",
            ("mechanics", "architecture", "physics", "art", "audio", "ui"),
            ("build jogável",),
            ("loop principal executável do início ao fim",),
            1.0,
        ),
        TaskTemplate(
            "testing",
            "Testar regras, estabilidade e experiência",
            "quality",
            "game_testing",
            ("integration",),
            ("relatório de defeitos", "testes de jogabilidade"),
            ("falhas críticas resolvidas",),
            0.95,
        ),
        TaskTemplate(
            "optimization",
            "Medir e otimizar desempenho",
            "performance",
            "game_optimization",
            ("integration",),
            ("perfil de cpu", "perfil de memória", "orçamento gráfico"),
            ("metas de desempenho atendidas",),
            0.8,
        ),
        TaskTemplate(
            "release",
            "Empacotar e validar a distribuição",
            "release",
            "game_release",
            ("testing", "optimization"),
            ("pacote instalável", "notas da versão"),
            ("instalação limpa validada",),
            0.9,
        ),
    ),
)


SOFTWARE_RECIPE = ProjectRecipe(
    name="software",
    keywords=(
        "aplicativo", "app", "programa", "sistema", "site", "software",
        "ferramenta", "plataforma", "dashboard",
    ),
    description="Desenvolvimento de um produto de software.",
    tasks=(
        TaskTemplate(
            "requirements", "Descobrir requisitos", "product", "requirements",
            outputs=("usuários", "casos de uso", "restrições"),
            acceptance=("escopo verificável",), priority=1.0,
        ),
        TaskTemplate(
            "architecture", "Projetar arquitetura", "engineering",
            "software_architecture", ("requirements",),
            ("componentes", "dados", "interfaces"),
            ("contratos definidos",), 0.9,
        ),
        TaskTemplate(
            "experience", "Projetar experiência", "interface", "ui_design",
            ("requirements",), ("fluxos", "interface", "acessibilidade"),
            ("fluxos críticos definidos",), 0.75,
        ),
        TaskTemplate(
            "implementation", "Implementar produto", "engineering",
            "software_implementation", ("architecture", "experience"),
            ("produto executável",), ("casos de uso principais executam",), 1.0,
        ),
        TaskTemplate(
            "testing", "Validar produto", "quality", "software_testing",
            ("implementation",), ("testes", "relatório de falhas"),
            ("testes críticos aprovados",), 0.95,
        ),
        TaskTemplate(
            "release", "Preparar distribuição", "release", "software_release",
            ("testing",), ("pacote", "documentação"),
            ("instalação reproduzível",), 0.8,
        ),
    ),
)


GENERIC_RECIPE = ProjectRecipe(
    name="generic",
    keywords=(),
    description="Plano genérico para uma intenção ainda não especializada.",
    tasks=(
        TaskTemplate(
            "discovery", "Compreender intenção e restrições", "analysis",
            "intent_analysis", outputs=("objetivo", "restrições", "critérios"),
            acceptance=("resultado esperado verificável",), priority=1.0,
        ),
        TaskTemplate(
            "planning", "Decompor trabalho", "planning", "task_planning",
            ("discovery",), ("tarefas", "dependências", "riscos"),
            ("ordem executável definida",), 0.9,
        ),
        TaskTemplate(
            "execution", "Executar plano", "execution", "generic_execution",
            ("planning",), ("resultado",), ("resultado produzido",), 1.0,
        ),
        TaskTemplate(
            "validation", "Validar resultado", "quality", "generic_validation",
            ("execution",), ("evidências",), ("critérios atendidos",), 0.9,
        ),
    ),
)


class PromptSystem:
    """Transforma solicitações em grafos de trabalho rastreáveis."""

    def __init__(self, recipes: Iterable[ProjectRecipe] = ()) -> None:
        self.recipes: Dict[str, ProjectRecipe] = {
            recipe.name: recipe
            for recipe in (GAME_RECIPE, SOFTWARE_RECIPE, GENERIC_RECIPE)
        }
        for recipe in recipes:
            self.register_recipe(recipe)
        self.plans: Dict[str, ProjectPlan] = {}

    def register_recipe(self, recipe: ProjectRecipe) -> None:
        self._validate_recipe(recipe)
        self.recipes[recipe.name] = recipe

    def create_plan(self, request: str) -> ProjectPlan:
        clean = request.strip()
        if not clean:
            raise ValueError("prompt não pode estar vazio")
        recipe, confidence = self._identify(clean)
        constraints = self._extract_constraints(clean)
        tasks = [
            ProjectTask(
                task_id=uuid4().hex,
                key=template.key,
                title=template.title,
                domain=template.domain,
                capability=template.capability,
                depends_on=list(template.depends_on),
                outputs=list(template.outputs),
                acceptance=list(template.acceptance),
                priority=template.priority,
            )
            for template in recipe.tasks
        ]
        plan = ProjectPlan(
            plan_id=uuid4().hex,
            request=clean,
            project_type=recipe.name,
            description=recipe.description,
            confidence=confidence,
            constraints=constraints,
            tasks=tasks,
        )
        self._validate_plan(plan)
        self.plans[plan.plan_id] = plan
        return plan

    def activate(self, core: CognitiveFabric, plan: ProjectPlan) -> None:
        """Registra a intenção e o objetivo no estado cognitivo."""
        core.perceive(
            "project_prompt",
            {
                "plan_id": plan.plan_id,
                "request": plan.request,
                "project_type": plan.project_type,
                "constraints": plan.constraints,
                "domains": sorted({task.domain for task in plan.tasks}),
            },
            source="prompt_system",
            salience=0.95,
            confidence=plan.confidence,
        )
        core.add_goal(
            f"concluir projeto: {plan.request}",
            desired=["projeto", plan.project_type, "concluído"],
            avoid=["falha", "inseguro"],
            priority=1.0,
            goal_id=f"plan-{plan.plan_id}",
        )

    def ready_tasks(self, plan_id: str) -> List[ProjectTask]:
        plan = self._get(plan_id)
        completed = {task.key for task in plan.tasks if task.status == "completed"}
        return [
            task
            for task in plan.tasks
            if task.status == "pending" and set(task.depends_on).issubset(completed)
        ]

    def actions_for_ready_tasks(self, plan_id: str) -> List[Action]:
        plan = self._get(plan_id)
        return [
            Action(
                action_id=task.task_id,
                name=task.title,
                capability=task.capability,
                inputs={
                    "plan_id": plan.plan_id,
                    "request": plan.request,
                    "constraints": plan.constraints,
                    "expected_outputs": task.outputs,
                    "acceptance": task.acceptance,
                },
                expected=task.outputs,
                cost=max(0.0, 1.0 - task.priority),
                risk=0.1,
            )
            for task in self.ready_tasks(plan_id)
        ]

    def start_task(self, plan_id: str, task_id: str) -> ProjectTask:
        task = self._task(plan_id, task_id)
        if task not in self.ready_tasks(plan_id):
            raise ValueError("tarefa bloqueada por dependência ou estado")
        task.status = "running"
        self._refresh_plan(self._get(plan_id))
        return task

    def complete_task(
        self,
        plan_id: str,
        task_id: str,
        result: Optional[Mapping[str, Any]] = None,
        *,
        success: bool = True,
    ) -> ProjectTask:
        task = self._task(plan_id, task_id)
        if task.status not in {"pending", "running"}:
            raise ValueError("tarefa já finalizada")
        missing = [
            dependency
            for dependency in task.depends_on
            if self._task_by_key(plan_id, dependency).status != "completed"
        ]
        if missing:
            raise ValueError(f"dependências incompletas: {', '.join(missing)}")
        task.status = "completed" if success else "failed"
        task.result = dict(result or {})
        self._refresh_plan(self._get(plan_id))
        return task

    def status(self, plan_id: str) -> Dict[str, Any]:
        plan = self._get(plan_id)
        counts: Dict[str, int] = {}
        for task in plan.tasks:
            counts[task.status] = counts.get(task.status, 0) + 1
        return {
            "plan": asdict(plan),
            "counts": counts,
            "ready": [task.task_id for task in self.ready_tasks(plan_id)],
            "progress": sum(task.status == "completed" for task in plan.tasks)
            / len(plan.tasks),
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "format": "dragonbrx-prompt-plans",
            "version": 1,
            "plans": {plan_id: asdict(plan) for plan_id, plan in self.plans.items()},
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "PromptSystem":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format") != "dragonbrx-prompt-plans":
            raise ValueError("arquivo de planos incompatível")
        system = cls()
        for plan_id, value in data.get("plans", {}).items():
            tasks = [ProjectTask(**task) for task in value.pop("tasks", [])]
            plan = ProjectPlan(tasks=tasks, **value)
            system.plans[plan_id] = plan
        return system

    def _identify(self, request: str) -> tuple[ProjectRecipe, float]:
        tokens = _words(request)
        scored: List[tuple[float, ProjectRecipe]] = []
        for recipe in self.recipes.values():
            if recipe.name == "generic":
                continue
            keywords = {keyword.casefold() for keyword in recipe.keywords}
            hits = len(tokens.intersection(keywords))
            if hits:
                score = hits / max(1, min(4, len(keywords)))
                scored.append((score, recipe))
        if not scored:
            return self.recipes["generic"], 0.35
        scored.sort(key=lambda item: (item[0], item[1].name), reverse=True)
        score, recipe = scored[0]
        return recipe, min(1.0, 0.55 + score)

    @staticmethod
    def _extract_constraints(request: str) -> Dict[str, Any]:
        tokens = _words(request)
        constraints: Dict[str, Any] = {}
        dimensions = [value for value in ("2d", "3d") if value in tokens]
        platforms = [
            value
            for value in ("android", "windows", "linux", "web", "termux", "mobile")
            if value in tokens
        ]
        modes = [
            value
            for value in ("online", "offline", "multiplayer", "cooperativo", "solo")
            if value in tokens
        ]
        genres = [
            value
            for value in ("rpg", "plataforma", "corrida", "puzzle", "fps", "aventura")
            if value in tokens
        ]
        if dimensions:
            constraints["dimension"] = dimensions
        if platforms:
            constraints["platforms"] = platforms
        if modes:
            constraints["modes"] = modes
        if genres:
            constraints["genres"] = genres
        number = re.search(r"\b(\d+)\s*(?:gb|mb|fps|jogadores?)\b", request.casefold())
        if number:
            constraints["numeric_hint"] = number.group(0)
        constraints["explicit_terms"] = sorted(tokens)
        return constraints

    @staticmethod
    def _validate_recipe(recipe: ProjectRecipe) -> None:
        keys = {task.key for task in recipe.tasks}
        if len(keys) != len(recipe.tasks):
            raise ValueError(f"receita {recipe.name} possui tarefas duplicadas")
        for task in recipe.tasks:
            unknown = set(task.depends_on).difference(keys)
            if unknown:
                raise ValueError(
                    f"tarefa {task.key} depende de chaves desconhecidas: {unknown}"
                )

    def _validate_plan(self, plan: ProjectPlan) -> None:
        recipe = self.recipes[plan.project_type]
        self._validate_recipe(recipe)
        graph = {task.key: task.depends_on for task in plan.tasks}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visiting:
                raise ValueError("receita contém dependência circular")
            if key in visited:
                return
            visiting.add(key)
            for dependency in graph[key]:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in graph:
            visit(key)

    def _get(self, plan_id: str) -> ProjectPlan:
        try:
            return self.plans[plan_id]
        except KeyError as exc:
            raise KeyError(f"plano desconhecido: {plan_id}") from exc

    def _task(self, plan_id: str, task_id: str) -> ProjectTask:
        for task in self._get(plan_id).tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(f"tarefa desconhecida: {task_id}")

    def _task_by_key(self, plan_id: str, key: str) -> ProjectTask:
        try:
            return self._get(plan_id).task_map()[key]
        except KeyError as exc:
            raise KeyError(f"chave de tarefa desconhecida: {key}") from exc

    @staticmethod
    def _refresh_plan(plan: ProjectPlan) -> None:
        statuses = {task.status for task in plan.tasks}
        if statuses == {"completed"}:
            plan.status = "completed"
        elif "failed" in statuses:
            plan.status = "blocked"
        elif "running" in statuses or "completed" in statuses:
            plan.status = "active"
        else:
            plan.status = "planned"
