"""Advanced tests for the `.lira` prototype.

This module extends the basic tests with additional scenarios:

* Detecting incompatible shapes when applying DELTA modules.
* Ignoring updates for tensors not present in the base model.
* Scaling to a large number of modules and verifying accumulation.
* Validating LoRA modules with mismatched ranks.
* Preventing duplicate module names.

These tests rely on the shape validation and custom exceptions
implemented in `lira_final_demo.py`.
"""

from pathlib import Path
import numpy as np
import pytest

from .lira_final_demo import (
    LiraContainer,
    Module,
    IncompatibleShapeError,
    ModuleAlreadyExistsError,
)


def test_incompatible_shapes(tmp_path: Path) -> None:
    """DELTA modules with a shape mismatch should raise IncompatibleShapeError."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    # delta with incorrect shape (3x2 instead of 2x2)
    bad_delta = np.ones((3, 2), dtype=np.float32)
    mod = Module(name="bad", module_type="DELTA", tensors={"tensor": bad_delta})
    with pytest.raises(IncompatibleShapeError):
        cont.append_module(mod)


def test_missing_tensor_in_base(tmp_path: Path) -> None:
    """Updates to tensors not present in the base model should be ignored."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    # Module updates a non‑existent tensor
    delta = np.full((2, 2), 0.5, dtype=np.float32)
    mod = Module(name="unknown", module_type="DELTA", tensors={"other": delta})
    cont.append_module(mod)
    # The existing tensor should be unchanged
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"])
    # Accessing a missing tensor should raise KeyError
    with pytest.raises(KeyError):
        cont.get_weight("other")


def test_large_number_of_modules(tmp_path: Path) -> None:
    """Adding many DELTA modules should accumulate their updates correctly."""
    base = {"tensor": np.zeros((1,), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    # Append 100 modules each adding 1.0 to the tensor
    for i in range(100):
        delta = np.ones((1,), dtype=np.float32)
        mod = Module(name=f"inc_{i}", module_type="DELTA", tensors={"tensor": delta})
        cont.append_module(mod)
    expected = base["tensor"] + 100 * np.ones((1,), dtype=np.float32)
    np.testing.assert_allclose(cont.get_weight("tensor"), expected)


def test_lora_rank_mismatch(tmp_path: Path) -> None:
    """LoRA modules with incompatible shapes should raise IncompatibleShapeError."""
    base = {"tensor": np.eye(3, dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    # A has shape (3, 2), B has shape (3, 3): ranks do not align (B should be 2×3)
    A = np.ones((3, 2), dtype=np.float32)
    B = np.ones((3, 3), dtype=np.float32)
    mod = Module(name="bad_lora", module_type="LORA", tensors={"tensor": (A, B)})
    with pytest.raises(IncompatibleShapeError):
        cont.append_module(mod)


def test_duplicate_module_name(tmp_path: Path) -> None:
    """Adding two modules with the same name should raise ModuleAlreadyExistsError."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    delta = np.ones((2, 2), dtype=np.float32)
    mod1 = Module(name="dup", module_type="DELTA", tensors={"tensor": delta})
    mod2 = Module(name="dup", module_type="DELTA", tensors={"tensor": delta})
    cont.append_module(mod1)
    with pytest.raises(ModuleAlreadyExistsError):
        cont.append_module(mod2)