"""Simple performance tests for the LiraContainer prototype.

This script measures the execution time of common operations in the
LiraContainer demonstration implementation:

* Loading base weights into memory.
* Appending delta and LoRA modules.
* Computing effective weights with multiple modules.
* Reading categories and experiences.

It prints a report summarizing the measured times.  The purpose is
illustrative; results depend on hardware and environment and should
not be considered final benchmarks.
"""

import time
from pathlib import Path
import tempfile
import numpy as np

# Add the parent directory of this file to the Python path so that
# `lira_final` can be imported when the script is run directly.
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from lira_final_demo import LiraContainer, Module  # type: ignore


def main() -> None:
    # Create a temporary container with a moderate number of weights
    base = {
        "layer.weight": np.random.rand(512, 512).astype(np.float32),
        "layer.bias": np.random.rand(512).astype(np.float32),
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "model"
        t0 = time.perf_counter()
        cont = LiraContainer.create(path, base, quantization="fp16")
        t1 = time.perf_counter()
        load_time = t1 - t0
        # Prepare modules
        delta = np.full((512, 512), 0.01, dtype=np.float32)
        m_delta = Module(name="delta", module_type="DELTA", tensors={"layer.weight": delta}, domain="domain/delta")
        A = np.random.rand(512, 16).astype(np.float32)
        B = np.random.rand(16, 512).astype(np.float32)
        m_lora = Module(name="lora", module_type="LORA", tensors={"layer.weight": (A, B)}, domain="domain/lora")
        # Append delta
        t2 = time.perf_counter()
        cont.append_module(m_delta)
        t3 = time.perf_counter()
        delta_time = t3 - t2
        # Append LoRA
        t4 = time.perf_counter()
        cont.append_module(m_lora)
        t5 = time.perf_counter()
        lora_time = t5 - t4
        # Compute effective weight
        t6 = time.perf_counter()
        _ = cont.get_weight("layer.weight")
        t7 = time.perf_counter()
        weight_time = t7 - t6
        # Read categories
        t8 = time.perf_counter()
        cats = cont.list_categories()
        mods_delta = cont.modules_in_category("domain/delta")
        t9 = time.perf_counter()
        categories_time = t9 - t8
        # Add experience and list
        t10 = time.perf_counter()
        cont.add_experience({"prompt": "p", "response": "r", "score": 1.0})
        _ = cont.list_experiences()
        t11 = time.perf_counter()
        experience_time = t11 - t10
    # Print results
    print(f"Base creation time: {load_time:.6f} s")
    print(f"Append delta module time: {delta_time:.6f} s")
    print(f"Append LoRA module time: {lora_time:.6f} s")
    print(f"Effective weight computation time: {weight_time:.6f} s")
    print(f"Category lookup time: {categories_time:.6f} s")
    print(f"Experience logging and retrieval time: {experience_time:.6f} s")


if __name__ == "__main__":
    main()