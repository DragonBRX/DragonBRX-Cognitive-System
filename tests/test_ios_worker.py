from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive_fabric import Action, CognitiveFabric
from distributed_runtime import (
    AgentRegistry,
    DiscoveryBroadcaster,
    envelope,
    verify,
)
from ios_bootstrap import pair_discovery, parse_discovery
from ios_worker import IOSWorker, IOSWorkerState, linear_gradient
from pairing import initialize_pairing, public_pairing


class IOSWorkerTests(unittest.TestCase):
    def test_lan_discovery_requires_the_private_pairing_key(self):
        secret = b"correct-key-" + b"x" * 32
        broadcaster = DiscoveryBroadcaster(secret, 9999)
        packet = broadcaster.packet()

        discovered = parse_discovery(
            packet,
            ("192.168.1.10", 9998),
            secret,
        )
        rejected = parse_discovery(
            packet,
            ("192.168.1.10", 9998),
            b"wrong-key-" + b"y" * 32,
        )

        self.assertEqual(discovered["host"], "192.168.1.10")
        self.assertEqual(discovered["port"], 9999)
        self.assertIsNone(rejected)

    def test_password_pairing_derives_key_without_storing_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pairing_path = root / "pairing.json"
            secret_path = root / "network.key"
            password = "dragao local forte 2026"
            pairing = initialize_pairing(
                password,
                pairing_file=pairing_path,
                secret_file=secret_path,
            )
            secret = secret_path.read_bytes().strip()
            broadcaster = DiscoveryBroadcaster(
                secret,
                9999,
                pairing=public_pairing(pairing),
            )
            packet = broadcaster.packet()

            paired = pair_discovery(
                packet,
                ("192.168.1.10", 9998),
                password,
            )
            wrong = pair_discovery(
                packet,
                ("192.168.1.10", 9998),
                "senha totalmente errada",
            )

            self.assertEqual(paired[0]["host"], "192.168.1.10")
            self.assertEqual(paired[1], secret)
            self.assertIsNone(wrong)
            self.assertNotIn(
                password,
                pairing_path.read_text(encoding="utf-8"),
            )
            self.assertNotIn(password.encode("utf-8"), secret)

    def test_two_digit_password_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "12 caracteres"):
                initialize_pairing(
                    "99",
                    pairing_file=root / "pairing.json",
                    secret_file=root / "network.key",
                )

    def test_linear_gradient_is_real_and_deterministic(self):
        result = linear_gradient(
            {
                "features": [[1, 2], [3, 4]],
                "targets": [1, 2],
                "weights": [0, 0],
                "bias": 0,
            }
        )

        self.assertEqual(result["objective"], "mean_squared_error")
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["features"], 2)
        self.assertAlmostEqual(result["loss"], 2.5)
        self.assertEqual(result["gradient"], [-7.0, -10.0])
        self.assertAlmostEqual(result["bias_gradient"], -3.0)

    def test_checkpoint_survives_restart_until_authenticated_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ios-worker-state.json"
            first = IOSWorkerState(path, "iphone-test")
            first.put(
                "lease-1",
                {
                    "reply_to": "lease-1",
                    "action_id": "action-1",
                    "capability": "system_info",
                    "ok": True,
                },
            )

            restored = IOSWorkerState(path, "iphone-test")
            self.assertEqual(restored.pending_ids(), ["lease-1"])
            self.assertTrue(restored.get("lease-1")["ok"])
            self.assertTrue(restored.acknowledge("lease-1", True))
            self.assertEqual(restored.pending_ids(), [])

    def test_redelivered_task_reuses_cached_result(self):
        with tempfile.TemporaryDirectory() as directory:
            state = IOSWorkerState(
                Path(directory) / "state.json",
                "iphone-idempotent",
            )
            calls = 0

            def handler(_):
                nonlocal calls
                calls += 1
                return {"value": 42}

            secret = b"x" * 32
            worker = IOSWorker(
                "iphone-idempotent",
                secret,
                {"bounded_test": handler},
                state,
            )
            stream = io.BytesIO()
            task = envelope(
                "task",
                "core",
                {
                    "action_id": "action-1",
                    "capability": "bounded_test",
                    "inputs": {},
                },
            )

            worker._handle(stream, task)
            worker._handle(stream, task)

            messages = [
                json.loads(line)
                for line in stream.getvalue().decode("utf-8").splitlines()
            ]
            self.assertEqual(calls, 1)
            self.assertEqual(len(messages), 2)
            self.assertTrue(all(verify(item, secret) for item in messages))
            self.assertNotIn("resumed", messages[0]["body"])
            self.assertTrue(messages[1]["body"]["resumed"])

    def test_server_redelivers_live_lease_to_reconnected_iphone(self):
        core = CognitiveFabric()
        registry = AgentRegistry(core, lease_seconds=60)
        registry.server_secret = b"x" * 32
        first_stream = io.BytesIO()
        registry.attach(
            "iphone-resume",
            first_stream,
            ["system_info"],
            "ios-a-shell",
        )
        action = Action(
            "ios-check",
            "verificar iPhone",
            "system_info",
        )
        message_id = registry.dispatch(action)
        registry.detach("iphone-resume")

        resumed_stream = io.BytesIO()
        registry.attach(
            "iphone-resume",
            resumed_stream,
            ["system_info"],
            "ios-a-shell",
        )
        count = registry.redeliver("iphone-resume")
        message = json.loads(
            resumed_stream.getvalue().decode("utf-8").strip()
        )

        self.assertEqual(count, 1)
        self.assertEqual(message["message_id"], message_id)
        self.assertTrue(message["body"]["redelivered"])
        self.assertTrue(verify(message, registry.server_secret))


if __name__ == "__main__":
    unittest.main()
