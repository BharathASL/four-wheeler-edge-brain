# Deployment notes (example) — Phase‑1 PoC

This document explains how to deploy the Phase‑1 PoC on a Raspberry Pi using the example `robot.service` unit provided in this folder.

Prerequisites
- A Raspberry Pi with Ubuntu Server 24.04 64-bit
- Project checkout at `/home/<user>/four-wheeler-robot` (adjust paths below)
- Python 3.10+, virtualenv with dependencies installed
- Optional: compiled `llama.cpp` library and a quantized GGML model on disk

Quick deploy steps (example)

1. Copy the example unit to systemd and edit paths:

```bash
sudo cp docs/phase1/robot.service /etc/systemd/system/four-wheeler-robot.service
sudo nano /etc/systemd/system/four-wheeler-robot.service
# Edit User, WorkingDirectory, ExecStart and Environment lines as appropriate
```

2. Reload systemd, enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable four-wheeler-robot.service
sudo systemctl start four-wheeler-robot.service
```

3. Inspect logs and status:

```bash
sudo systemctl status four-wheeler-robot.service
sudo journalctl -u four-wheeler-robot.service -f
```

Notes & recommendations
- Do not run the model as `root` — use a dedicated user (e.g., `pi` or `robot`).
- Ensure the Python virtualenv path in `ExecStart` points to the venv's Python binary.
- Export `MODEL_PATH` and `LLAMA_LIB_PATH` in the unit `Environment=` lines, or create an `/etc/environment.d/` file for system-wide vars.
- On low-memory devices (4GB Pi), keep the model small (q4/q8) and consider adding swap or zram.
- For debugging, run the entrypoint interactively before configuring systemd:

```bash
source .venv/bin/activate
python main.py
```

Security
- Limit filesystem permissions for the service user to only the necessary project and model paths.
- Consider running under a systemd scope or with resource limits if you expect memory pressure.
