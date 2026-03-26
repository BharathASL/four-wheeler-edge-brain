# WSL / Audio & Camera Notes (development)

Notes to help develop on Windows using WSL2/WSLg and to mirror Pi behavior.

## One-time WSL bootstrap

Use the repository bootstrap script on a fresh Ubuntu-based WSL instance:

```bash
bash scripts/setup_wsl_dev.sh
```

Useful flags:

```bash
# inspect commands without changing the machine
bash scripts/setup_wsl_dev.sh --dry-run

# install deps into a different virtualenv and run a smoke test
bash scripts/setup_wsl_dev.sh --venv-path .venv-wsl --run-smoke-test
```

What the script does:

- installs required Ubuntu packages for Python builds, audio tooling, and basic camera utilities
- creates a project virtual environment
- upgrades pip/setuptools/wheel
- installs `requirements.txt`
- optionally runs `tests/test_smoke.py`

## Camera access (WSL2)

- Windows: install `usbipd-win` to forward USB cameras into WSL:

```powershell
# on Windows (Admin)
winget install --id=Microsoft.usbipd
usbipd wsl list
usbipd wsl attach --busid <busid>
```

- In WSL, verify `/dev/video0` exists and test with `v4l2-ctl` or `ffmpeg`.

## Audio (WSLg / PulseAudio)

- WSLg forwards audio to Windows automatically for GUI apps. For CLI audio capture/playback use PulseAudio in WSL or use Windows host redirection.
- Recommended for deterministic tests: use mocked audio adapter (see `src/audio_adapter.py`) so unit tests do not require system audio.

## Tips

- Use `v4l2-ctl --list-devices` to confirm camera devices in WSL.
- For USB forwarding, detach the device from Windows if you want exclusive access in WSL.
- Keep adapters in code so the same tests run in WSL and on Pi.

---

Last updated: 2026-03-25
