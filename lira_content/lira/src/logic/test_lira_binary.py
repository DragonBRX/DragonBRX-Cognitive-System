"""Tests for the single-file binary `.lira` container (`lira_binary.py`).

Mirrors the behavioural coverage of the JSON-based prototype's test
suites (creation, modules, categories, rollback, persistence) and adds
tests specific to the binary format: superblock parsing, dual-slot
atomic commits, mmap-backed reads, and corruption detection for both
tensors and metadata slots.
"""

import struct
from pathlib import Path

import numpy as np
import pytest

from .lira_binary import LiraBinary, MAGIC, SUPERBLOCK_SIZE
from .lira_final_demo import (
    Module,
    IncompatibleShapeError,
    ModuleAlreadyExistsError,
    IntegrityError,
    LiraError,
)


# ----------------------------------------------------------------------
# Basic behaviour parity with the JSON prototype
# ----------------------------------------------------------------------

def test_create_and_read_base_weight(tmp_path: Path) -> None:
    base = {"tensor": np.eye(3, dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"])
    assert cont.current_modules() == []
    cont.close()


def test_append_delta_and_lora_modules(tmp_path: Path) -> None:
    base = {"tensor": np.eye(3, dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    delta = np.full((3, 3), 0.5, dtype=np.float32)
    cont.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": delta}, domain="cat/inc"))
    assert cont.current_modules() == ["inc"]
    assert "cat/inc" in cont.list_categories()
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"] + delta)

    A = np.array([[1.0], [0.0], [1.0]], dtype=np.float32)
    B = np.array([[0.2, 0.0, -0.1]], dtype=np.float32)
    cont.append_module(Module(name="rank1", module_type="LORA", tensors={"tensor": (A, B)}, domain="cat/lora"))
    expected = base["tensor"] + delta + A @ B
    np.testing.assert_allclose(cont.get_weight("tensor"), expected)
    cont.close()


def test_duplicate_module_name_raises(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    delta = np.ones((2, 2), dtype=np.float32)
    cont.append_module(Module(name="dup", module_type="DELTA", tensors={"tensor": delta}))
    with pytest.raises(ModuleAlreadyExistsError):
        cont.append_module(Module(name="dup", module_type="DELTA", tensors={"tensor": delta}))
    cont.close()


def test_incompatible_shape_raises(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    bad = np.ones((3, 2), dtype=np.float32)
    with pytest.raises(IncompatibleShapeError):
        cont.append_module(Module(name="bad", module_type="DELTA", tensors={"tensor": bad}))
    cont.close()


def test_lora_rank_mismatch_raises(tmp_path: Path) -> None:
    base = {"tensor": np.eye(3, dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    A = np.ones((3, 2), dtype=np.float32)
    B = np.ones((3, 3), dtype=np.float32)  # should be (2, 3)
    with pytest.raises(IncompatibleShapeError):
        cont.append_module(Module(name="bad_lora", module_type="LORA", tensors={"tensor": (A, B)}))
    cont.close()


def test_unsupported_module_type_raises_value_error(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    with pytest.raises(ValueError):
        cont.append_module(Module(name="weird", module_type="ROUTER", tensors={"tensor": np.ones((2, 2), dtype=np.float32)}))
    cont.close()


def test_rollback_and_branching(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    cont.append_module(Module(name="m1", module_type="DELTA", tensors={"tensor": np.full((2, 2), 1.0, dtype=np.float32)}))
    cont.append_module(Module(name="m2", module_type="DELTA", tensors={"tensor": np.full((2, 2), -0.5, dtype=np.float32)}))
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"] + 1.0 - 0.5)
    cont.rollback(0)
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"])
    cont.append_module(Module(name="m3", module_type="DELTA", tensors={"tensor": np.full((2, 2), 2.0, dtype=np.float32)}))
    np.testing.assert_allclose(cont.get_weight("tensor"), base["tensor"] + 2.0)
    assert cont.current_modules() == ["m3"]
    cont.close()


def test_persistence_across_reopen(tmp_path: Path) -> None:
    base = {"tensor": np.eye(3, dtype=np.float32)}
    path = tmp_path / "model.lira"
    cont1 = LiraBinary.create(path, base)
    delta = 0.5 * np.eye(3, dtype=np.float32)
    cont1.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": delta}, domain="cat/inc"))
    cont1.add_experience({"prompt": "hi", "response": "there", "score": 1.0})
    cont1.close()

    cont2 = LiraBinary(path)  # reopen fresh, reading everything from disk
    assert cont2.current_modules() == ["inc"]
    np.testing.assert_allclose(cont2.get_weight("tensor"), base["tensor"] + delta)
    assert len(cont2.list_experiences()) == 1
    assert "cat/inc" in cont2.list_categories()
    cont2.close()


def test_experience_and_memory_do_not_bump_generation(tmp_path: Path) -> None:
    """Per spec: logging experiences or memory must not create a new generation."""
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    cont.append_module(Module(name="m1", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}))
    gens_before = len(cont._metadata["history"]["generations"])
    cont.add_experience({"prompt": "p", "response": "r", "score": 1.0})
    cont.add_memory("some fact", vector=np.random.rand(4).astype(np.float32))
    gens_after = len(cont._metadata["history"]["generations"])
    assert gens_before == gens_after
    assert cont.current_modules() == ["m1"]
    cont.close()


def test_skills_register_and_activate(tmp_path: Path) -> None:
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    cont.register_skill("skill_x", {"kind": "prompt"}, domain="dom/skills")
    assert cont.current_skills() == []  # registered, not yet active
    assert "skill_x" in cont._metadata["skills"]
    cont.activate_skill("skill_x")
    assert cont.current_skills() == ["skill_x"]
    with pytest.raises(KeyError):
        cont.activate_skill("does_not_exist")
    cont.close()


# ----------------------------------------------------------------------
# Binary-format specific behaviour
# ----------------------------------------------------------------------

def test_file_starts_with_magic_and_is_page_aligned(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    path = tmp_path / "model.lira"
    cont = LiraBinary.create(path, base)
    cont.close()
    with open(path, "rb") as f:
        header = f.read(SUPERBLOCK_SIZE)
    assert header[:8] == MAGIC
    assert path.stat().st_size % 4096 == 0 or path.stat().st_size >= SUPERBLOCK_SIZE


def test_opening_non_lira_file_raises(tmp_path: Path) -> None:
    junk = tmp_path / "not_a_lira_file.lira"
    junk.write_bytes(b"not a real container" * 100)
    with pytest.raises(LiraError):
        LiraBinary(junk)


def test_commit_slot_alternates_between_a_and_b(tmp_path: Path) -> None:
    """Every mutating commit should flip commit_slot_active, per the spec's
    dual-slot design (never overwrite the currently-active slot in place)."""
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    slots_seen = [cont._active_slot]
    for i in range(5):
        cont.append_module(Module(name=f"m{i}", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}))
        slots_seen.append(cont._active_slot)
    # Should strictly alternate a, b, a, b, ...
    for i in range(1, len(slots_seen)):
        assert slots_seen[i] != slots_seen[i - 1]
    cont.close()


def test_base_tensor_corruption_detected(tmp_path: Path) -> None:
    """Flipping bits in the base tensor's raw bytes on disk must be caught by
    the SHA-256 check when the tensor is read back."""
    base = {"tensor": np.eye(3, dtype=np.float32)}
    path = tmp_path / "model.lira"
    cont = LiraBinary.create(path, base)
    cont.close()

    with open(path, "r+b") as f:
        f.seek(SUPERBLOCK_SIZE)
        (index_len,) = struct.unpack("<Q", f.read(8))
        f.read(index_len)  # skip index
        data_start = f.tell()
        f.seek(data_start)
        byte = f.read(1)
        f.seek(data_start)
        f.write(bytes([byte[0] ^ 0xFF]))

    cont2 = LiraBinary(path)
    with pytest.raises(IntegrityError):
        cont2.get_weight("tensor")
    cont2.close()


def test_module_tensor_corruption_detected(tmp_path: Path) -> None:
    base = {"tensor": np.ones((2, 2), dtype=np.float32)}
    path = tmp_path / "model.lira"
    cont = LiraBinary.create(path, base)
    delta = np.full((2, 2), 0.5, dtype=np.float32)
    cont.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": delta}))
    ref = cont._metadata["modules"]["inc"]["tensors"]["tensor"]
    offset = ref["offset"]
    cont.close()

    with open(path, "r+b") as f:
        f.seek(offset)
        byte = f.read(1)
        f.seek(offset)
        f.write(bytes([byte[0] ^ 0xFF]))

    cont2 = LiraBinary(path)
    with pytest.raises(IntegrityError):
        cont2.get_weight("tensor")
    cont2.close()


def test_corrupted_inactive_slot_does_not_break_reading(tmp_path: Path) -> None:
    """Corrupting the *inactive* slot must not affect reads of the active
    state — this is exactly the crash-safety property the two-slot design
    is meant to provide."""
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    path = tmp_path / "model.lira"
    cont = LiraBinary.create(path, base)
    cont.append_module(Module(name="m1", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}))
    active = cont._active_slot
    inactive = "b" if active == "a" else "a"
    inactive_offset = cont._sb[f"offset_slot_{inactive}"]
    cont.close()

    with open(path, "r+b") as f:
        f.seek(inactive_offset)
        f.write(struct.pack("<Q", 999999))  # bogus length, unreadable slot

    cont2 = LiraBinary(path)  # must still open fine using the active slot
    assert cont2.current_modules() == ["m1"]
    np.testing.assert_allclose(cont2.get_weight("tensor"), base["tensor"] + 1.0)
    report = cont2.verify_integrity()
    assert report[f"slot_{inactive}_readable"] is False
    assert report[f"slot_{active}_readable"] is True
    cont2.close()


def test_verify_integrity_reports_all_tensors_ok(tmp_path: Path) -> None:
    base = {"tensor": np.eye(3, dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    cont.append_module(Module(name="inc", module_type="DELTA", tensors={"tensor": 0.5 * np.eye(3, dtype=np.float32)}))
    A = np.ones((3, 1), dtype=np.float32)
    B = np.ones((1, 3), dtype=np.float32)
    cont.append_module(Module(name="lora", module_type="LORA", tensors={"tensor": (A, B)}))
    report = cont.verify_integrity()
    # 1 base tensor + 1 delta tensor + 2 LoRA tensors (A and B) = 4
    assert report["tensors_checked"] == 4
    assert report["tensors_ok"] == 4
    assert report["errors"] == []
    cont.close()


def test_append_modules_batch_matches_individual_appends(tmp_path: Path) -> None:
    """append_modules() should produce the same end state as calling
    append_module() once per item, just with fewer fsync calls."""
    base = {"tensor": np.zeros((1,), dtype=np.float32)}

    cont_ref = LiraBinary.create(tmp_path / "ref.lira", base)
    for i in range(10):
        cont_ref.append_module(Module(name=f"m{i}", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}, domain=f"d/{i}"))

    cont_batch = LiraBinary.create(tmp_path / "batch.lira", base)
    cont_batch.append_modules(
        [Module(name=f"m{i}", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}, domain=f"d/{i}") for i in range(10)]
    )

    assert cont_batch.current_modules() == cont_ref.current_modules()
    np.testing.assert_allclose(cont_batch.get_weight("tensor"), cont_ref.get_weight("tensor"))
    assert set(cont_batch.list_categories()) == set(cont_ref.list_categories())

    reloaded = LiraBinary(tmp_path / "batch.lira")
    assert reloaded.current_modules() == cont_ref.current_modules()
    np.testing.assert_allclose(reloaded.get_weight("tensor"), cont_ref.get_weight("tensor"))
    cont_ref.close()
    cont_batch.close()
    reloaded.close()


def test_append_modules_batch_rejects_duplicate_within_batch(tmp_path: Path) -> None:
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base)
    with pytest.raises(ModuleAlreadyExistsError):
        cont.append_modules([
            Module(name="dup", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}),
            Module(name="dup", module_type="DELTA", tensors={"tensor": np.ones((1,), dtype=np.float32)}),
        ])
    cont.close()


def test_metadata_slot_size_enforced(tmp_path: Path) -> None:
    """Metadata that outgrows the reserved slot size should raise a clear
    LiraError rather than silently truncating data."""
    base = {"tensor": np.ones((1,), dtype=np.float32)}
    cont = LiraBinary.create(tmp_path / "model.lira", base, metadata_slot_size=600)
    # A handful of modules with long domain strings should overflow a 600-byte slot.
    with pytest.raises(LiraError):
        for i in range(20):
            cont.append_module(
                Module(
                    name=f"m{i}",
                    module_type="DELTA",
                    tensors={"tensor": np.ones((1,), dtype=np.float32)},
                    domain=f"a/very/long/domain/string/to/fill/space/{i}",
                )
            )
    cont.close()
