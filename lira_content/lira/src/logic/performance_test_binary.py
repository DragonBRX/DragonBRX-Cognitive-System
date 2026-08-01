"""Performance comparison: JSON-directory prototype vs. binary `.lira` container.

Runs the same workload against `LiraContainer` (lira_final_demo.py) and
`LiraBinary` (lira_binary.py) and prints timings side by side, both with
and without the JSON prototype's new `batch()` mode. This gives concrete
numbers for the I/O-optimization discussion in the feedback report
(section 5.5), rather than just a claim.
"""

import sys
import time
import tempfile
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))

from lira_final.lira_final_demo import LiraContainer, Module as JModule
from lira_final.lira_binary import LiraBinary
from lira_final.lira_final_demo import Module as BModule  # same class, reused by both


def _make_base():
    return {
        "layer.weight": np.random.rand(512, 512).astype(np.float32),
        "layer.bias": np.random.rand(512).astype(np.float32),
    }


def bench_json_prototype(n_modules: int, batch: bool) -> float:
    base = _make_base()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "model"
        cont = LiraContainer.create(path, base, quantization="fp16")
        delta = np.full((512, 512), 0.001, dtype=np.float32)
        t0 = time.perf_counter()
        if batch:
            with cont.batch():
                for i in range(n_modules):
                    cont.append_module(JModule(name=f"m{i}", module_type="DELTA", tensors={"layer.weight": delta}, domain=f"d/{i}"))
        else:
            for i in range(n_modules):
                cont.append_module(JModule(name=f"m{i}", module_type="DELTA", tensors={"layer.weight": delta}, domain=f"d/{i}"))
        t1 = time.perf_counter()
    return t1 - t0


def bench_binary(n_modules: int, batch: bool) -> float:
    base = _make_base()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "model.lira"
        cont = LiraBinary.create(path, base, quantization="fp16", metadata_slot_size=2 * 1024 * 1024)
        delta = np.full((512, 512), 0.001, dtype=np.float32)
        t0 = time.perf_counter()
        if batch:
            cont.append_modules([BModule(name=f"m{i}", module_type="DELTA", tensors={"layer.weight": delta}, domain=f"d/{i}") for i in range(n_modules)])
        else:
            for i in range(n_modules):
                cont.append_module(BModule(name=f"m{i}", module_type="DELTA", tensors={"layer.weight": delta}, domain=f"d/{i}"))
        t1 = time.perf_counter()
        cont.close()
    return t1 - t0


def main() -> None:
    for n in (10, 50, 100):
        t_json = bench_json_prototype(n, batch=False)
        t_json_batch = bench_json_prototype(n, batch=True)
        t_bin = bench_binary(n, batch=False)
        t_bin_batch = bench_binary(n, batch=True)
        print(f"\n--- Appending {n} DELTA modules (512x512 float32) ---")
        print(f"JSON prototype, write-through:        {t_json:.4f} s  ({t_json / n * 1000:.2f} ms/module)")
        print(f"JSON prototype, batch():               {t_json_batch:.4f} s  ({t_json_batch / n * 1000:.2f} ms/module)")
        print(f"Binary container, per-module commit:  {t_bin:.4f} s  ({t_bin / n * 1000:.2f} ms/module)")
        print(f"Binary container, append_modules():    {t_bin_batch:.4f} s  ({t_bin_batch / n * 1000:.2f} ms/module)")


if __name__ == "__main__":
    main()
