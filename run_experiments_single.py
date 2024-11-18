#!/usr/bin/env python3
import sys
import subprocess


subprocess.run(["./scripts/comp-run.py", "single_inputs", "single_src/bin", "speed-gpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "single_inputs", "single_src/bin", "speed-gpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "single_inputs", "single_src/bin", "ratio-gpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "single_inputs", "single_src/bin", "ratio-gpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "single_inputs", "single_src/bin", "speed-cpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "single_inputs", "single_src/bin", "speed-cpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "single_inputs", "single_src/bin", "ratio-cpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "single_inputs", "single_src/bin", "ratio-cpu-decompress.exe"])

