"""Persistence and rollback tests for the `.lira` prototype.

These tests verify that containers can be saved and reloaded correctly
and that rollback operations behave as expected when additional modules
are appended after a rollback.
"""

from pathlib import Path
import numpy as np
import pytest

from .lira_final_demo import LiraContainer, Module


def test_persistence_and_reload(tmp_path: Path) -> None:
    """A container should preserve its state when reloaded from disk."""
    # Use a two‑dimensional base tensor so that LoRA updates apply naturally
    base = {"tensor": np.eye(3, dtype=np.float32)}
    model_path = tmp_path / "model"
    cont1 = LiraContainer.create(model_path, base)
    # Append a delta module (same shape as base)
    delta = 0.5 * np.eye(3, dtype=np.float32)
    m1 = Module(name="inc", module_type="DELTA", tensors={"tensor": delta}, domain="cat/inc")
    cont1.append_module(m1)
    # Append a LoRA module (rank‑1 update)
    A = np.array([[1.0], [0.0], [-1.0]], dtype=np.float32)
    B = np.array([[0.1, -0.2, 0.3]], dtype=np.float32)
    m2 = Module(name="rank1", module_type="LORA", tensors={"tensor": (A, B)}, domain="cat/lora")
    cont1.append_module(m2)
    # Compute expected weight
    lora_update = A @ B
    expected = base["tensor"] + delta + lora_update
    # Reload the container from the same path
    cont2 = LiraContainer(model_path)
    # Ensure modules and generations match
    assert cont2.current_modules() == cont1.current_modules()
    # Verify effective weight
    np.testing.assert_allclose(cont2.get_weight("tensor"), expected)
    # Verify categories
    assert set(cont2.list_categories()) == set(cont1.list_categories())
    # Add an experience and ensure persistence
    cont1.add_experience({"prompt": "hello", "response": "world", "score": 1.0})
    cont2 = LiraContainer(model_path)
    assert len(cont2.list_experiences()) == 1


def test_rollback_integrity(tmp_path: Path) -> None:
    """Rollback should revert the active modules and allow branching of generations."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    model_path = tmp_path / "model"
    cont = LiraContainer.create(model_path, base)
    # First delta adds 1.0
    delta1 = np.full((2, 2), 1.0, dtype=np.float32)
    m1 = Module(name="m1", module_type="DELTA", tensors={"tensor": delta1})
    cont.append_module(m1)
    # Second delta subtracts 0.5
    delta2 = np.full((2, 2), -0.5, dtype=np.float32)
    m2 = Module(name="m2", module_type="DELTA", tensors={"tensor": delta2})
    cont.append_module(m2)
    # Effective weight after two modules
    expected_two = base["tensor"] + delta1 + delta2
    np.testing.assert_allclose(cont.get_weight("tensor"), expected_two)
    # Rollback to generation 0 (no modules)
    cont.rollback(0)
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"])
    # Append a new delta after rollback that doubles the tensor
    delta3 = np.full((2, 2), 2.0, dtype=np.float32)
    m3 = Module(name="m3", module_type="DELTA", tensors={"tensor": delta3})
    cont.append_module(m3)
    # Now effective weight should be base + delta3 only
    expected_after_rollback = base["tensor"] + delta3
    np.testing.assert_allclose(cont.get_weight("tensor"), expected_after_rollback)
    # Ensure current modules list reflects the new branch
    assert cont.current_modules() == ["m3"]