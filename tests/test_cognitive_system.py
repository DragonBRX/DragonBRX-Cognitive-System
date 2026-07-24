import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive_fabric import Action, CognitiveFabric, self_test
from distributed_runtime import envelope, sign, text_statistics, verify


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


class DistributedProtocolTests(unittest.TestCase):
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
