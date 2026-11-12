#!/usr/bin/env python3
"""Run the H15 add fixture's MIL on this Mac's ANE (macOS, native compiler) and
check the output against the shared H14/H15 smoke golden.

  clang -O2 -fobjc-arc -framework Foundation -framework IOSurface \
      tools/native-macos/ane_inmem_run.m -o SCRATCH/ane_inmem_run
  python3 tools/native-macos/h15_add_smoke.py SCRATCH

Inputs, packing, rounding and the golden come from packaging/omarchy-ane-smoke,
so a match here is the same check the Linux smoke makes.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def smoke_module():
    loader = importlib.machinery.SourceFileLoader("smoke", str(REPO / "packaging/omarchy-ane-smoke"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("smoke", loader))
    loader.exec_module(module)
    return module


def main(scratch, warmup=2, repeat=20):
    sm = smoke_module()
    lanes = sm.H14_LANES
    a, b = sm.inputs("a", lanes), sm.inputs("b", lanes)
    expected = sm.surface([sm.add_fp16(x, y) for x, y in zip(a, b)], lanes)
    golden = hashlib.sha256(sm.valid(expected, lanes)).hexdigest()
    assert golden == sm.H14_GOLDEN, golden
    (scratch / "out").mkdir(parents=True, exist_ok=True)
    (scratch / "tmp").mkdir(exist_ok=True)
    for name, bits in (("a", a), ("b", b)):
        (scratch / f"{name}.bin").write_bytes(sm.surface(bits, lanes))
    (scratch / "empty.bin").write_bytes(b"")
    size = len(expected)
    p = subprocess.run([str(scratch / "ane_inmem_run"), str(REPO / "fixtures/h15-hwx/add/model.mil"),
                        str(scratch / "empty.bin"), str(scratch / "out"), str(warmup), str(repeat),
                        f"in:{scratch}/a.bin:{size}", f"in:{scratch}/b.bin:{size}", f"out:y:{size}"],
                       capture_output=True, text=True, env={**os.environ, "TMPDIR": f"{scratch}/tmp/"})
    if p.returncode:
        sys.exit(f"ane_inmem_run rc={p.returncode}: {p.stderr.strip()}")
    run = json.loads(p.stdout)
    y = (scratch / "out/y.bin").read_bytes()
    got = hashlib.sha256(sm.valid(y, lanes)).hexdigest()
    stray = sum(1 for i in range(0, size, 2) if i % sm.PLANE and y[i:i + 2] != b"\0\0")
    result = {"valid_sha256": got, "golden_sha256": golden, "valid_match": got == golden,
              "full_surface_match": y[:size] == expected, "stray_nonzero_fp16": stray,
              "calls": len(run["exec_ms"]), "min_ms": min(run["exec_ms"]), "compile_ms": run["compile_ms"]}
    print(json.dumps(result))
    return 0 if result["valid_match"] and result["full_surface_match"] and not stray else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]).resolve()))
