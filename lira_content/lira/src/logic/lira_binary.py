"""A genuine single-file binary implementation of the `.lira` format.

`lira_final_demo.py` simulates the `.lira` container with a directory of
JSON index files and `.npy` tensors.  That is a reasonable way to
prototype the *API*, but it sidesteps three of the six objectives in
`lira_final_spec.md`: memory-mapped zero-copy reads, per-section
integrity hashing that's actually verified, and atomic dual-slot commits
that survive a crash mid-write.

This module implements those parts for real, in one binary file:

* **Superblock** (fixed 4 KiB header): magic, version, architecture and
  quantization codes, and two commit slots (A/B), each with a generation
  pointer and a SHA-512 hash — exactly as specified.
* **Model base**: tensors are written once as raw bytes and read back
  with `mmap`, so loading a tensor never copies the whole file into
  Python memory.
* **Modules** (DELTA/LORA): tensor bytes are appended to the end of the
  file (append-only); each tensor's SHA-256 hash is stored per the
  module-header field in the spec and is re-checked on every read.
* **Categories / skills / memory (RAG) / experiences / history**: kept
  as one JSON metadata blob per commit (the spec explicitly allows JSON
  for these sections), written into whichever slot is *not* currently
  active, hashed with SHA-512, and only then does the superblock flip
  `commit_slot_active` to point at it. If the process dies between
  "write new slot" and "flip pointer", the old slot — still fully
  intact — remains the active, valid state. That's the crash-safety
  property the spec's superblock is designed to provide.

Reuses `Module`, `LiraError`, `IncompatibleShapeError`,
`ModuleAlreadyExistsError` and `IntegrityError` from `lira_final_demo`
so both implementations share the same public vocabulary.
"""

from __future__ import annotations

import copy
import hashlib
import json
import mmap
import os
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

try:
    from .lira_final_demo import (
        LiraError,
        IncompatibleShapeError,
        ModuleAlreadyExistsError,
        IntegrityError,
        Module,
    )
except ImportError:  # pragma: no cover - keeps direct CLI/script execution working
    from lira_final_demo import (
        LiraError,
        IncompatibleShapeError,
        ModuleAlreadyExistsError,
        IntegrityError,
        Module,
    )

# ---------------------------------------------------------------------------
# Constants and superblock layout
# ---------------------------------------------------------------------------

MAGIC = b"LIRA\x00\x00\x00\x00"
FORMAT_VERSION = 1
SUPERBLOCK_SIZE = 4096  # aligned to a page, as required by the spec
PAGE_SIZE = 4096
DEFAULT_METADATA_SLOT_SIZE = 256 * 1024  # 256 KiB; configurable at create()

ARCH_CODES = {"generic": 0, "transformer": 1}
ARCH_NAMES = {v: k for k, v in ARCH_CODES.items()}
QUANT_CODES = {"fp16": 0, "int8": 1, "nf4": 2}
QUANT_NAMES = {v: k for k, v in QUANT_CODES.items()}

# little-endian:
#   magic(8s) version(B) arch_code(B) quantization(B) flags(B)
#   commit_slot_active(B) pad(3x)
#   offset_model_base(Q) offset_slot_a(Q) offset_slot_b(Q) slot_size(Q)
#   slot_a_generation(Q) slot_a_hash(64s)
#   slot_b_generation(Q) slot_b_hash(64s)
_SB_FMT = "<8sBBBBB3xQQQQQ64sQ64s"
_SB_SIZE = struct.calcsize(_SB_FMT)
assert _SB_SIZE <= SUPERBLOCK_SIZE

_EMPTY_HASH = b"\x00" * 64


def _align_up(value: int, alignment: int = PAGE_SIZE) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LiraBinary:
    """A `.lira` container backed by a single binary file.

    Parameters
    ----------
    path: str or Path
        Path to an existing `.lira` file. Use :meth:`create` to make a
        new one; the plain constructor only opens an existing file.
    """

    # -- construction / opening ------------------------------------------------
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self._fh = None
        self._mmap = None
        self._sb: Optional[Dict] = None
        self._metadata: Optional[Dict] = None
        self._active_slot: Optional[str] = None
        self.__base_index_cache: Optional[Tuple[Dict, int]] = None
        if self.path.exists():
            self._open_existing()

    @classmethod
    def create(
        cls,
        path: Union[str, Path],
        base_weights: Dict[str, np.ndarray],
        quantization: str = "fp16",
        arch: str = "generic",
        metadata_slot_size: int = DEFAULT_METADATA_SLOT_SIZE,
    ) -> "LiraBinary":
        """Create a new `.lira` binary file at ``path``. ``path`` must not exist."""
        path = Path(path)
        if path.exists():
            raise FileExistsError(f"{path} already exists")
        if path.parent != Path("") and not path.parent.exists():
            path.parent.mkdir(parents=True)

        # --- build the immutable model-base region ---
        index: Dict[str, Dict] = {}
        payload = bytearray()
        for name, array in base_weights.items():
            arr = np.ascontiguousarray(array)
            raw = arr.tobytes()
            index[name] = {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype),
                "offset": len(payload),
                "length": len(raw),
                "sha256": _sha256(raw),
            }
            payload.extend(raw)
        index_bytes = json.dumps(index).encode("utf-8")
        model_base_region = struct.pack("<Q", len(index_bytes)) + index_bytes + bytes(payload)

        offset_model_base = SUPERBLOCK_SIZE
        offset_slot_a = _align_up(offset_model_base + len(model_base_region))
        offset_slot_b = offset_slot_a + metadata_slot_size

        metadata = {
            "categories": {},
            "modules": {},
            "memory": [],
            "skills": {},
            "experiences": [],
            "history": {"generations": [{"modules": [], "skills": []}], "current": 0},
        }
        meta_bytes = json.dumps(metadata).encode("utf-8")
        if len(meta_bytes) + 8 > metadata_slot_size:
            raise LiraError("Initial metadata does not fit into metadata_slot_size")
        slot_a_hash = hashlib.sha512(meta_bytes).digest()

        with open(path, "wb") as f:
            f.write(b"\x00" * SUPERBLOCK_SIZE)
            f.seek(offset_model_base)
            f.write(model_base_region)
            f.seek(offset_slot_a)
            f.write(struct.pack("<Q", len(meta_bytes)) + meta_bytes)
            # Reserve (and zero-fill via sparse write) both metadata slots
            f.seek(offset_slot_b + metadata_slot_size - 1)
            f.write(b"\x00")
            f.flush()
            os.fsync(f.fileno())

        sb = {
            "magic": MAGIC,
            "version": FORMAT_VERSION,
            "arch_code": ARCH_CODES.get(arch, 0),
            "quantization": QUANT_CODES.get(quantization, 0),
            "flags": 0,
            "commit_slot_active": 0,
            "offset_model_base": offset_model_base,
            "offset_slot_a": offset_slot_a,
            "offset_slot_b": offset_slot_b,
            "slot_size": metadata_slot_size,
            "slot_a_generation": 0,
            "slot_a_hash": slot_a_hash,
            "slot_b_generation": 0,
            "slot_b_hash": _EMPTY_HASH,
        }
        cls._write_superblock(path, sb)
        return cls(path)

    # -- superblock (de)serialization -----------------------------------------
    @staticmethod
    def _pack_superblock(sb: Dict) -> bytes:
        packed = struct.pack(
            _SB_FMT,
            sb["magic"], sb["version"], sb["arch_code"], sb["quantization"],
            sb["flags"], sb["commit_slot_active"],
            sb["offset_model_base"], sb["offset_slot_a"], sb["offset_slot_b"],
            sb["slot_size"],
            sb["slot_a_generation"], sb["slot_a_hash"],
            sb["slot_b_generation"], sb["slot_b_hash"],
        )
        return packed + b"\x00" * (SUPERBLOCK_SIZE - len(packed))

    @staticmethod
    def _unpack_superblock(data: bytes) -> Dict:
        fields = struct.unpack(_SB_FMT, data[:_SB_SIZE])
        (magic, version, arch_code, quantization, flags, commit_slot_active,
         offset_model_base, offset_slot_a, offset_slot_b, slot_size,
         slot_a_generation, slot_a_hash, slot_b_generation, slot_b_hash) = fields
        if magic != MAGIC:
            raise LiraError(f"'{data[:8]!r}' is not a valid .lira file (bad magic bytes)")
        return {
            "magic": magic, "version": version, "arch_code": arch_code,
            "quantization": quantization, "flags": flags,
            "commit_slot_active": commit_slot_active,
            "offset_model_base": offset_model_base,
            "offset_slot_a": offset_slot_a, "offset_slot_b": offset_slot_b,
            "slot_size": slot_size,
            "slot_a_generation": slot_a_generation, "slot_a_hash": slot_a_hash,
            "slot_b_generation": slot_b_generation, "slot_b_hash": slot_b_hash,
        }

    @classmethod
    def _write_superblock(cls, path: Path, sb: Dict) -> None:
        data = cls._pack_superblock(sb)
        with open(path, "r+b") as f:
            f.seek(0)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    def _open_existing(self) -> None:
        with open(self.path, "rb") as f:
            sb_bytes = f.read(SUPERBLOCK_SIZE)
        self._sb = self._unpack_superblock(sb_bytes)
        self._metadata, self._active_slot = self._read_active_metadata()

    # -- metadata slot read / commit -------------------------------------------
    def _read_slot(self, slot: str) -> Optional[Dict]:
        offset = self._sb[f"offset_slot_{slot}"]
        expected_hash = self._sb[f"slot_{slot}_hash"]
        with open(self.path, "rb") as f:
            f.seek(offset)
            (length,) = struct.unpack("<Q", f.read(8))
            if length == 0:
                return None
            data = f.read(length)
        if len(data) != length:
            return None
        if expected_hash != _EMPTY_HASH and hashlib.sha512(data).digest() != expected_hash:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _read_active_metadata(self) -> Tuple[Dict, str]:
        active = "a" if self._sb["commit_slot_active"] == 0 else "b"
        inactive = "b" if active == "a" else "a"
        meta = self._read_slot(active)
        if meta is not None:
            return meta, active
        # The spec's crash-safety guarantee: if the active slot is corrupt,
        # fall back to the other slot rather than failing outright.
        meta = self._read_slot(inactive)
        if meta is not None:
            return meta, inactive
        raise IntegrityError(
            f"Both commit slots of {self.path} are corrupted or unreadable"
        )

    def _commit(self, new_metadata: Dict) -> None:
        meta_bytes = json.dumps(new_metadata).encode("utf-8")
        if len(meta_bytes) + 8 > self._sb["slot_size"]:
            raise LiraError(
                f"Metadata ({len(meta_bytes)} bytes) no longer fits in the "
                f"reserved slot size ({self._sb['slot_size']} bytes); "
                "consolidate the container or recreate it with a larger "
                "metadata_slot_size."
            )
        current_active = "a" if self._sb["commit_slot_active"] == 0 else "b"
        target = "b" if current_active == "a" else "a"
        offset = self._sb[f"offset_slot_{target}"]
        new_hash = hashlib.sha512(meta_bytes).digest()
        generation = new_metadata["history"]["current"]

        with open(self.path, "r+b") as f:
            f.seek(offset)
            f.write(struct.pack("<Q", len(meta_bytes)) + meta_bytes)
            f.flush()
            os.fsync(f.fileno())

        # Only after the new slot is safely on disk do we flip the pointer.
        self._sb[f"slot_{target}_generation"] = generation
        self._sb[f"slot_{target}_hash"] = new_hash
        self._sb["commit_slot_active"] = 0 if target == "a" else 1
        self._write_superblock(self.path, self._sb)

        self._metadata = new_metadata
        self._active_slot = target
        self._invalidate_mmap()

    def _append_raw(self, data: bytes) -> Tuple[int, int]:
        """Append bytes to the end of the file. Returns (offset, length)."""
        with open(self.path, "r+b") as f:
            f.seek(0, os.SEEK_END)
            offset = f.tell()
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        self._invalidate_mmap()
        return offset, len(data)

    def _append_raw_batch(self, chunks: List[bytes]) -> List[Tuple[int, int]]:
        """Append several byte chunks with a single fsync. Returns (offset, length) per chunk, in order."""
        results: List[Tuple[int, int]] = []
        with open(self.path, "r+b") as f:
            f.seek(0, os.SEEK_END)
            for chunk in chunks:
                offset = f.tell()
                f.write(chunk)
                results.append((offset, len(chunk)))
            f.flush()
            os.fsync(f.fileno())
        self._invalidate_mmap()
        return results

    # -- mmap-backed reads -------------------------------------------------
    def _ensure_mmap(self) -> mmap.mmap:
        if self._mmap is None:
            self._fh = open(self.path, "rb")
            self._mmap = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        return self._mmap

    def _invalidate_mmap(self) -> None:
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def _base_index(self) -> Tuple[Dict, int]:
        if self.__base_index_cache is None:
            mm = self._ensure_mmap()
            off = self._sb["offset_model_base"]
            (index_len,) = struct.unpack("<Q", mm[off:off + 8])
            index = json.loads(bytes(mm[off + 8: off + 8 + index_len]).decode("utf-8"))
            self.__base_index_cache = (index, off + 8 + index_len)
        return self.__base_index_cache

    def _read_ref(self, ref: Dict, label: str) -> bytes:
        mm = self._ensure_mmap()
        start, end = ref["offset"], ref["offset"] + ref["length"]
        raw = bytes(mm[start:end])
        if _sha256(raw) != ref["sha256"]:
            raise IntegrityError(f"Hash mismatch for {label}: data may be corrupted or tampered with")
        return raw

    def _ref_to_array(self, ref: Dict, label: str) -> np.ndarray:
        raw = self._read_ref(ref, label)
        return np.frombuffer(raw, dtype=np.dtype(ref["dtype"])).reshape(ref["shape"])

    def _load_base_tensor(self, name: str) -> np.ndarray:
        index, data_start = self._base_index()
        if name not in index:
            raise KeyError(f"Tensor {name} not in base model")
        info = index[name]
        ref = {**info, "offset": data_start + info["offset"]}
        return self._ref_to_array(ref, f"base tensor '{name}'")

    # -- modules -------------------------------------------------------------
    def append_module(self, module: Module) -> None:
        """Append a DELTA or LoRA module, validating shapes and hashing tensors."""
        if module.name in self._metadata["modules"]:
            raise ModuleAlreadyExistsError(f"Module {module.name} already exists")
        base_index, _ = self._base_index()
        tensors_meta: Dict[str, Dict] = {}
        for tname, value in module.tensors.items():
            base_info = base_index.get(tname)
            if module.module_type == "DELTA":
                arr = np.ascontiguousarray(value)
                if base_info is not None and list(arr.shape) != base_info["shape"]:
                    raise IncompatibleShapeError(
                        f"Shape mismatch for tensor {tname} in module {module.name}: "
                        f"got {arr.shape}, expected {tuple(base_info['shape'])}"
                    )
                raw = arr.tobytes()
                offset, length = self._append_raw(raw)
                tensors_meta[tname] = {
                    "shape": list(arr.shape), "dtype": str(arr.dtype),
                    "offset": offset, "length": length, "sha256": _sha256(raw),
                }
            elif module.module_type == "LORA":
                try:
                    A, B = value
                except Exception:
                    raise IncompatibleShapeError(
                        f"LoRA tensor for {tname} in module {module.name} must be a tuple (A, B)"
                    )
                A = np.ascontiguousarray(A)
                B = np.ascontiguousarray(B)
                if A.ndim != 2 or B.ndim != 2:
                    raise IncompatibleShapeError(
                        f"LoRA tensors for {tname} in module {module.name} must be 2D matrices"
                    )
                if base_info is not None:
                    m, n = base_info["shape"]
                    mA, r1 = A.shape
                    r2, nB = B.shape
                    if mA != m or nB != n or r1 != r2:
                        raise IncompatibleShapeError(
                            f"LoRA shape mismatch for tensor {tname} in module {module.name}: "
                            f"base shape {(m, n)}, A shape {A.shape}, B shape {B.shape}"
                        )
                raw_A, raw_B = A.tobytes(), B.tobytes()
                off_A, len_A = self._append_raw(raw_A)
                off_B, len_B = self._append_raw(raw_B)
                tensors_meta[tname] = {
                    "A": {"shape": list(A.shape), "dtype": str(A.dtype), "offset": off_A, "length": len_A, "sha256": _sha256(raw_A)},
                    "B": {"shape": list(B.shape), "dtype": str(B.dtype), "offset": off_B, "length": len_B, "sha256": _sha256(raw_B)},
                }
            else:
                raise ValueError(f"Unsupported module type: {module.module_type}")

        new_metadata = copy.deepcopy(self._metadata)
        new_metadata["modules"][module.name] = {
            "type": module.module_type,
            "domain": module.domain,
            "metadata": module.metadata,
            "tensors": tensors_meta,
        }
        if module.domain:
            cat = new_metadata["categories"].get(module.domain, {"modules": [], "skills": []})
            cat["modules"].append(module.name)
            new_metadata["categories"][module.domain] = cat
        hist = new_metadata["history"]
        cur = hist["current"]
        active_modules = list(hist["generations"][cur]["modules"]) if cur >= 0 else []
        active_skills = list(hist["generations"][cur].get("skills", [])) if cur >= 0 else []
        active_modules.append(module.name)
        hist["generations"].append({"modules": active_modules, "skills": active_skills})
        hist["current"] = len(hist["generations"]) - 1
        self._commit(new_metadata)

    def append_modules(self, modules: List[Module]) -> None:
        """Append several modules in a single on-disk transaction.

        Equivalent to calling :meth:`append_module` once per item, except
        that every tensor byte-write is flushed with **one** `fsync` at
        the end instead of one per module, and the resulting metadata is
        committed with a single slot write + superblock flip.

        Each call to :meth:`append_module` does 1–2 `fsync` calls for the
        tensor data plus one for the metadata commit, which is exactly
        what makes each individual append durable — but `fsync` is slow
        (typically several milliseconds), so appending many modules one
        at a time is dominated by that cost. Batching trades fine-grained
        crash-safety (a crash mid-batch loses the *whole* batch, not just
        the last module) for throughput, the same trade-off
        ``LiraContainer.batch()`` makes in the JSON-based prototype.
        """
        if not modules:
            return
        base_index, _ = self._base_index()
        new_metadata = copy.deepcopy(self._metadata)
        chunks: List[bytes] = []
        chunk_specs: List[Tuple[str, str, str]] = []  # (module_name, tensor_name, "DELTA"|"A"|"B")
        module_tensor_meta: Dict[str, Dict[str, Dict]] = {}

        for module in modules:
            if module.name in new_metadata["modules"] or module.name in module_tensor_meta:
                raise ModuleAlreadyExistsError(f"Module {module.name} already exists")
            tensors_meta: Dict[str, Dict] = {}
            for tname, value in module.tensors.items():
                base_info = base_index.get(tname)
                if module.module_type == "DELTA":
                    arr = np.ascontiguousarray(value)
                    if base_info is not None and list(arr.shape) != base_info["shape"]:
                        raise IncompatibleShapeError(
                            f"Shape mismatch for tensor {tname} in module {module.name}: "
                            f"got {arr.shape}, expected {tuple(base_info['shape'])}"
                        )
                    raw = arr.tobytes()
                    chunks.append(raw)
                    chunk_specs.append((module.name, tname, "DELTA"))
                    tensors_meta[tname] = {"shape": list(arr.shape), "dtype": str(arr.dtype), "sha256": _sha256(raw)}
                elif module.module_type == "LORA":
                    try:
                        A, B = value
                    except Exception:
                        raise IncompatibleShapeError(
                            f"LoRA tensor for {tname} in module {module.name} must be a tuple (A, B)"
                        )
                    A = np.ascontiguousarray(A)
                    B = np.ascontiguousarray(B)
                    if A.ndim != 2 or B.ndim != 2:
                        raise IncompatibleShapeError(
                            f"LoRA tensors for {tname} in module {module.name} must be 2D matrices"
                        )
                    if base_info is not None:
                        m, n = base_info["shape"]
                        mA, r1 = A.shape
                        r2, nB = B.shape
                        if mA != m or nB != n or r1 != r2:
                            raise IncompatibleShapeError(
                                f"LoRA shape mismatch for tensor {tname} in module {module.name}: "
                                f"base shape {(m, n)}, A shape {A.shape}, B shape {B.shape}"
                            )
                    raw_A, raw_B = A.tobytes(), B.tobytes()
                    chunks.append(raw_A)
                    chunk_specs.append((module.name, tname, "A"))
                    chunks.append(raw_B)
                    chunk_specs.append((module.name, tname, "B"))
                    tensors_meta[tname] = {
                        "A": {"shape": list(A.shape), "dtype": str(A.dtype), "sha256": _sha256(raw_A)},
                        "B": {"shape": list(B.shape), "dtype": str(B.dtype), "sha256": _sha256(raw_B)},
                    }
                else:
                    raise ValueError(f"Unsupported module type: {module.module_type}")
            module_tensor_meta[module.name] = tensors_meta

        offsets = self._append_raw_batch(chunks)
        for (mod_name, tname, kind), (offset, length) in zip(chunk_specs, offsets):
            entry = module_tensor_meta[mod_name][tname]
            target = entry if kind == "DELTA" else entry[kind]
            target["offset"] = offset
            target["length"] = length

        hist = new_metadata["history"]
        for module in modules:
            new_metadata["modules"][module.name] = {
                "type": module.module_type,
                "domain": module.domain,
                "metadata": module.metadata,
                "tensors": module_tensor_meta[module.name],
            }
            if module.domain:
                cat = new_metadata["categories"].get(module.domain, {"modules": [], "skills": []})
                cat["modules"].append(module.name)
                new_metadata["categories"][module.domain] = cat
            cur = hist["current"]
            active_modules = list(hist["generations"][cur]["modules"]) if cur >= 0 else []
            active_skills = list(hist["generations"][cur].get("skills", [])) if cur >= 0 else []
            active_modules.append(module.name)
            hist["generations"].append({"modules": active_modules, "skills": active_skills})
            hist["current"] = len(hist["generations"]) - 1

        self._commit(new_metadata)

    def get_weight(self, name: str) -> np.ndarray:
        """Compute the effective tensor for ``name`` in the current generation."""
        weight = self._load_base_tensor(name).copy()
        for mod_name in self.current_modules():
            entry = self._metadata["modules"][mod_name]
            if name not in entry["tensors"]:
                continue
            ref = entry["tensors"][name]
            if entry["type"] == "DELTA":
                delta = self._ref_to_array(ref, f"module '{mod_name}' tensor '{name}'")
                weight = weight + delta
            elif entry["type"] == "LORA":
                A = self._ref_to_array(ref["A"], f"module '{mod_name}' tensor '{name}' (A)")
                B = self._ref_to_array(ref["B"], f"module '{mod_name}' tensor '{name}' (B)")
                weight = weight + A @ B
            else:
                raise ValueError(f"Unsupported module type: {entry['type']}")
        return weight

    # -- history / rollback --------------------------------------------------
    def current_modules(self) -> List[str]:
        hist = self._metadata["history"]
        cur = hist["current"]
        return list(hist["generations"][cur]["modules"]) if cur >= 0 else []

    def current_skills(self) -> List[str]:
        hist = self._metadata["history"]
        cur = hist["current"]
        return list(hist["generations"][cur].get("skills", [])) if cur >= 0 else []

    def rollback(self, generation: int) -> None:
        hist = self._metadata["history"]
        if generation < 0 or generation >= len(hist["generations"]):
            raise IndexError("Generation out of range")
        new_metadata = copy.deepcopy(self._metadata)
        new_metadata["history"]["current"] = generation
        self._commit(new_metadata)

    # -- categories / experiences --------------------------------------------
    def list_categories(self) -> List[str]:
        return list(self._metadata["categories"].keys())

    def modules_in_category(self, category: str) -> List[str]:
        return self._metadata["categories"].get(category, {}).get("modules", [])

    def add_experience(self, record: Dict) -> None:
        """Log an experience. Per spec, this does not create a new generation."""
        new_metadata = copy.deepcopy(self._metadata)
        new_metadata["experiences"].append(record)
        self._commit(new_metadata)

    def list_experiences(self) -> List[Dict]:
        return list(self._metadata["experiences"])

    # -- memory (RAG) ---------------------------------------------------------
    def add_memory(self, text: str, vector: Optional[np.ndarray] = None, memory_id: Optional[str] = None) -> str:
        """Add a retrieval memory entry. Does not create a new generation."""
        new_metadata = copy.deepcopy(self._metadata)
        mem_id = memory_id or f"mem_{len(new_metadata['memory'])}"
        entry: Dict = {"id": mem_id, "text": text}
        if vector is not None:
            arr = np.ascontiguousarray(vector, dtype=np.float32)
            raw = arr.tobytes()
            offset, length = self._append_raw(raw)
            entry["vector"] = {"shape": list(arr.shape), "dtype": str(arr.dtype), "offset": offset, "length": length, "sha256": _sha256(raw)}
        new_metadata["memory"].append(entry)
        self._commit(new_metadata)
        return mem_id

    def list_memory(self) -> List[Dict]:
        return list(self._metadata["memory"])

    def get_memory_vector(self, memory_id: str) -> np.ndarray:
        for entry in self._metadata["memory"]:
            if entry["id"] == memory_id and "vector" in entry:
                return self._ref_to_array(entry["vector"], f"memory '{memory_id}' vector")
        raise KeyError(f"No vector stored for memory id {memory_id}")

    # -- skills ---------------------------------------------------------------
    def register_skill(self, skill_id: str, definition: Dict, domain: Optional[str] = None) -> None:
        """Register a skill in the catalog without activating it in a generation."""
        if skill_id in self._metadata["skills"]:
            raise ModuleAlreadyExistsError(f"Skill {skill_id} already registered")
        new_metadata = copy.deepcopy(self._metadata)
        new_metadata["skills"][skill_id] = {"definition": definition, "domain": domain}
        if domain:
            cat = new_metadata["categories"].get(domain, {"modules": [], "skills": []})
            cat["skills"].append(skill_id)
            new_metadata["categories"][domain] = cat
        self._commit(new_metadata)

    def activate_skill(self, skill_id: str) -> None:
        """Activate a registered skill in a new generation."""
        if skill_id not in self._metadata["skills"]:
            raise KeyError(f"Skill {skill_id} is not registered")
        new_metadata = copy.deepcopy(self._metadata)
        hist = new_metadata["history"]
        cur = hist["current"]
        active_modules = list(hist["generations"][cur]["modules"]) if cur >= 0 else []
        active_skills = list(hist["generations"][cur].get("skills", [])) if cur >= 0 else []
        if skill_id not in active_skills:
            active_skills.append(skill_id)
        hist["generations"].append({"modules": active_modules, "skills": active_skills})
        hist["current"] = len(hist["generations"]) - 1
        self._commit(new_metadata)

    # -- diagnostics ------------------------------------------------------------
    def verify_integrity(self, check_all_tensors: bool = True) -> Dict:
        """Audit both commit slots and (optionally) every reachable tensor.

        Never raises for a stale *inactive* slot — that's expected once
        it's superseded. Only the read path for the active slot can raise
        ``IntegrityError`` (via the constructor / reload).
        """
        report = {
            "path": str(self.path),
            "slot_a_readable": self._read_slot("a") is not None,
            "slot_b_readable": self._read_slot("b") is not None,
            "active_slot": self._active_slot,
            "tensors_checked": 0,
            "tensors_ok": 0,
            "errors": [],
        }
        if check_all_tensors:
            base_index, data_start = self._base_index()
            for name, info in base_index.items():
                report["tensors_checked"] += 1
                try:
                    self._read_ref({**info, "offset": data_start + info["offset"]}, f"base tensor '{name}'")
                    report["tensors_ok"] += 1
                except IntegrityError as e:
                    report["errors"].append(str(e))
            for mod_name, entry in self._metadata["modules"].items():
                for tname, ref in entry["tensors"].items():
                    refs = [ref] if entry["type"] == "DELTA" else [ref["A"], ref["B"]]
                    for r in refs:
                        report["tensors_checked"] += 1
                        try:
                            self._read_ref(r, f"module '{mod_name}' tensor '{tname}'")
                            report["tensors_ok"] += 1
                        except IntegrityError as e:
                            report["errors"].append(str(e))
        return report

    def storage_report(self) -> Dict:
        """Report active data versus bytes no longer referenced by metadata."""
        file_size = self.path.stat().st_size
        meta_bytes = len(json.dumps(self._metadata).encode("utf-8"))
        base_index, data_start = self._base_index()
        tensor_bytes = 0
        active_extra_tensor_bytes = 0
        payload_bytes = 0
        base_region_length = self._sb["offset_slot_a"] - self._sb["offset_model_base"]
        spans = [
            (0, SUPERBLOCK_SIZE),
            (self._sb["offset_model_base"], base_region_length),
            (self._sb["offset_slot_a"], self._sb["slot_size"]),
            (self._sb["offset_slot_b"], self._sb["slot_size"]),
        ]

        for info in base_index.values():
            off = data_start + info["offset"]
            length = info["length"]
            tensor_bytes += length
            spans.append((off, length))

        for entry in self._metadata["modules"].values():
            meta = entry.get("metadata", {})
            if "knowledge_payload_offset" in meta and "knowledge_payload_length" in meta:
                length = meta["knowledge_payload_length"]
                payload_bytes += length
                spans.append((meta["knowledge_payload_offset"], length))
            for ref in entry.get("tensors", {}).values():
                refs = [ref] if entry["type"] == "DELTA" else [ref["A"], ref["B"]]
                for r in refs:
                    tensor_bytes += r["length"]
                    active_extra_tensor_bytes += r["length"]
                    spans.append((r["offset"], r["length"]))

        for mem in self._metadata.get("memory", []):
            if "vector" in mem:
                ref = mem["vector"]
                tensor_bytes += ref["length"]
                active_extra_tensor_bytes += ref["length"]
                spans.append((ref["offset"], ref["length"]))

        active_ranges = sorted((start, start + length) for start, length in spans if length > 0)
        merged = []
        for start, end in active_ranges:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        referenced_bytes = sum(end - start for start, end in merged)
        metadata_reserved = SUPERBLOCK_SIZE + (2 * self._sb["slot_size"])
        active_bytes = active_extra_tensor_bytes + payload_bytes + metadata_reserved + base_region_length
        return {
            "file_size": file_size,
            "bytes_ativos": active_bytes,
            "bytes_orfaos": max(file_size - referenced_bytes, 0),
            "bytes_metadados": metadata_reserved,
            "bytes_estrutura_base": base_region_length,
            "bytes_metadata_json_ativo": meta_bytes,
            "bytes_tensores": tensor_bytes,
            "bytes_payload": payload_bytes,
        }

    def compact(self) -> Dict:
        """Rewrite the container into a temporary file and atomically replace it.

        Only bytes reachable from active metadata are copied. Stale payloads and
        tensors left by previous recompilations are intentionally omitted.
        """
        before = self.storage_report()
        base_index, _ = self._base_index()
        base_weights = {name: self._load_base_tensor(name).copy() for name in base_index}
        new_metadata = copy.deepcopy(self._metadata)
        chunks: List[bytes] = []
        targets: List[Dict] = []

        def collect_ref(ref: Dict, label: str) -> None:
            raw = self._read_ref(ref, label)
            chunks.append(raw)
            targets.append(ref)

        for mod_name, entry in new_metadata["modules"].items():
            original_entry = self._metadata["modules"][mod_name]
            meta = entry.get("metadata", {})
            original_meta = original_entry.get("metadata", {})
            if "knowledge_payload_offset" in original_meta and "knowledge_payload_length" in original_meta:
                ref = {
                    "offset": original_meta["knowledge_payload_offset"],
                    "length": original_meta["knowledge_payload_length"],
                    "sha256": original_meta["knowledge_payload_sha256"],
                }
                raw = self._read_ref(ref, f"{mod_name}/knowledge_payload")
                chunks.append(raw)
                targets.append({
                    "_knowledge_meta": meta,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                })
            for tname, ref in entry.get("tensors", {}).items():
                original_ref = original_entry["tensors"][tname]
                if entry["type"] == "DELTA":
                    collect_ref(original_ref, f"{mod_name}/{tname}")
                    targets[-1] = ref
                else:
                    collect_ref(original_ref["A"], f"{mod_name}/{tname}/A")
                    targets[-1] = ref["A"]
                    collect_ref(original_ref["B"], f"{mod_name}/{tname}/B")
                    targets[-1] = ref["B"]

        for idx, mem in enumerate(new_metadata.get("memory", [])):
            if "vector" in mem:
                collect_ref(self._metadata["memory"][idx]["vector"], f"memory/{mem.get('id', idx)}")
                targets[-1] = mem["vector"]

        tmp_path = self.path.with_name(self.path.name + ".compact.tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        compacted = LiraBinary.create(
            tmp_path,
            base_weights,
            quantization=QUANT_NAMES.get(self._sb["quantization"], "fp16"),
            arch=ARCH_NAMES.get(self._sb["arch_code"], "generic"),
            metadata_slot_size=self._sb["slot_size"],
        )
        try:
            offsets = compacted._append_raw_batch(chunks)
            for target, (offset, length) in zip(targets, offsets):
                if "_knowledge_meta" in target:
                    meta = target["_knowledge_meta"]
                    meta["knowledge_payload_offset"] = offset
                    meta["knowledge_payload_length"] = length
                    meta["knowledge_payload_sha256"] = target["sha256"]
                else:
                    target["offset"] = offset
                    target["length"] = length
            compacted._commit(new_metadata)
        finally:
            compacted.close()

        self.close()
        os.replace(tmp_path, self.path)
        self._open_existing()
        after = self.storage_report()
        return {"before": before, "after": after}

    def info(self) -> str:
        base_index, _ = self._base_index()
        hist = self._metadata["history"]
        lines = [
            f"Format version: {self._sb['version']}",
            f"Architecture: {ARCH_NAMES.get(self._sb['arch_code'], self._sb['arch_code'])}",
            f"Quantization: {QUANT_NAMES.get(self._sb['quantization'], self._sb['quantization'])}",
            f"Active commit slot: {'A' if self._sb['commit_slot_active'] == 0 else 'B'}",
            f"File size: {self.path.stat().st_size} bytes",
            f"Base tensors: {len(base_index)}",
            f"Total modules: {len(self._metadata['modules'])}",
            f"Categories: {len(self._metadata['categories'])}",
            f"Registered skills: {len(self._metadata['skills'])}",
            f"Memory entries: {len(self._metadata['memory'])}",
            f"Generations: {len(hist['generations'])}",
            f"Current generation: {hist['current']}",
        ]
        for idx, gen in enumerate(hist["generations"]):
            marker = "*" if idx == hist["current"] else " "
            lines.append(f"{marker} Gen {idx}: modules={gen['modules']} skills={gen.get('skills', [])}")
        return "\n".join(lines)

    # -- lifecycle --------------------------------------------------------------
    def close(self) -> None:
        self._invalidate_mmap()

    def __enter__(self) -> "LiraBinary":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def _demo() -> None:
    """Demonstrate LiraBinary end to end, mirroring lira_final_demo._demo()."""
    import tempfile

    base = {
        "layer.weight": np.ones((4, 4), dtype=np.float32),
        "layer.bias": np.zeros((4,), dtype=np.float32),
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "model.lira"
        cont = LiraBinary.create(path, base, quantization="fp16")
        print("After creation:\n", cont.info())

        delta = np.full((4, 4), 0.1, dtype=np.float32)
        m1 = Module(name="mod_increment", module_type="DELTA", tensors={"layer.weight": delta}, domain="programacao/python")
        cont.append_module(m1)
        print("\nAfter adding delta module:\n", cont.info())

        A = np.arange(4, dtype=np.float32).reshape(4, 1)
        B = (np.arange(4, dtype=np.float32) * 0.01).reshape(1, 4)
        m2 = Module(name="mod_rank1", module_type="LORA", tensors={"layer.weight": (A, B)}, domain="programacao/numerico")
        cont.append_module(m2)
        print("\nAfter adding LoRA module:\n", cont.info())

        cont.add_experience({"prompt": "Hello", "response": "World", "score": 0.9})
        cont.add_memory("The sky is blue", vector=np.random.rand(8).astype(np.float32))
        cont.register_skill("skill_greet", {"kind": "prompt_template", "text": "Say hello"}, domain="social/greeting")
        cont.activate_skill("skill_greet")

        w = cont.get_weight("layer.weight")
        print("\nEffective weight:\n", w)

        report = cont.verify_integrity()
        print("\nIntegrity report:", report)

        cont.rollback(0)
        print("\nAfter rollback to generation 0:\n", cont.info())
        print("Weight after rollback:\n", cont.get_weight("layer.weight"))
        cont.close()


if __name__ == "__main__":
    _demo()
