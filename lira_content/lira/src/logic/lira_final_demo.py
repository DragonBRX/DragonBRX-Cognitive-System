"""Demonstration of a simplified `.lira` container.

This module provides classes to create and manage a `.lira` container
according to the specification in `lira_final_spec.md`.  It is not
a full binary implementation; instead it uses a directory with
JSON files and NumPy `.npy` arrays to emulate the behavior.  The
goal is to illustrate how base weights, modules, categories,
experiences and generations can be managed incrementally without
rewriting the base weights.

Key concepts:

* **Base weights**: stored in `base_weights/` directory as `.npy` files.
  Metadata about each tensor is recorded in `base.json`.
* **Modules**: represent deltas or LoRA adapters.  Each module has
  a name, a type, tensors (arrays or pairs for LoRA) and metadata
  including domain/category.  Data for each module is stored in
  `modules/` and indexed in `modules.json`.
* **Categories**: a mapping from semantic keys (e.g.
  "programacao/python") to lists of module names and skills.
  Stored in `categories.json`.
* **Experiences**: logs of interactions; stored in `experiences.json`.
* **History**: records generations and the active modules for each
  generation; stored in `history.json`.

This prototype does not implement quantization or binary serialization
directly.  Instead, it serves as a high‑level demonstration of the
ideas outlined in the specification.

Dependencies: NumPy for array handling and the Python standard
library for file and JSON operations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import contextlib
import hashlib
import numpy as np

# Custom exceptions for clearer error reporting
class LiraError(Exception):
    """Base class for Lira-related exceptions."""


class IncompatibleShapeError(LiraError):
    """Raised when a module tensor shape is not compatible with the base weight."""


class ModuleAlreadyExistsError(LiraError):
    """Raised when attempting to add a module that already exists in the container."""


class IntegrityError(LiraError):
    """Raised when a tensor file's SHA-512 hash does not match the recorded hash."""


def _compute_sha512(file_path: Path) -> str:
    """Compute the SHA‑512 hash of a file.

    Parameters
    ----------
    file_path: pathlib.Path
        Path to the file whose hash should be computed.

    Returns
    -------
    str
        Hexadecimal string representation of the SHA‑512 digest.
    """
    h = hashlib.sha512()
    # Read in chunks to avoid large memory usage
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class Module:
    """Represents an update module in the `.lira` container.

    A module can be of type ``DELTA`` (additive updates) or ``LORA``
    (low‑rank adapters).  Additional types (e.g. ``EMBEDDING``) could
    be added in the future.  Each module stores its tensor data and
    metadata such as the domain/category.

    Parameters
    ----------
    name: str
        Unique name of the module.
    module_type: str
        ``DELTA`` or ``LORA``.
    tensors: Dict[str, Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]
        Mapping from tensor names to either NumPy arrays (for DELTA) or
        tuples of arrays (A, B) for LoRA.  The arrays must be
        compatible with the base weights.
    domain: Optional[str]
        Semantic domain for this module (e.g. "programacao/python").
    metadata: Optional[Dict[str, str]]
        Additional key/value metadata.
    """

    def __init__(
        self,
        name: str,
        module_type: str,
        tensors: Dict[str, Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]],
        domain: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        self.name = name
        self.module_type = module_type.upper()
        self.tensors = tensors
        self.domain = domain
        self.metadata = metadata or {}

    def apply(self, base: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Compute the updated tensors given a mapping of base weights.

        Only returns tensors that this module modifies.  If a tensor
        name is not present in ``base``, it is ignored.
        """
        updates: Dict[str, np.ndarray] = {}
        if self.module_type == "DELTA":
            for name, delta in self.tensors.items():
                if name not in base:
                    # If the tensor does not exist in the base, it cannot be updated.
                    continue
                base_weight = base[name]
                # Validate shape compatibility
                if not isinstance(delta, np.ndarray):
                    raise IncompatibleShapeError(
                        f"Delta for tensor {name} in module {self.name} is not a NumPy array"
                    )
                if delta.shape != base_weight.shape:
                    raise IncompatibleShapeError(
                        f"Shape mismatch for tensor {name} in module {self.name}: "
                        f"delta shape {delta.shape} vs base shape {base_weight.shape}"
                    )
                updates[name] = base_weight + delta  # type: ignore[operator]
        elif self.module_type == "LORA":
            for name, pair in self.tensors.items():
                if name not in base:
                    # Skip unknown tensors
                    continue
                base_weight = base[name]
                # Validate LoRA pair structure
                try:
                    A, B = pair  # type: ignore[assignment]
                except Exception:
                    raise IncompatibleShapeError(
                        f"LoRA tensor for {name} in module {self.name} must be a tuple (A, B)"
                    )
                if not (isinstance(A, np.ndarray) and isinstance(B, np.ndarray)):
                    raise IncompatibleShapeError(
                        f"LoRA tensors for {name} in module {self.name} must be NumPy arrays"
                    )
                # Shapes: base_weight is (m, n), A is (m, r), B is (r, n)
                if A.ndim != 2 or B.ndim != 2:
                    raise IncompatibleShapeError(
                        f"LoRA tensors for {name} in module {self.name} must be 2D matrices"
                    )
                m, n = base_weight.shape
                mA, r1 = A.shape
                r2, nB = B.shape
                if mA != m or nB != n or r1 != r2:
                    raise IncompatibleShapeError(
                        f"LoRA shape mismatch for tensor {name} in module {self.name}: "
                        f"base shape {base_weight.shape}, A shape {A.shape}, B shape {B.shape}"
                    )
                update = A @ B
                updates[name] = base_weight + update  # type: ignore[operator]
        else:
            raise ValueError(f"Unsupported module type: {self.module_type}")
        return updates

    def to_index(self) -> Dict:
        """Serialize metadata for this module for the index file.

        The actual tensor data lives on disk; here we record paths,
        shapes and dtypes so that tensors can be loaded lazily.
        """
        entry = {
            "name": self.name,
            "type": self.module_type,
            "tensors": {},
            "domain": self.domain,
            "metadata": self.metadata,
        }
        for tensor_name, value in self.tensors.items():
            if self.module_type == "DELTA":
                file_name = f"{self.name}_{tensor_name}.npy"
                entry["tensors"][tensor_name] = {
                    "path": file_name,
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                }
            elif self.module_type == "LORA":
                A, B = value  # type: ignore[assignment]
                file_A = f"{self.name}_{tensor_name}_A.npy"
                file_B = f"{self.name}_{tensor_name}_B.npy"
                entry["tensors"][tensor_name] = {
                    "path_A": file_A,
                    "shape_A": list(A.shape),
                    "path_B": file_B,
                    "shape_B": list(B.shape),
                    "dtype": str(A.dtype),
                }
        return entry


class LiraContainer:
    """Manage a `.lira` container stored in a directory.

    A LiraContainer organizes the base weights, modules, categories,
    experiences and generations.  This implementation uses JSON for
    metadata and `.npy` files for tensors.  It simulates the behavior
    of a binary `.lira` container in a readable form.
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.base_dir = self.path / "base_weights"
        self.modules_dir = self.path / "modules"
        self.metadata_path = self.path / "base.json"
        self.modules_index_path = self.path / "modules.json"
        self.categories_path = self.path / "categories.json"
        self.experiences_path = self.path / "experiences.json"
        self.history_path = self.path / "history.json"
        # loaded state
        self._base_metadata: Dict[str, Dict] = {}
        self._loaded_base: Optional[Dict[str, np.ndarray]] = None
        self._modules: Dict[str, Module] = {}
        self._categories: Dict[str, Dict[str, List[str]]] = {}
        self._experiences: List[Dict] = []
        self._generations: List[Dict[str, List[str]]] = []
        self._current_gen: int = -1
        self._modules_index: Dict = {"modules": {}, "count": 0}
        # Batch-write support: while _batch_depth > 0, mutating operations
        # update in-memory state and mark the relevant file "dirty" instead
        # of rewriting it to disk immediately. See ``batch()``.
        self._batch_depth: int = 0
        self._dirty = {"modules": False, "categories": False, "history": False, "experiences": False}
        if self.path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Creation and loading
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        path: Union[str, Path],
        base_weights: Dict[str, np.ndarray],
        quantization: Optional[str] = None,
    ) -> "LiraContainer":
        """Create a new `.lira` container at ``path`` with given base weights.

        Parameters
        ----------
        path: str or Path
            Directory where the container will be stored.  Must not exist.
        base_weights: Dict[str, np.ndarray]
            Mapping of tensor names to arrays representing the initial model.
        quantization: Optional[str]
            String indicating the quantization applied to the base
            (e.g. "fp16", "int8", "nf4").  Stored for informational
            purposes; this prototype does not actually quantize.

        Returns
        -------
        LiraContainer
            The newly created container instance.
        """
        inst = cls(path)
        if inst.path.exists():
            raise FileExistsError(f"Directory {path} already exists")
        # Create directory structure
        inst.path.mkdir(parents=True)
        inst.base_dir.mkdir()
        inst.modules_dir.mkdir()
        # Save base weights
        base_meta = {}
        for name, array in base_weights.items():
            file_name = f"{name}.npy"
            full_path = inst.base_dir / file_name
            np.save(full_path, array)
            base_meta[name] = {
                "path": file_name,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "sha512": _compute_sha512(full_path),
            }
        base_meta["quantization"] = quantization or "fp16"
        inst._base_metadata = base_meta
        with open(inst.metadata_path, "w", encoding="utf-8") as f:
            json.dump(base_meta, f, indent=2)
        # Initialize modules index
        modules_index = {"modules": {}, "count": 0}
        with open(inst.modules_index_path, "w", encoding="utf-8") as f:
            json.dump(modules_index, f, indent=2)
        # Initialize categories, experiences and history
        with open(inst.categories_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        with open(inst.experiences_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        # Create first generation (generation 0) with no modules
        history = {"generations": [{"modules": [], "skills": []}], "current": 0}
        with open(inst.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        # Reload state from disk for immediate use
        inst._load()
        return inst

    def _load(self) -> None:
        """Load metadata and indices from disk if present."""
        # Load base metadata
        if self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._base_metadata = json.load(f)
        # Load modules index
        if self.modules_index_path.exists():
            with open(self.modules_index_path, "r", encoding="utf-8") as f:
                idx = json.load(f)
            self._modules_index = idx
            for name, meta in idx.get("modules", {}).items():
                module = Module(
                    name=name,
                    module_type=meta["type"],
                    tensors={},  # lazy loading
                    domain=meta.get("domain"),
                    metadata=meta.get("metadata", {}),
                )
                self._modules[name] = module
        # Load categories
        if self.categories_path.exists():
            with open(self.categories_path, "r", encoding="utf-8") as f:
                self._categories = json.load(f)
        else:
            self._categories = {}
        # Load experiences
        if self.experiences_path.exists():
            with open(self.experiences_path, "r", encoding="utf-8") as f:
                self._experiences = json.load(f)
        else:
            self._experiences = []
        # Load history
        if self.history_path.exists():
            with open(self.history_path, "r", encoding="utf-8") as f:
                hist = json.load(f)
            self._generations = hist.get("generations", [])
            self._current_gen = hist.get("current", -1)
        else:
            self._generations = []
            self._current_gen = -1

    # ------------------------------------------------------------------
    # Helpers for loading data
    # ------------------------------------------------------------------
    def _load_base(self) -> Dict[str, np.ndarray]:
        """Load base weights into memory if not already loaded.

        Each tensor's SHA-512 hash is recomputed and compared against the
        hash recorded at creation time.  A mismatch means the file was
        corrupted or tampered with since it was last written, and raises
        ``IntegrityError`` rather than silently returning bad data.
        """
        if self._loaded_base is None:
            self._loaded_base = {}
            for name, meta in self._base_metadata.items():
                if name == "quantization":
                    continue
                path = self.base_dir / meta["path"]
                expected_hash = meta.get("sha512")
                if expected_hash is not None:
                    actual_hash = _compute_sha512(path)
                    if actual_hash != expected_hash:
                        raise IntegrityError(
                            f"Hash mismatch for base tensor '{name}': "
                            f"file may be corrupted or tampered with "
                            f"(expected {expected_hash[:16]}..., got {actual_hash[:16]}...)"
                        )
                self._loaded_base[name] = np.load(path)
        return self._loaded_base

    @staticmethod
    def _verify_hash(path: Path, expected_hash: Optional[str], label: str) -> None:
        """Recompute the SHA-512 hash of ``path`` and compare it to ``expected_hash``.

        Raises ``IntegrityError`` on mismatch.  If ``expected_hash`` is
        ``None`` (e.g. an older container written before hashing existed),
        the check is skipped rather than treated as a failure.
        """
        if expected_hash is None:
            return
        actual_hash = _compute_sha512(path)
        if actual_hash != expected_hash:
            raise IntegrityError(
                f"Hash mismatch for {label}: file may be corrupted or "
                f"tampered with (expected {expected_hash[:16]}..., got "
                f"{actual_hash[:16]}...)"
            )

    def _load_module_tensors(self, module_name: str) -> Dict[str, Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
        """Load the tensor data for a module given its name.

        Every tensor file's SHA-512 hash is verified against the hash
        recorded in the modules index before the array is returned.
        """
        # Read metadata from the in-memory modules index (kept in sync with disk)
        meta = self._modules_index["modules"][module_name]
        module_type = meta["type"]
        tensors: Dict[str, Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]] = {}
        if module_type == "DELTA":
            for tname, info in meta["tensors"].items():
                path = self.modules_dir / info["path"]
                self._verify_hash(path, info.get("sha512"), f"module '{module_name}' tensor '{tname}'")
                tensors[tname] = np.load(path)
        elif module_type == "LORA":
            for tname, info in meta["tensors"].items():
                path_A = self.modules_dir / info["path_A"]
                path_B = self.modules_dir / info["path_B"]
                self._verify_hash(path_A, info.get("sha512_A"), f"module '{module_name}' tensor '{tname}' (A)")
                self._verify_hash(path_B, info.get("sha512_B"), f"module '{module_name}' tensor '{tname}' (B)")
                A = np.load(path_A)
                B = np.load(path_B)
                tensors[tname] = (A, B)
        else:
            raise ValueError(f"Unknown module type: {module_type}")
        return tensors

    # ------------------------------------------------------------------
    # Batch-write support (I/O optimization)
    # ------------------------------------------------------------------
    @contextlib.contextmanager
    def batch(self):
        """Defer disk writes for the duration of the ``with`` block.

        Rewriting ``modules.json``, ``categories.json``, ``history.json``
        and ``experiences.json`` from scratch on every single operation is
        fine for a handful of calls, but becomes a bottleneck when adding
        many modules or experiences in a loop (see feedback 5.5).  Wrapping
        a sequence of calls in ``with container.batch(): ...`` keeps all
        the same in-memory state changes (and hash computation, which
        still happens per module since it depends on the file just
        written) but only flushes each JSON index to disk once, when the
        block exits. Calls can be nested; only the outermost block flushes.

        Example
        -------
        >>> with cont.batch():
        ...     for m in many_modules:
        ...         cont.append_module(m)
        """
        self._batch_depth += 1
        try:
            yield self
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                self._flush_dirty()

    def _flush_dirty(self) -> None:
        """Write any pending in-memory changes to disk."""
        if self._dirty["modules"]:
            with open(self.modules_index_path, "w", encoding="utf-8") as f:
                json.dump(self._modules_index, f, indent=2)
            self._dirty["modules"] = False
        if self._dirty["categories"]:
            with open(self.categories_path, "w", encoding="utf-8") as f:
                json.dump(self._categories, f, indent=2)
            self._dirty["categories"] = False
        if self._dirty["history"]:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump({"generations": self._generations, "current": self._current_gen}, f, indent=2)
            self._dirty["history"] = False
        if self._dirty["experiences"]:
            with open(self.experiences_path, "w", encoding="utf-8") as f:
                json.dump(self._experiences, f, indent=2)
            self._dirty["experiences"] = False

    def _write_modules_index(self) -> None:
        if self._batch_depth > 0:
            self._dirty["modules"] = True
            return
        with open(self.modules_index_path, "w", encoding="utf-8") as f:
            json.dump(self._modules_index, f, indent=2)

    def _write_categories(self) -> None:
        if self._batch_depth > 0:
            self._dirty["categories"] = True
            return
        with open(self.categories_path, "w", encoding="utf-8") as f:
            json.dump(self._categories, f, indent=2)

    def _write_history(self) -> None:
        if self._batch_depth > 0:
            self._dirty["history"] = True
            return
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump({"generations": self._generations, "current": self._current_gen}, f, indent=2)

    def _write_experiences(self) -> None:
        if self._batch_depth > 0:
            self._dirty["experiences"] = True
            return
        with open(self.experiences_path, "w", encoding="utf-8") as f:
            json.dump(self._experiences, f, indent=2)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    def append_module(self, module: Module) -> None:
        """Append a new module and create a new generation.

        The module's tensors are saved to disk, categories are updated
        with the module's domain (if provided), and the history is
        extended with the new generation.
        """
        # Disallow duplicate module names
        if module.name in self._modules:
            raise ModuleAlreadyExistsError(f"Module {module.name} already exists")
        # Save tensor files with shape validation and compute hashes
        # We defer updating the index until all files are written successfully.
        hashes: Dict[str, Dict[str, str]] = {}
        for tname, value in module.tensors.items():
            if module.module_type == "DELTA":
                # Validate shape against base metadata if present
                base_meta = self._base_metadata.get(tname)
                if base_meta is not None and tname != "quantization":
                    expected_shape = tuple(base_meta["shape"])
                    if value.shape != expected_shape:
                        raise IncompatibleShapeError(
                            f"Shape mismatch for tensor {tname} in module {module.name}: "
                            f"got {value.shape}, expected {expected_shape}"
                        )
                fname = f"{module.name}_{tname}.npy"
                full_path = self.modules_dir / fname
                np.save(full_path, value)  # type: ignore[arg-type]
                # Record SHA for integrity
                hashes[tname] = {"sha512": _compute_sha512(full_path)}
            elif module.module_type == "LORA":
                # value is a tuple (A, B)
                A, B = value  # type: ignore[assignment]
                base_meta = self._base_metadata.get(tname)
                if base_meta is not None and tname != "quantization":
                    expected_shape = tuple(base_meta["shape"])
                    # base_weight shape is (m, n)
                    m, n = expected_shape  # type: ignore[misc]
                    # Validate LoRA shapes
                    if not (isinstance(A, np.ndarray) and isinstance(B, np.ndarray)):
                        raise IncompatibleShapeError(
                            f"LoRA tensors for {tname} in module {module.name} must be NumPy arrays"
                        )
                    if A.ndim != 2 or B.ndim != 2:
                        raise IncompatibleShapeError(
                            f"LoRA tensors for {tname} in module {module.name} must be 2D matrices"
                        )
                    mA, r1 = A.shape
                    r2, nB = B.shape
                    if mA != m or nB != n or r1 != r2:
                        raise IncompatibleShapeError(
                            f"LoRA shape mismatch for tensor {tname} in module {module.name}: "
                            f"base shape {expected_shape}, A shape {A.shape}, B shape {B.shape}"
                        )
                fname_A = f"{module.name}_{tname}_A.npy"
                fname_B = f"{module.name}_{tname}_B.npy"
                full_path_A = self.modules_dir / fname_A
                full_path_B = self.modules_dir / fname_B
                np.save(full_path_A, A)
                np.save(full_path_B, B)
                hashes[tname] = {
                    "sha512_A": _compute_sha512(full_path_A),
                    "sha512_B": _compute_sha512(full_path_B),
                }
            else:
                raise ValueError(f"Unsupported module type: {module.module_type}")
        # Update in-memory modules index (flushed to disk by _write_modules_index,
        # either immediately or deferred if inside a batch() block).
        idx = self._modules_index
        # Serialize module metadata
        entry = module.to_index()
        # Attach the computed hashes to the entry
        for tname, hash_info in hashes.items():
            if module.module_type == "DELTA":
                entry["tensors"][tname].update(hash_info)
            elif module.module_type == "LORA":
                entry["tensors"][tname].update(hash_info)
        idx["modules"][module.name] = entry
        idx["count"] = idx.get("count", 0) + 1
        self._write_modules_index()
        # Update in‑memory modules
        self._modules[module.name] = Module(
            name=module.name,
            module_type=module.module_type,
            tensors={},  # lazy load later
            domain=module.domain,
            metadata=module.metadata,
        )
        # Update categories if a domain is provided
        if module.domain:
            cat = self._categories.get(module.domain, {"modules": [], "skills": []})
            cat["modules"].append(module.name)
            self._categories[module.domain] = cat
            self._write_categories()
        # Update history: copy active modules from current generation and append the new one
        active_modules: List[str] = []
        active_skills: List[str] = []
        if self._current_gen >= 0:
            active_modules = list(self._generations[self._current_gen]["modules"])
            active_skills = list(self._generations[self._current_gen].get("skills", []))
        active_modules.append(module.name)
        new_gen = {
            "modules": active_modules,
            "skills": active_skills,
        }
        self._generations.append(new_gen)
        self._current_gen = len(self._generations) - 1
        # Save history
        self._write_history()

    def current_modules(self) -> List[str]:
        """Return the list of module names active in the current generation."""
        if self._current_gen < 0:
            return []
        return list(self._generations[self._current_gen]["modules"])

    def rollback(self, generation: int) -> None:
        """Rollback to a previous generation index."""
        if generation < 0 or generation >= len(self._generations):
            raise IndexError("Generation out of range")
        self._current_gen = generation
        # Save history to disk
        self._write_history()

    def get_weight(self, name: str) -> np.ndarray:
        """Compute the effective tensor for ``name`` in the current generation."""
        base = self._load_base()
        if name not in base:
            raise KeyError(f"Tensor {name} not in base model")
        weight = base[name].copy()
        active_modules = self.current_modules()
        for mod_name in active_modules:
            mod = self._modules[mod_name]
            # lazy load tensors
            if not mod.tensors:
                mod.tensors = self._load_module_tensors(mod_name)
            updates = mod.apply({name: weight})
            if name in updates:
                weight = updates[name]
        return weight

    # ------------------------------------------------------------------
    # Categories and experiences
    # ------------------------------------------------------------------
    def list_categories(self) -> List[str]:
        """Return all category keys."""
        return list(self._categories.keys())

    def modules_in_category(self, category: str) -> List[str]:
        """Return module names associated with a given category."""
        entry = self._categories.get(category)
        if not entry:
            return []
        return entry.get("modules", [])

    def add_experience(self, record: Dict) -> None:
        """Append an experience record to the log."""
        self._experiences.append(record)
        self._write_experiences()

    def list_experiences(self) -> List[Dict]:
        """Return all experience records."""
        return list(self._experiences)

    def info(self) -> str:
        """Return a human‑readable summary of the container."""
        lines: List[str] = []
        lines.append(f"Base tensors: {len([k for k in self._base_metadata if k != 'quantization'])}")
        lines.append(f"Quantization: {self._base_metadata.get('quantization')}")
        lines.append(f"Total modules: {len(self._modules)}")
        lines.append(f"Categories: {len(self._categories)}")
        lines.append(f"Generations: {len(self._generations)}")
        lines.append(f"Current generation: {self._current_gen}")
        for idx, gen in enumerate(self._generations):
            marker = "*" if idx == self._current_gen else " "
            lines.append(f"{marker} Gen {idx}: modules={gen['modules']} skills={gen.get('skills', [])}")
        return "\n".join(lines)


def _demo() -> None:
    """Demonstrate the usage of the LiraContainer.

    This function is not used in tests but can be run manually to see
    how a container is created, modules are appended, experiences are
    recorded and generations are managed.
    """
    import tempfile
    # Create base weights for a toy model
    base = {
        "layer.weight": np.ones((4, 4), dtype=np.float32),
        "layer.bias": np.zeros((4,), dtype=np.float32),
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "lira_model"
        cont = LiraContainer.create(path, base, quantization="fp16")
        print("After creation:\n", cont.info())
        # Create a delta module that increments the weight
        delta = np.full((4, 4), 0.1, dtype=np.float32)
        m1 = Module(name="mod_increment", module_type="DELTA", tensors={"layer.weight": delta}, domain="programacao/python")
        cont.append_module(m1)
        print("After adding delta module:\n", cont.info())
        # Create a LoRA module: A (4x1) and B (1x4) to add rank‑1 update
        A = np.arange(4, dtype=np.float32).reshape(4, 1)
        B = (np.arange(4, dtype=np.float32) * 0.01).reshape(1, 4)
        m2 = Module(name="mod_rank1", module_type="LORA", tensors={"layer.weight": (A, B)}, domain="programacao/numerico")
        cont.append_module(m2)
        print("After adding LoRA module:\n", cont.info())
        # Record an experience
        cont.add_experience({"prompt": "Hello", "response": "World", "score": 0.9})
        # Inspect weight
        w = cont.get_weight("layer.weight")
        print("Effective weight:\n", w)
        # Rollback
        cont.rollback(0)
        print("After rollback to generation 0:\n", cont.info())
        w0 = cont.get_weight("layer.weight")
        print("Weight after rollback:\n", w0)


if __name__ == "__main__":
    _demo()