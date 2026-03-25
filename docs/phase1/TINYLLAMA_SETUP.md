# TinyLlama / llama.cpp Setup (Raspberry Pi 4 — Phase‑1)

This guide shows minimal, repeatable steps to build `llama.cpp` and prepare `llama-cpp-python` on a Raspberry Pi 4 (64-bit). Perform these steps on the Pi (or cross-compile in CI).

## Prerequisites

- Ubuntu Server 22.04 (64-bit) on Raspberry Pi 4 (4GB)
- External USB3 SSD recommended for model files and swap
- SSH access (optional)

## System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git cmake python3-venv python3-pip libgomp1
```

## Build llama.cpp

```bash
# in /home/pi or workspace dir
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
# build with make (auto-detects ARM/NEON)
make -j4
```

After building, the shared library/binary will be available in the repository. `llama-cpp-python` will try to locate the compiled library automatically; you can also set `LLAMA_LIB_PATH` to the built library path.

## Install Python binding

```bash
# create venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install llama-cpp-python
```

If `llama-cpp-python` cannot find the library, set `LLAMA_LIB_PATH` to the built shared library file (e.g., `/home/pi/llama.cpp/libllama.so`) before importing.

## Model placement & env

- Place quantized GGML models (q4/q8) on the SSD, e.g. `/mnt/ssd/models/tinyllama-q4.bin`.
- Set env var: `export MODEL_PATH=/mnt/ssd/models/tinyllama-q4.bin`

## Swap and memory tips

- Configure a small zram or file swap to reduce OOMs during model load.
- Keep context lengths short to conserve RAM. Use q4/q8 models for 4GB Pi.

## Quick Python test

```python
from llama_cpp import Llama
llm = Llama(model_path="/path/to/tinyllama-q4.bin")
print(llm("Hello world", max_tokens=16))
```

## Troubleshooting

- If `ImportError` occurs, check `LLAMA_LIB_PATH` and that the built library has correct permissions.
- If OOM while loading: use a more aggressive quantized build, move model to faster SSD, or reduce context size.

---

Last updated: 2026-03-25
