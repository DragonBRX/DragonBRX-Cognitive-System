import io
import json
import sys
from pathlib import Path
import threading
import time
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive_fabric import Action, CognitiveFabric, self_test
from distributed_runtime import (
    AgentRegistry,
    TermuxAgent,
    envelope,
    sign,
    text_statistics,
    verify,
)
from prompt_system import PromptSystem


class CognitiveFabricTests(unittest.TestCase):
    def test_integrated_cycle(self):
        result = self_test()
        self.assertTrue(result["ok"])
        self.assertEqual(result["decision"]["delegated_to"], "phone-01")

    def test_state_round_trip(self):
        core = CognitiveFabric(memory_limit=32)
        core.add_goal("aprender padrão", desired=["padrão"], priority=0.8)
        core.perceive("observação", {"padrão": "azul"}, salience=0.9)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            core.save(path)
            restored = CognitiveFabric.load(path)
        self.assertIn("padrão", restored.concepts)
        self.assertEqual(len(restored.goals), 1)
        self.assertEqual(len(restored.experiences), 1)


    def test_goal_accumulates_evidence_across_events(self):
        core = CognitiveFabric()
        goal = core.add_goal("combinar sinais", desired=["alpha", "beta"])
        core.perceive("sinal", {"valor": "alpha"})
        self.assertEqual(goal.status, "active")
        core.perceive("sinal", {"valor": "beta"})
        self.assertEqual(goal.status, "completed")
        self.assertEqual(goal.progress, 1.0)

    def test_recall_and_introspection(self):
        core = CognitiveFabric()
        core.add_goal("entender energia", desired=["energia", "estável"])
        core.perceive("sensor", {"energia": "baixa"}, salience=0.9)
        core.perceive("sensor", {"energia": "estável"}, salience=0.8)
        recalled = core.recall({"energia": "baixa"}, limit=1)
        self.assertEqual(len(recalled), 1)
        self.assertIn("energia", recalled[0]["experience"]["concepts"])
        report = core.introspect()
        self.assertIn("focus", report)
        self.assertIn("strongest_associations", report)

    def test_goal_guides_action(self):
        core = CognitiveFabric()
        core.add_goal(
            "manter armazenamento íntegro",
            desired=["armazenamento", "íntegro"],
            avoid=["corrupção"],
            priority=1.0,
        )
        safe = Action(
            "safe",
            "verificar armazenamento",
            "diagnóstico",
            expected=["armazenamento", "íntegro"],
            cost=0.1,
            risk=0.1,
        )
        unsafe = Action(
            "unsafe",
            "ignorar falha",
            "local",
            expected=["corrupção"],
            risk=0.9,
        )
        self.assertEqual(core.choose([unsafe, safe]).action.action_id, "safe")


class PromptSystemTests(unittest.TestCase):
    def test_game_prompt_discovers_complete_domains(self):
        system = PromptSystem()
        plan = system.create_plan(
            "Cria um jogo 3D de aventura offline para Android"
        )
        self.assertEqual(plan.project_type, "game")
        self.assertIn("3d", plan.constraints["dimension"])
        self.assertIn("android", plan.constraints["platforms"])
        capabilities = {task.capability for task in plan.tasks}
        self.assertTrue(
            {
                "game_mechanics",
                "game_physics",
                "game_art",
                "game_audio",
                "game_ui",
                "game_testing",
                "game_optimization",
                "game_release",
            }.issubset(capabilities)
        )
        ready = system.ready_tasks(plan.plan_id)
        self.assertEqual([task.key for task in ready], ["vision"])

    def test_dependencies_unlock_progressively(self):
        system = PromptSystem()
        plan = system.create_plan("criar um jogo de plataforma")
        vision = plan.task_map()["vision"]
        system.complete_task(plan.plan_id, vision.task_id, {"scope": "small"})
        ready_keys = {task.key for task in system.ready_tasks(plan.plan_id)}
        self.assertTrue({"mechanics", "architecture", "art", "audio"}.issubset(ready_keys))
        self.assertNotIn("integration", ready_keys)

    def test_plan_persistence(self):
        system = PromptSystem()
        plan = system.create_plan("criar um jogo puzzle 2D")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plans.json"
            system.save(path)
            restored = PromptSystem.load(path)
        self.assertEqual(
            restored.plans[plan.plan_id].project_type,
            "game",
        )
        self.assertEqual(len(restored.plans[plan.plan_id].tasks), len(plan.tasks))


class DistributedProtocolTests(unittest.TestCase):

    def test_prompt_task_result_advances_plan(self):
        core = CognitiveFabric()
        prompt_system = PromptSystem()
        plan = prompt_system.create_plan("criar um jogo 2D")
        vision = plan.task_map()["vision"]
        prompt_system.complete_task(plan.plan_id, vision.task_id)
        mechanics = plan.task_map()["mechanics"]

        registry = AgentRegistry(core)
        registry.server_secret = b"x" * 32
        registry.prompt_system = prompt_system
        stream = io.BytesIO()
        registry.attach("phone-design", stream, ["game_mechanics"], "termux")
        action = next(
            action
            for action in prompt_system.actions_for_ready_tasks(plan.plan_id)
            if action.action_id == mechanics.task_id
        )
        message_id = registry.dispatch(action)
        prompt_system.start_task(plan.plan_id, mechanics.task_id)
        registry.complete(
            "phone-design",
            {"reply_to": message_id, "ok": True, "output": {"loop": "jump"}},
        )
        self.assertEqual(mechanics.status, "completed")

    def test_agent_result_closes_learning_cycle(self):
        core = CognitiveFabric()
        registry = AgentRegistry(core)
        registry.server_secret = b"x" * 32
        stream = io.BytesIO()
        registry.attach("phone-01", stream, ["system_info"], "termux")
        before = core.agents["phone-01"].reliability
        action = Action(
            "hardware-check",
            "verificar hardware",
            "system_info",
            expected=["hardware", "disponível"],
        )
        message_id = registry.dispatch(action)
        wire = json.loads(stream.getvalue().decode("utf-8").strip())
        self.assertEqual(wire["message_id"], message_id)
        closed = registry.complete(
            "phone-01",
            {"reply_to": message_id, "ok": True, "output": {"cpu_count": 8}},
        )
        self.assertTrue(closed)
        self.assertGreater(core.agents["phone-01"].reliability, before)
        self.assertTrue(any(event.kind == "outcome" for event in core.experiences))

    def test_termux_heartbeat_keeps_channel_alive(self):
        secret = b"x" * 32
        agent = TermuxAgent("phone-heartbeat", secret, {"system_info": lambda _: {}})
        stream = io.BytesIO()
        stop = threading.Event()
        thread = threading.Thread(
            target=agent._heartbeat_loop,
            args=(stream, stop, 0.01),
        )
        thread.start()
        time.sleep(0.035)
        stop.set()
        thread.join(timeout=1)
        messages = [
            json.loads(line)
            for line in stream.getvalue().decode("utf-8").splitlines()
        ]
        self.assertGreaterEqual(len(messages), 2)
        self.assertTrue(all(message["type"] == "heartbeat" for message in messages))
        self.assertTrue(all(verify(message, secret) for message in messages))

    def test_signed_message(self):
        secret = b"x" * 32
        message = envelope("heartbeat", "phone-test", {"load": 0.1})
        signed = sign(message, secret)
        self.assertTrue(verify(signed, secret))
        signed["body"]["load"] = 0.9
        self.assertFalse(verify(signed, secret))

    def test_builtin_capability(self):
        result = text_statistics({"text": "um dois\ntrês"})
        self.assertEqual(result["words"], 3)
        self.assertEqual(result["lines"], 2)
        self.assertEqual(len(result["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
