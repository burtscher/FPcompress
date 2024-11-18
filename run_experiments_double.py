#!/usr/bin/env python3
import sys
import subprocess

subprocess.run(["./scripts/comp-run.py", "double_inputs", "double_src/bin", "speed-gpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "double_inputs", "double_src/bin", "speed-gpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "double_inputs", "double_src/bin", "ratio-gpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "double_inputs", "double_src/bin", "ratio-gpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "double_inputs", "double_src/bin", "speed-cpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "double_inputs", "double_src/bin", "speed-cpu-decompress.exe"])
subprocess.run(["./scripts/comp-run.py", "double_inputs", "double_src/bin", "ratio-cpu-compress.exe"])
subprocess.run(["./scripts/decomp-run.py", "double_inputs", "double_src/bin", "ratio-cpu-decompress.exe"])

