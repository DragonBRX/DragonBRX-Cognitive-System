"""Tests for the simplified `.lira` container implementation.

This test suite uses `pytest` to verify that the `LiraContainer`
behaves as expected.  It covers creation, module addition, category
updates, experience logging, weight computation and rollback.
"""

import numpy as np
import pytest
from pathlib import Path

from .lira_final_demo import LiraContainer, Module


def test_container_creation_and_module_updates(tmp_path: Path) -> None:
    # Create base weights
    base = {
        # Use a 3×3 weight matrix to test LoRA updates properly.
        "tensor": np.array(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        ),
    }
    container_path = tmp_path / "model"
    cont = LiraContainer.create(container_path, base, quantization="fp16")
    # Ensure base info is correct
    assert cont.current_modules() == []
    assert cont.list_categories() == []
    # Add delta module
    delta = np.full((3, 3), 0.5, dtype=np.float32)
    m1 = Module(name="inc", module_type="DELTA", tensors={"tensor": delta}, domain="cat/inc")
    cont.append_module(m1)
    # Module should appear in active modules and category
    assert cont.current_modules() == ["inc"]
    assert "cat/inc" in cont.list_categories()
    assert cont.modules_in_category("cat/inc") == ["inc"]
    # Effective weight should reflect delta addition
    weight = cont.get_weight("tensor")
    np.testing.assert_allclose(weight, base["tensor"] + delta)
    # Add LoRA module: rank‑1 update (3×1 × 1×3)
    A = np.array([[1.0], [0.0], [1.0]], dtype=np.float32)
    B = np.array([[0.2, 0.0, -0.1]], dtype=np.float32)
    m2 = Module(name="rank1", module_type="LORA", tensors={"tensor": (A, B)}, domain="cat/lora")
    cont.append_module(m2)
    # Active modules should be both
    assert cont.current_modules() == ["inc", "rank1"]
    # Effective weight should include both updates
    lora_update = A @ B
    expected = base["tensor"] + delta + lora_update
    np.testing.assert_allclose(cont.get_weight("tensor"), expected)
    # Experience logging
    cont.add_experience({"prompt": "P", "response": "R", "score": 1.0})
    assert len(cont.list_experiences()) == 1
    # Rollback to generation 0 (no modules)
    cont.rollback(0)
    assert cont.current_modules() == []
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"])
