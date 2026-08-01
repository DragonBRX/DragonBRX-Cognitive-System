"""Integrity, exception-coverage and batch-write tests for the `.lira` prototype.

This suite addresses feedback items 5.3, 5.4 and 5.5 from the review:

* 5.3 — Hash validation on read: tensors are re-hashed on load and an
  ``IntegrityError`` is raised if the file was corrupted or tampered with.
* 5.4 — Exception coverage: every custom exception (``LiraError``,
  ``IncompatibleShapeError``, ``ModuleAlreadyExistsError``,
  ``IntegrityError``) and the ``ValueError`` raised for unknown module
  types are explicitly exercised.
* 5.5 — I/O batching: ``LiraContainer.batch()`` defers JSON writes and
  still produces state identical to the non-batched path.
"""

from pathlib import Path
import json

import numpy as np
import pytest

from .lira_final_demo import (
    LiraContainer,
    Module,
    LiraError,
    IncompatibleShapeError,
    ModuleAlreadyExistsError,
    IntegrityError,
)


# ----------------------------------------------------------------------
# 5.4 — Exception hierarchy and coverage
# ----------------------------------------------------------------------

def test_exception_hierarchy() -> None:
    """All custom exceptions should derive from LiraError."""
    assert issubclass(IncompatibleShapeError, LiraError)
    assert issubclass(ModuleAlreadyExistsError, LiraError)
    assert issubclass(IntegrityError, LiraError)
    assert issubclass(LiraError, Exception)


def test_module_apply_unsupported_type_raises_value_error() -> None:
    """Module.apply() should raise ValueError for an unrecognized module type."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    mod = Module(name="weird", module_type="ROUTER", tensors={})
    with pytest.raises(ValueError):
        mod.apply(base)


def test_load_module_tensors_unsupported_type_raises_value_error(tmp_path: Path) -> None:
    """Loading a module whose recorded type is unknown should raise ValueError."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    delta = np.ones((2, 2), dtype=np.float32)
    mod = Module(name="ok", module_type="DELTA", tensors={"tensor": delta})
    cont.append_module(mod)
    # Corrupt the recorded type directly in the on-disk index to simulate
    # an unsupported/future module type being encountered by an older reader.
    with open(cont.modules_index_path, "r", encoding="utf-8") as f:
        idx = json.load(f)
    idx["modules"]["ok"]["type"] = "ROUTER"
    with open(cont.modules_index_path, "w", encoding="utf-8") as f:
        json.dump(idx, f)
    cont2 = LiraContainer(tmp_path / "model")
    with pytest.raises(ValueError):
        cont2._load_module_tensors("ok")


def test_incompatible_shape_error_is_lira_error(tmp_path: Path) -> None:
    """IncompatibleShapeError should be catchable as a LiraError."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    bad = Module(name="bad", module_type="DELTA", tensors={"tensor": np.ones((3, 3), dtype=np.float32)})
    with pytest.raises(LiraError):
        cont.append_module(bad)


def test_module_already_exists_error_is_lira_error(tmp_path: Path) -> None:
    """ModuleAlreadyExistsError should be catchable as a LiraError."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    delta = np.ones((2, 2), dtype=np.float32)
    cont.append_module(Module(name="dup", module_type="DELTA", tensors={"tensor": delta}))
    with pytest.raises(LiraError):
        cont.append_module(Module(name="dup", module_type="DELTA", tensors={"tensor": delta}))


# ----------------------------------------------------------------------
# 5.3 — Hash validation on read
# ----------------------------------------------------------------------

def test_base_tensor_corruption_detected(tmp_path: Path) -> None:
    """Tampering with a base weight file on disk should be detected on load."""
    base = {"tensor": np.eye(3, dtype=np.float32)}
    model_path = tmp_path / "model"
    LiraContainer.create(model_path, base)
    # Corrupt the .npy file on disk after creation
    tensor_path = model_path / "base_weights" / "tensor.npy"
    data = bytearray(tensor_path.read_bytes())
    data[-1] ^= 0xFF  # flip bits in the last byte of the payload
    tensor_path.write_bytes(bytes(data))
    # A fresh load must now detect the mismatch when the base is accessed
    cont2 = LiraContainer(model_path)
    with pytest.raises(IntegrityError):
        cont2.get_weight("tensor")


def test_module_tensor_corruption_detected(tmp_path: Path) -> None:
    """Tampering with a module's tensor file on disk should be detected on load."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    model_path = tmp_path / "model"
    cont = LiraContainer.create(model_path, base)
    delta = np.full((2, 2), 0.5, dtype=np.float32)
    cont.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": delta}))
    # Corrupt the module tensor file on disk
    mod_path = model_path / "modules" / "inc_tensor.npy"
    data = bytearray(mod_path.read_bytes())
    data[-1] ^= 0xFF
    mod_path.write_bytes(bytes(data))
    # Reload fresh so the corrupted bytes are actually re-read from disk
    cont2 = LiraContainer(model_path)
    with pytest.raises(IntegrityError):
        cont2.get_weight("tensor")


def test_uncorrupted_tensor_passes_hash_check(tmp_path: Path) -> None:
    """A tensor that was never tampered with should load without error."""
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    delta = np.full((2, 2), 0.5, dtype=np.float32)
    cont.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": delta}))
    # Should not raise
    weight = cont.get_weight("tensor")
    np.testing.assert_allclose(weight, base["tensor"] + delta)


# ----------------------------------------------------------------------
# 5.5 — Batch-write mode
# ----------------------------------------------------------------------

def test_batch_mode_produces_same_state_as_write_through(tmp_path: Path) -> None:
    """batch() should defer writes but leave the same final on-disk state."""
    base = {"tensor": np.zeros((1,), dtype=np.float32)}

    # Reference: write-through (default) behaviour
    cont_ref = LiraContainer.create(tmp_path / "ref", base)
    for i in range(20):
        cont_ref.append_module(
            Module(name=f"m{i}", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}, domain=f"cat/{i}")
        )

    # Batched behaviour
    cont_batch = LiraContainer.create(tmp_path / "batch", base)
    with cont_batch.batch():
        for i in range(20):
            cont_batch.append_module(
                Module(name=f"m{i}", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}, domain=f"cat/{i}")
            )

    assert cont_batch.current_modules() == cont_ref.current_modules()
    np.testing.assert_allclose(cont_batch.get_weight("tensor"), cont_ref.get_weight("tensor"))
    assert set(cont_batch.list_categories()) == set(cont_ref.list_categories())

    # Confirm the batched container's state survives a fresh reload from disk
    reloaded = LiraContainer(tmp_path / "batch")
    assert reloaded.current_modules() == cont_ref.current_modules()
    np.testing.assert_allclose(reloaded.get_weight("tensor"), cont_ref.get_weight("tensor"))


def test_batch_defers_writes_until_exit(tmp_path: Path) -> None:
    """While inside batch(), the on-disk history file should not change yet."""
    base = {"tensor": np.zeros((1,), dtype=np.float32)}
    cont = LiraContainer.create(tmp_path / "model", base)
    with open(cont.history_path, "r", encoding="utf-8") as f:
        history_before = f.read()
    with cont.batch():
        cont.append_module(Module(name="m0", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}))
        with open(cont.history_path, "r", encoding="utf-8") as f:
            history_during = f.read()
        assert history_during == history_before  # not flushed yet
    with open(cont.history_path, "r", encoding="utf-8") as f:
        history_after = f.read()
    assert history_after != history_before  # flushed on exit
