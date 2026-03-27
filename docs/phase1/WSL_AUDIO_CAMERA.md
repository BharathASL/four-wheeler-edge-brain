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

Development note:
- If an Android phone is used as a USB webcam for Windows, treat that as a development convenience path and verify first that WSL sees it as a normal video device before planning around it. Windows camera availability alone is not sufficient; WSL still needs a usable `/dev/video*` device or another explicit frame bridge.

## Audio (WSLg / PulseAudio)

- WSLg forwards audio to Windows automatically for GUI apps. For CLI audio capture/playback use PulseAudio in WSL or use Windows host redirection.
- Recommended for deterministic tests: use mocked audio adapter (see `src/audio_adapter.py`) so unit tests do not require system audio.

Development note:
- A Windows-connected speaker is a reasonable development target for the current pyttsx3 path, but confirm playback end to end from WSL before relying on it for TTS debugging.
- A Blue Yeti microphone is a reasonable development target for STT and input-listener experiments, but confirm that the chosen WSL audio input path exposes the microphone to Linux-side capture libraries before treating it as the default dev setup.

## Suggested Pre-Hardware Validation

Before buying Pi-side audio and camera hardware, validate the current Windows-hosted development devices in this order:

1. Confirm Windows speaker output works from the WSL development environment.
2. Confirm Blue Yeti microphone capture works from the WSL development environment.
3. Confirm the Android phone camera path appears as a usable WSL capture device or identify the bridge required.
4. Only after those checks pass, document the approved development workflow for speech and camera testing.

## Tips

- Use `v4l2-ctl --list-devices` to confirm camera devices in WSL.
- For USB forwarding, detach the device from Windows if you want exclusive access in WSL.
- Keep adapters in code so the same tests run in WSL and on Pi.

---

Last updated: 2026-03-27
